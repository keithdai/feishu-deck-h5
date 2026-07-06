#!/usr/bin/env python3
"""Upload deck-level reusable artifacts with resumable manifest logging."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import archive
import lark_base
from upload_thumbnails import (
    append_manifest,
    prepare_cli_upload_path,
)


@dataclass(frozen=True)
class ArtifactItem:
    kind: str
    key_field: str
    key_value: str
    field_id: str
    local_path: Path


def build_artifact_items(output_dir: Path, deck_id: str | None) -> list[ArtifactItem]:
    plan = archive.build_archive_plan(output_dir, deck_id)
    resolved_deck_id = str(plan["deck_record"]["deck_id"])
    artifacts = archive.prepare_artifacts_for_upload(output_dir, plan["artifact_files"])
    items: list[ArtifactItem] = []
    for field_id in ("deck_json", "inline_html", "assets_zip"):
        local_path = artifacts.get(field_id)
        if not local_path:
            continue
        items.append(
            ArtifactItem(
                kind="deck_artifact",
                key_field="deck_id",
                key_value=resolved_deck_id,
                field_id=field_id,
                local_path=Path(str(local_path)),
            )
        )
    return items


def item_to_manifest(item: ArtifactItem) -> dict[str, Any]:
    data = asdict(item)
    data["local_path"] = str(item.local_path)
    return data


def upload_artifact_item(
    config: lark_base.BaseConfig,
    item: ArtifactItem,
    *,
    skip_existing: bool = False,
) -> dict[str, Any]:
    result = item_to_manifest(item)
    if not item.local_path.exists():
        result.update({"status": "skipped", "reason": "local artifact missing"})
        return result

    record_id = lark_base.find_record_id(
        config,
        table_id=config.decks_table,
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
            table_id=config.decks_table,
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
            table_id=config.decks_table,
            record_id=record_id,
            field_id=item.field_id,
            files=[prepare_cli_upload_path(item.local_path, staging_dir=Path(".deck-library-cache/upload-artifacts"))],
        )
        result.update({"status": "uploaded", "result": {"removed": 0, "upload_result": upload_result}})
        return result

    upload_result = lark_base.replace_attachment(
        config,
        table_id=config.decks_table,
        record_id=record_id,
        field_id=item.field_id,
        files=[prepare_cli_upload_path(item.local_path, staging_dir=Path(".deck-library-cache/upload-artifacts"))],
    )
    result.update({"status": "uploaded", "result": upload_result})
    return result


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
            statuses[(str(entry.get("field_id")), str(entry.get("key_value")))] = str(entry.get("status"))
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
    items: list[ArtifactItem],
    *,
    manifest_path: Path,
    resume: bool,
    retry_failed: bool,
) -> list[ArtifactItem]:
    if retry_failed:
        failed = prior_failed_keys(manifest_path)
        return [item for item in items if (item.field_id, item.key_value) in failed]
    if resume:
        done = prior_success_keys(manifest_path)
        return [item for item in items if (item.field_id, item.key_value) not in done]
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload deck_json, inline_html, and assets_zip for an archived deck.")
    parser.add_argument("output_dir", type=Path, help="Directory containing deck.json and index.html.")
    parser.add_argument("--deck-id", help="Stable deck ID used by the existing Base record.")
    parser.add_argument("--skip-existing", action="store_true", help="Do not replace fields that already have an attachment token.")
    parser.add_argument("--resume", action="store_true", help="Skip items already marked uploaded/skipped in the manifest.")
    parser.add_argument("--retry-failed", action="store_true", help="Only retry items marked failed in the manifest.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned artifact upload items without writing Base.")
    parser.add_argument("--manifest", type=Path, help="JSONL manifest path. Defaults to <output_dir>/artifact-upload-manifest.jsonl.")
    parser.add_argument("--command-timeout", type=float, default=180.0, help="Per lark-cli command timeout in seconds. Default: 180.")
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
        print("upload_artifacts.py: choose either --resume or --retry-failed, not both", file=sys.stderr)
        return 2

    try:
        output_dir = args.output_dir.resolve()
        manifest_path = args.manifest or output_dir / "artifact-upload-manifest.jsonl"
        items = build_artifact_items(output_dir, args.deck_id)
        items = filter_items_for_manifest(
            items,
            manifest_path=manifest_path,
            resume=args.resume,
            retry_failed=args.retry_failed,
        )
    except Exception as exc:
        print(f"upload_artifacts.py: {exc}", file=sys.stderr)
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
        print("upload_artifacts.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    lark_base.COMMAND_TIMEOUT_SECONDS = args.command_timeout
    summary = {"uploaded": 0, "skipped": 0, "failed": 0, "total": len(items)}
    for index, item in enumerate(items, start=1):
        try:
            result = upload_artifact_item(config, item, skip_existing=args.skip_existing)
        except Exception as exc:
            result = item_to_manifest(item)
            result.update({"status": "failed", "reason": str(exc)})
        summary[result.get("status", "failed")] = summary.get(result.get("status", "failed"), 0) + 1
        append_manifest(manifest_path, result)
        print(f"[{index}/{len(items)}] {item.key_value} {item.field_id}: {result.get('status')}")

    print(json.dumps({"mode": "write", "summary": summary, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
