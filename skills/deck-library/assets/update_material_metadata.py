#!/usr/bin/env python3
"""Safely update human-maintained metadata fields on Materials records."""

from __future__ import annotations

import argparse
import json
import sys

import lark_base


ALLOWED_FIELDS = {
    "素材名称",
    "素材描述",
    "适用场景",
    "页面价值",
    "视觉类型",
    "关键词",
    "title",
    "page_description",
    "content_summary",
    "visual_summary",
    "tags",
    "scene",
    "quality_tier",
    "reuse_status",
    "edit_notes",
    "page_role",
    "is_representative_page",
    "status",
}

PROTECTED_FIELDS = {
    "material_id",
    "material_code",
    "slide_id",
    "deck_id",
    "slide_key",
    "slide_index",
    "thumbnail",
    "slide_payload_json",
    "source_artifact_ref",
    "content_hash",
    "layout",
    "material_type",
}


CHECKBOX_FIELDS = {"is_representative_page"}


def parse_field_value(key: str, value: str) -> str | bool:
    if key not in CHECKBOX_FIELDS:
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"checkbox field requires true/false value: {key}")


def parse_set_values(items: list[str]) -> dict[str, str | bool]:
    fields: dict[str, str | bool] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--set must use field=value format: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--set field name cannot be empty")
        if key in PROTECTED_FIELDS:
            raise ValueError(f"protected field cannot be updated by metadata command: {key}")
        if key not in ALLOWED_FIELDS:
            raise ValueError(f"field is not allowed for material metadata updates: {key}")
        fields[key] = parse_field_value(key, value)
    if not fields:
        raise ValueError("at least one --set field=value pair is required")
    return fields


def build_update_plan(args: argparse.Namespace) -> dict[str, object]:
    fields = parse_set_values(args.set_values)
    return {
        "mode": "write" if args.write else "dry-run",
        "operation": "update_material_metadata",
        "identifier": args.identifier,
        "fields": fields,
        "protected_fields": sorted(PROTECTED_FIELDS),
        "write_requires": ["base_token", "slides_table"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely update Materials metadata fields.")
    parser.add_argument("identifier", help="Material ID or material code, e.g. deck_20260704_001:M001 or M001.")
    parser.add_argument("--set", dest="set_values", action="append", default=[], help="Allowed metadata update in field=value format. Repeatable.")
    parser.add_argument("--write", action="store_true", help="Write metadata updates to Feishu Base.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Accepted for shared config; not required.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name. Defaults to DECK_LIBRARY_SLIDES_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        plan = build_update_plan(args)
    except ValueError as exc:
        print(f"update_material_metadata.py: {exc}", file=sys.stderr)
        return 1

    if not args.write:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    config = lark_base.BaseConfig.from_env(
        base_token=args.base_token,
        decks_table=args.decks_table,
        slides_table=args.slides_table,
        profile=args.profile,
        identity=args.identity,
    )
    errors = config.validation_errors(required=("base_token", "slides_table"))
    if errors:
        print("update_material_metadata.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        lookup_command = lark_base.build_material_lookup_command(
            config=config,
            table_id=config.slides_table,
            identifier=args.identifier,
            select_fields=["material_id", "material_code"],
        )
        record_id = lark_base.extract_single_record_id(lark_base.run_json(lookup_command))
        if not record_id:
            raise RuntimeError(f"material not found: {args.identifier}")
        result = lark_base.run_json(
            lark_base.build_record_upsert_command(
                config=config,
                table_id=config.slides_table,
                record_id=record_id,
                fields=plan["fields"],
            )
        )
    except Exception as exc:
        print(f"update_material_metadata.py: Feishu Base update failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
