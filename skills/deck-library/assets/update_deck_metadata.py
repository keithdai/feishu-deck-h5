#!/usr/bin/env python3
"""Safely update human-maintained metadata fields on Decks records."""

from __future__ import annotations

import argparse
import json
import sys

import lark_base


ALLOWED_FIELDS = {
    "中文名称",
    "中文描述",
    "适用场景",
    "推荐用法",
    "复用范围",
    "链接状态",
    "title",
    "online_url",
    "deck_type",
    "scene",
    "tags",
    "content_summary",
    "recommended_use",
    "reuse_scope",
    "quality_tier",
    "access_status",
    "link_health",
    "last_checked_at",
    "owner",
    "status",
}

PROTECTED_FIELDS = {
    "deck_id",
    "deck_json",
    "inline_html",
    "assets_zip",
    "cover_thumbnail",
    "content_hash",
    "source_run_path",
    "created_at",
    "created_by",
    "version",
}


def parse_set_values(items: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
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
            raise ValueError(f"field is not allowed for deck metadata updates: {key}")
        fields[key] = value
    if not fields:
        raise ValueError("at least one --set field=value pair is required")
    return fields


def build_update_plan(args: argparse.Namespace) -> dict[str, object]:
    fields = parse_set_values(args.set_values)
    return {
        "mode": "write" if args.write else "dry-run",
        "operation": "update_deck_metadata",
        "deck_id": args.deck_id,
        "fields": fields,
        "protected_fields": sorted(PROTECTED_FIELDS),
        "write_requires": ["base_token", "decks_table"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely update Decks metadata fields.")
    parser.add_argument("deck_id", help="Stable deck ID from the Decks table.")
    parser.add_argument("--set", dest="set_values", action="append", default=[], help="Allowed metadata update in field=value format. Repeatable.")
    parser.add_argument("--write", action="store_true", help="Write metadata updates to Feishu Base.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Accepted for shared config; not required.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        plan = build_update_plan(args)
    except ValueError as exc:
        print(f"update_deck_metadata.py: {exc}", file=sys.stderr)
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
    errors = config.validation_errors(required=("base_token", "decks_table"))
    if errors:
        print("update_deck_metadata.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        record_id = lark_base.find_record_id(
            config,
            table_id=config.decks_table,
            key_field="deck_id",
            key_value=args.deck_id,
        )
        if not record_id:
            raise RuntimeError(f"deck_id not found: {args.deck_id}")
        result = lark_base.run_json(
            lark_base.build_record_upsert_command(
                config=config,
                table_id=config.decks_table,
                record_id=record_id,
                fields=plan["fields"],
            )
        )
    except Exception as exc:
        print(f"update_deck_metadata.py: Feishu Base update failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
