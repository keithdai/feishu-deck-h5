#!/usr/bin/env python3
"""List page materials that belong to one complete deck record."""

from __future__ import annotations

import argparse
import json
import sys

import lark_base


SEARCH_FIELDS = ["deck_id", "material_id", "material_code", "title", "素材名称", "素材描述", "slide_key"]

SELECT_FIELDS = [
    "material_id",
    "material_code",
    "素材名称",
    "素材描述",
    "适用场景",
    "页面价值",
    "视觉类型",
    "关键词",
    "thumbnail",
    "slide_id",
    "deck_id",
    "slide_key",
    "slide_index",
    "title",
    "page_description",
    "layout",
    "tags",
    "scene",
    "content_summary",
    "visual_summary",
    "material_type",
    "quality_tier",
    "reuse_status",
    "edit_notes",
    "page_role",
    "is_representative_page",
    "has_motion",
    "motion_tier",
    "motion_notes",
    "slide_payload_json",
    "source_artifact_ref",
    "content_hash",
    "status",
]


def build_filter_json(args: argparse.Namespace) -> dict[str, object]:
    conditions: list[list[object]] = [["deck_id", "==", args.deck_id]]
    if not args.include_hidden and args.status:
        conditions.append(["status", "==", args.status])
    return {"logic": "and", "conditions": conditions}


def build_list_plan(args: argparse.Namespace) -> dict[str, object]:
    return {
        "mode": "dry-run",
        "operation": "list_deck_materials",
        "deck_id": args.deck_id,
        "base_query": {
            "keyword": args.deck_id,
            "search_fields": SEARCH_FIELDS,
            "select_fields": SELECT_FIELDS,
            "filter_json": build_filter_json(args),
            "sort_json": [{"field": "slide_index", "desc": False}],
            "limit": args.limit,
        },
        "presentation_order": "slide_index ascending",
        "result_shape": {
            "deck_id": args.deck_id,
            "slide_index": 1,
            "material_code": "M001",
            "素材名称": "封面页",
            "素材描述": "Human-facing page description",
            "reuse_status": "可直接复用",
            "edit_notes": "What to adjust before reuse",
            "slide_payload_json": "{...}",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List page materials for one complete deck.")
    parser.add_argument("deck_id", help="Stable deck ID from the Decks table.")
    parser.add_argument("--status", default="active", help="Material status to include. Defaults to active.")
    parser.add_argument("--include-hidden", action="store_true", help="Do not filter by material status.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum materials to return.")
    parser.add_argument("--dry-run", action="store_true", help="Print the query plan without calling Base.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Accepted for shared config; not required for material drill-down.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name. Defaults to DECK_LIBRARY_SLIDES_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 200:
        print("list_deck_materials.py: --limit must be between 1 and 200", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(build_list_plan(args), ensure_ascii=False, indent=2))
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
        print("list_deck_materials.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        result = lark_base.run_json(
            lark_base.build_record_list_command(
                config=config,
                table_id=config.slides_table,
                select_fields=SELECT_FIELDS,
                filter_json=build_filter_json(args),
                sort_json=[{"field": "slide_index", "desc": False}],
                limit=args.limit,
            )
        )
    except Exception as exc:
        print(f"list_deck_materials.py: Feishu Base query failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
