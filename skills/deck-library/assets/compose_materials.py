#!/usr/bin/env python3
"""Compose a new deck from Material records selected by material_id/material_code."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import lark_base


MATERIAL_SELECT_FIELDS = [
    "material_id",
    "material_code",
    "slide_key",
    "title",
    "page_description",
    "slide_payload_json",
    "source_artifact_ref",
    "material_type",
    "quality_tier",
    "fidelity_notes",
    "has_motion",
    "motion_tier",
    "motion_notes",
]


def extract_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    fields = data.get("fields")
    rows = data.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return []
    return [
        {str(field): value for field, value in zip(fields, row)}
        for row in rows
        if isinstance(row, list)
    ]


def first_material(result: dict[str, Any], identifier: str) -> dict[str, Any]:
    rows = extract_rows(result)
    if not rows:
        raise ValueError(f"material not found: {identifier}")
    if len(rows) > 1:
        exact_rows = [
            row
            for row in rows
            if row.get("material_id") == identifier or row.get("material_code") == identifier
        ]
        if len(exact_rows) == 1:
            return exact_rows[0]
        raise ValueError(f"material identifier matched multiple records: {identifier}")
    return rows[0]


def fetch_material_records(config: lark_base.BaseConfig, identifiers: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for identifier in identifiers:
        result = lark_base.lookup_material(
            config,
            identifier=identifier,
            select_fields=MATERIAL_SELECT_FIELDS,
        )
        records.append(first_material(result, identifier))
    return records


def scalar_cell(value: Any, default: str = "unknown") -> str:
    if isinstance(value, list):
        if not value:
            return default
        return str(value[0])
    if value is None or value == "":
        return default
    return str(value)


def bool_cell(value: Any) -> bool:
    if isinstance(value, list):
        return any(bool_cell(item) for item in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def quality_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_material_type: dict[str, int] = {}
    by_quality_tier: dict[str, int] = {}
    for record in records:
        material_type = scalar_cell(record.get("material_type"))
        quality_tier = scalar_cell(record.get("quality_tier"))
        by_material_type[material_type] = by_material_type.get(material_type, 0) + 1
        by_quality_tier[quality_tier] = by_quality_tier.get(quality_tier, 0) + 1
    return {
        "total": len(records),
        "by_material_type": by_material_type,
        "by_quality_tier": by_quality_tier,
    }


def quality_warnings(records: list[dict[str, Any]]) -> list[str]:
    replica_codes = [
        str(record.get("material_code") or record.get("material_id") or "<unknown>")
        for record in records
        if scalar_cell(record.get("material_type")) == "replica_screenshot"
    ]
    if not replica_codes:
        return []
    return [
        "包含截图 replica 素材 "
        + ", ".join(replica_codes)
        + "；适合快速预览/草稿组合，正式客户交付前建议升级为 native H5。"
    ]


def motion_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_motion_tier: dict[str, int] = {}
    with_motion = 0
    for record in records:
        motion_tier = scalar_cell(record.get("motion_tier"), default="none")
        by_motion_tier[motion_tier] = by_motion_tier.get(motion_tier, 0) + 1
        if bool_cell(record.get("has_motion")):
            with_motion += 1
    return {
        "total": len(records),
        "with_motion": with_motion,
        "by_motion_tier": by_motion_tier,
    }


def motion_warnings(records: list[dict[str, Any]]) -> list[str]:
    replica_codes = [
        str(record.get("material_code") or record.get("material_id") or "<unknown>")
        for record in records
        if scalar_cell(record.get("material_type")) == "replica_screenshot"
    ]
    warnings: list[str] = []
    if replica_codes:
        warnings.append(
            "截图素材 "
            + ", ".join(replica_codes)
            + " 默认不加动效；如需高级动效，先升级为 native H5。"
        )
    return warnings


def build_deck_from_material_records(records: list[dict[str, Any]], title: str) -> dict[str, Any]:
    slides: list[dict[str, Any]] = []
    for record in records:
        payload = record.get("slide_payload_json")
        if not isinstance(payload, str) or not payload.strip():
            raise ValueError(f"material {record.get('material_id', '<unknown>')} is missing slide_payload_json")
        slide = json.loads(payload)
        if not isinstance(slide, dict):
            raise ValueError(f"material {record.get('material_id', '<unknown>')} slide_payload_json must be an object")
        extracted = copy.deepcopy(slide)
        material_id = str(record.get("material_id") or "")
        extracted["lifted"] = material_id
        extracted["lift_origin"] = {
            "material_id": material_id,
            "material_code": record.get("material_code"),
            "source_artifact_ref": record.get("source_artifact_ref"),
            "src_key": record.get("slide_key") or slide.get("key"),
        }
        slides.append(extracted)
    warnings = quality_warnings(records)
    notes = "Composed by deck-library from Material records."
    if warnings:
        notes += " " + " ".join(warnings)
    return {
        "version": "1.0",
        "deck": {"title": title},
        "slides": slides,
        "notes": notes,
    }


def write_deck(deck: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    deck_path = output_dir / "deck.json"
    deck_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return deck_path


def copy_asset_roots(asset_roots: list[Path], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for root in asset_roots:
        for name in ("assets", "pages"):
            source = root / name
            if not source.exists() or not source.is_dir():
                continue
            destination = output_dir / name
            shutil.copytree(source, destination, dirs_exist_ok=True)


def deck_ids_from_material_records(records: list[dict[str, Any]]) -> list[str]:
    deck_ids: list[str] = []
    for record in records:
        ref = str(record.get("source_artifact_ref") or "")
        prefix = "base://deck/"
        if not ref.startswith(prefix):
            continue
        deck_id = ref.removeprefix(prefix)
        if deck_id and deck_id not in deck_ids:
            deck_ids.append(deck_id)
    return deck_ids


def extract_asset_zip(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_root = output_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (output_dir / member.filename).resolve()
            if output_root not in (target, *target.parents):
                raise ValueError(f"unsafe zip member path: {member.filename}")
        archive.extractall(output_dir)


def download_asset_roots(
    config: lark_base.BaseConfig,
    deck_ids: list[str],
    cache_dir: Path,
) -> list[Path]:
    roots: list[Path] = []
    for deck_id in deck_ids:
        record_id = lark_base.find_record_id(
            config,
            table_id=config.decks_table,
            key_field="deck_id",
            key_value=deck_id,
        )
        if not record_id:
            raise ValueError(f"deck artifact record not found: {deck_id}")
        tokens = lark_base.get_attachment_tokens(
            config,
            table_id=config.decks_table,
            record_id=record_id,
            field_id="assets_zip",
        )
        if not tokens:
            raise ValueError(f"deck {deck_id} has no assets_zip attachment")
        deck_cache = cache_dir / deck_id
        deck_cache.mkdir(parents=True, exist_ok=True)
        zip_path = deck_cache / "assets.zip"
        lark_base.download_attachment(
            config,
            table_id=config.decks_table,
            record_id=record_id,
            file_tokens=[tokens[0]],
            output=os.path.relpath(zip_path, Path.cwd()),
            overwrite=True,
        )
        asset_root = deck_cache / "extracted"
        extract_asset_zip(zip_path, asset_root)
        roots.append(asset_root)
    return roots


def default_renderer_root() -> Path:
    return Path(__file__).resolve().parents[2] / "feishu-deck-h5"


def render_deck(deck_path: Path, output_dir: Path, renderer_root: Path) -> dict[str, Any]:
    render_script = renderer_root / "deck-json" / "render-deck.py"
    command = [sys.executable, str(render_script), str(deck_path), str(output_dir), "--final"]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose a deck from material IDs/codes stored in Base.")
    parser.add_argument("materials", nargs="+", help="Material IDs or human-facing codes, e.g. M001 or deck_id:M001.")
    parser.add_argument("--title", default="Composed Material Deck", help="Title for the generated deck.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/deck-library-material-compose/output"))
    parser.add_argument("--asset-root", action="append", type=Path, default=[], help="Local extracted artifact root containing assets/ or pages/. Repeatable.")
    parser.add_argument("--renderer-root", type=Path, default=default_renderer_root())
    parser.add_argument("--write", action="store_true", help="Write output deck.json.")
    parser.add_argument("--no-render", action="store_true", help="With --write, skip HTML rendering.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    args = parser.parse_args()

    config = lark_base.BaseConfig.from_env(
        base_token=args.base_token,
        decks_table=args.decks_table,
        slides_table=args.slides_table,
        profile=args.profile,
        identity=args.identity,
    )
    required = ("base_token", "slides_table") if args.asset_root or args.no_render else ("base_token", "decks_table", "slides_table")
    errors = config.validation_errors(required=required)
    if errors:
        print("compose_materials.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        records = fetch_material_records(config, args.materials)
        deck = build_deck_from_material_records(records, args.title)
    except Exception as exc:
        print(f"compose_materials.py: {exc}", file=sys.stderr)
        return 1

    if not args.write:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "operation": "compose_materials",
                    "title": args.title,
                    "materials": args.materials,
                    "resolved_materials": [
                        {
                            "material_id": record.get("material_id"),
                            "material_code": record.get("material_code"),
                            "title": record.get("title"),
                        }
                        for record in records
                    ],
                    "slide_count": len(deck["slides"]),
                    "quality_summary": quality_summary(records),
                    "quality_warnings": quality_warnings(records),
                    "motion_summary": motion_summary(records),
                    "motion_warnings": motion_warnings(records),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    deck_path = write_deck(deck, args.output_dir)
    asset_roots = [path.resolve() for path in args.asset_root]
    downloaded_asset_roots: list[Path] = []
    if not asset_roots and not args.no_render:
        downloaded_asset_roots = download_asset_roots(
            config,
            deck_ids_from_material_records(records),
            Path(".deck-library-cache") / "material-assets",
        )
        asset_roots.extend(downloaded_asset_roots)
    copy_asset_roots(asset_roots, args.output_dir)
    render_result: dict[str, Any] | str = "skipped"
    if not args.no_render:
        render_result = render_deck(deck_path, args.output_dir, args.renderer_root.resolve())
        if render_result["returncode"] != 0:
            print(f"compose_materials.py: render failed with exit {render_result['returncode']}", file=sys.stderr)
            print(render_result["stderr"], file=sys.stderr)
            return int(render_result["returncode"])

    print(
        json.dumps(
            {
                "mode": "write",
                "operation": "compose_materials",
                "deck_json": str(deck_path),
                "html": str(args.output_dir / "index.html") if render_result != "skipped" else None,
                "slide_count": len(deck["slides"]),
                "materials": args.materials,
                "quality_summary": quality_summary(records),
                "quality_warnings": quality_warnings(records),
                "motion_summary": motion_summary(records),
                "motion_warnings": motion_warnings(records),
                "asset_roots": [str(path) for path in asset_roots],
                "downloaded_asset_roots": [str(path) for path in downloaded_asset_roots],
                "render": render_result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
