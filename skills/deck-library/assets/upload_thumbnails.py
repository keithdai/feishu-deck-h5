#!/usr/bin/env python3
"""Upload deck cover and material thumbnails with resumable manifest logging."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import archive
import lark_base


@dataclass(frozen=True)
class ThumbnailItem:
    kind: str
    table_attr: str
    key_field: str
    key_value: str
    field_id: str
    local_path: Path


def build_thumbnail_items(
    output_dir: Path,
    deck_id: str | None,
    *,
    limit: int | None = None,
    include_cover: bool = True,
) -> list[ThumbnailItem]:
    plan = archive.build_archive_plan(output_dir, deck_id, limit_slides=limit)
    resolved_deck_id = str(plan["deck_record"]["deck_id"])
    items: list[ThumbnailItem] = []
    cover_thumbnail = plan["deck_record"].get("cover_thumbnail")
    if include_cover and cover_thumbnail:
        items.append(
            ThumbnailItem(
                kind="deck_cover",
                table_attr="decks_table",
                key_field="deck_id",
                key_value=resolved_deck_id,
                field_id="cover_thumbnail",
                local_path=Path(str(cover_thumbnail)),
            )
        )
    for record in plan["slide_records"]:
        thumbnail = record.get("thumbnail")
        if not thumbnail:
            continue
        items.append(
            ThumbnailItem(
                kind="slide_thumbnail",
                table_attr="slides_table",
                key_field="slide_id",
                key_value=str(record["slide_id"]),
                field_id="thumbnail",
                local_path=Path(str(thumbnail)),
            )
        )
    return items


def item_to_manifest(item: ThumbnailItem) -> dict[str, Any]:
    data = asdict(item)
    data["local_path"] = str(item.local_path)
    return data


def prepare_cli_upload_path(
    local_path: Path,
    *,
    staging_dir: Path = Path(".deck-library-cache/upload-thumbnails"),
) -> str:
    resolved = local_path.resolve()
    cwd = Path.cwd().resolve()
    try:
        resolved.relative_to(cwd)
        return os.path.relpath(resolved, cwd)
    except ValueError:
        digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        root = staging_dir if staging_dir.is_absolute() else cwd / staging_dir
        target_dir = root / digest
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / resolved.name
        shutil.copy2(resolved, target)
        return os.path.relpath(target.resolve(), cwd)


def upload_thumbnail_item(
    config: lark_base.BaseConfig,
    item: ThumbnailItem,
    *,
    skip_existing: bool = False,
) -> dict[str, Any]:
    result = item_to_manifest(item)
    table_id = getattr(config, item.table_attr)
    if not item.local_path.exists():
        result.update({"status": "skipped", "reason": "local thumbnail missing"})
        return result

    record_id = lark_base.find_record_id(
        config,
        table_id=table_id,
        key_field=item.key_field,
        key_value=item.key_value,
    )
    result["record_id"] = record_id
    if not record_id:
        result.update({"status": "skipped", "reason": "record not found"})
        return result

    if skip_existing:
        existing_tokens = lark_base.get_attachment_tokens(
            config,
            table_id=table_id,
            record_id=record_id,
            field_id=item.field_id,
        )
        if existing_tokens:
            result.update(
                {
                    "status": "skipped",
                    "reason": "attachment already exists",
                    "existing_tokens": existing_tokens,
                }
            )
            return result

        upload_result = lark_base.upload_attachment(
            config,
            table_id=table_id,
            record_id=record_id,
            field_id=item.field_id,
            files=[prepare_cli_upload_path(item.local_path)],
        )
        result.update({"status": "uploaded", "result": {"removed": 0, "upload_result": upload_result}})
        return result

    upload_result = lark_base.replace_attachment(
        config,
        table_id=table_id,
        record_id=record_id,
        field_id=item.field_id,
        files=[prepare_cli_upload_path(item.local_path)],
    )
    result.update({"status": "uploaded", "result": upload_result})
    return result


def append_manifest(manifest_path: Path, result: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")


def latest_manifest_statuses(manifest_path: Path) -> dict[tuple[str, str], str]:
    if not manifest_path.exists():
        return {}
    statuses: dict[tuple[str, str], str] = {}
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            statuses[(str(entry.get("kind")), str(entry.get("key_value")))] = str(entry.get("status"))
    return statuses


def manifest_keys_with_status(manifest_path: Path, statuses: set[str]) -> set[tuple[str, str]]:
    return {
        key
        for key, status in latest_manifest_statuses(manifest_path).items()
        if status in statuses
    }


def prior_success_keys(manifest_path: Path) -> set[tuple[str, str]]:
    return manifest_keys_with_status(manifest_path, {"uploaded", "skipped"})


def prior_failed_keys(manifest_path: Path) -> set[tuple[str, str]]:
    return manifest_keys_with_status(manifest_path, {"failed"})


def filter_items_for_manifest(
    items: list[ThumbnailItem],
    *,
    manifest_path: Path,
    resume: bool,
    retry_failed: bool,
) -> list[ThumbnailItem]:
    if retry_failed:
        failed = prior_failed_keys(manifest_path)
        return [item for item in items if (item.kind, item.key_value) in failed]
    if resume:
        done = prior_success_keys(manifest_path)
        return [item for item in items if (item.kind, item.key_value) not in done]
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload deck cover and material thumbnails for an archived deck.")
    parser.add_argument("output_dir", type=Path, help="Directory containing deck.json, index.html, and pages/page-XX thumbnails.")
    parser.add_argument("--deck-id", help="Stable deck ID used by the existing Base records.")
    parser.add_argument("--limit", type=int, help="Upload only the first N slide thumbnails.")
    parser.add_argument("--no-cover", action="store_true", help="Skip Decks.cover_thumbnail upload.")
    parser.add_argument("--skip-existing", action="store_true", help="Do not replace records that already have an attachment token.")
    parser.add_argument("--resume", action="store_true", help="Skip items already marked uploaded/skipped in the manifest.")
    parser.add_argument("--retry-failed", action="store_true", help="Only retry items marked failed in the manifest.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned upload items without writing Base.")
    parser.add_argument("--manifest", type=Path, help="JSONL manifest path. Defaults to <output_dir>/thumbnail-upload-manifest.jsonl.")
    parser.add_argument("--command-timeout", type=float, default=90.0, help="Per lark-cli command timeout in seconds. Default: 90.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name. Defaults to DECK_LIBRARY_SLIDES_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.resume and args.retry_failed:
        print("upload_thumbnails.py: choose either --resume or --retry-failed, not both", file=sys.stderr)
        return 2

    try:
        output_dir = args.output_dir.resolve()
        manifest_path = args.manifest or output_dir / "thumbnail-upload-manifest.jsonl"
        items = build_thumbnail_items(
            output_dir,
            args.deck_id,
            limit=args.limit,
            include_cover=not args.no_cover,
        )
        items = filter_items_for_manifest(
            items,
            manifest_path=manifest_path,
            resume=args.resume,
            retry_failed=args.retry_failed,
        )
    except Exception as exc:
        print(f"upload_thumbnails.py: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps({"mode": "dry-run", "items": [item_to_manifest(item) for item in items]}, ensure_ascii=False, indent=2))
        return 0

    config = lark_base.BaseConfig.from_env(
        base_token=args.base_token,
        decks_table=args.decks_table,
        slides_table=args.slides_table,
        profile=args.profile,
        identity=args.identity,
    )
    errors = config.validation_errors()
    if errors:
        print("upload_thumbnails.py: " + "; ".join(errors), file=sys.stderr)
        return 2
    lark_base.COMMAND_TIMEOUT_SECONDS = args.command_timeout

    summary = {"uploaded": 0, "skipped": 0, "failed": 0, "manifest": str(manifest_path)}
    for item in items:
        try:
            result = upload_thumbnail_item(config, item, skip_existing=args.skip_existing)
        except Exception as exc:
            result = item_to_manifest(item)
            result.update({"status": "failed", "reason": str(exc)})
        append_manifest(manifest_path, result)
        status = result.get("status")
        if status in summary:
            summary[status] += 1
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)

    print(json.dumps({"mode": "write", "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
