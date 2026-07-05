#!/usr/bin/env python3
"""Search planner and Base query runner for the deck material library."""

from __future__ import annotations

import argparse
import json
import sys

import lark_base


SEARCH_FIELDS = ["material_id", "material_code", "title", "page_description", "content_summary", "visual_summary", "slide_key"]
SELECT_FIELDS = [
    "material_id",
    "material_code",
    "slide_id",
    "deck_id",
    "slide_key",
    "slide_index",
    "title",
    "layout",
    "thumbnail",
    "source_artifact_ref",
    "page_description",
    "content_summary",
    "visual_summary",
    "slide_payload_json",
]


def build_filter_json(args: argparse.Namespace) -> dict[str, object] | None:
    conditions: list[list[object]] = []
    if args.tag:
        conditions.append(["tags", "intersects", args.tag])
    if args.layout:
        conditions.append(["layout", "intersects", args.layout])
    if args.scene:
        conditions.append(["scene", "==", args.scene])
    if args.source:
        conditions.append(["source", "==", args.source])
    if args.status:
        conditions.append(["status", "==", args.status])
    if not conditions:
        return None
    return {"logic": "and", "conditions": conditions}


def build_search_plan(args: argparse.Namespace) -> dict[str, object]:
    filters = {
        "query": args.query,
        "tags": args.tag,
        "layouts": args.layout,
        "scene": args.scene,
        "source": args.source,
        "status": args.status,
        "limit": args.limit,
    }
    return {
        "mode": "dry-run",
        "operation": "search",
        "base_filters": filters,
        "base_query": {
            "search_fields": SEARCH_FIELDS,
            "select_fields": SELECT_FIELDS,
            "filter_json": build_filter_json(args),
        },
        "ranking_order": [
            "exact slide_key/title match",
            "tag/layout/scene match",
            "content_summary text match",
            "visual_summary text match",
        ],
        "result_shape": {
            "material_id": "deck_20260704_001:M001",
            "material_code": "M001",
            "slide_id": "deck_20260704_001:intro",
            "deck_id": "deck_20260704_001",
            "title": "Example slide title",
            "page_description": "What this material page explains and when to use it",
            "layout": "raw",
            "thumbnail": "drive://thumbnail-or-base-attachment",
            "source_artifact_ref": "base://deck/deck_20260704_001",
            "slide_payload_json": "{...}",
            "reason": "Why this candidate matched the query",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a deck-library search query.")
    parser.add_argument("query", help="Natural-language query or keyword.")
    parser.add_argument("--tag", action="append", default=[], help="Filter by tag. Repeatable.")
    parser.add_argument("--layout", action="append", default=[], help="Filter by layout. Repeatable.")
    parser.add_argument("--scene", help="Filter by usage scene.")
    parser.add_argument("--source", help="Filter by deck source.")
    parser.add_argument("--status", default="active", help="Slide status to include.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum candidates to return.")
    parser.add_argument("--dry-run", action="store_true", help="Print the query plan without calling Base.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name. Defaults to DECK_LIBRARY_SLIDES_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 20:
        print("search.py: --limit must be between 1 and 20", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(build_search_plan(args), ensure_ascii=False, indent=2))
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
        print("search.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        result = lark_base.search_slides(
            config,
            keyword=args.query,
            search_fields=SEARCH_FIELDS,
            select_fields=SELECT_FIELDS,
            filter_json=build_filter_json(args),
            limit=args.limit,
        )
    except Exception as exc:
        print(f"search.py: Feishu Base query failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
