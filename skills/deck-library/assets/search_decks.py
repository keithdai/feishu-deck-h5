#!/usr/bin/env python3
"""Search planner and Base query runner for complete deck registry records."""

from __future__ import annotations

import argparse
import json
import sys

import lark_base


SEARCH_FIELDS = [
    "deck_id",
    "中文名称",
    "中文描述",
    "适用场景",
    "title",
    "online_url",
    "deck_type",
    "scene",
    "tags",
    "content_summary",
    "推荐用法",
    "recommended_use",
]

SELECT_FIELDS = [
    "deck_id",
    "中文名称",
    "中文描述",
    "适用场景",
    "推荐用法",
    "复用范围",
    "链接状态",
    "title",
    "online_url",
    "cover_thumbnail",
    "deck_type",
    "source",
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
    "slide_count",
    "deck_json",
    "inline_html",
    "assets_zip",
    "status",
]


def build_filter_json(args: argparse.Namespace) -> dict[str, object] | None:
    conditions: list[object] = []
    if args.tag:
        conditions.extend([["tags", "intersects", tag] for tag in args.tag])
    if args.deck_id:
        conditions.append(["deck_id", "==", args.deck_id])
    if args.scene:
        conditions.append(["scene", "==", args.scene])
    if args.deck_type:
        conditions.append(["deck_type", "==", args.deck_type])
    if args.quality_tier:
        conditions.append(["quality_tier", "==", args.quality_tier])
    if args.access_status:
        conditions.append(["access_status", "==", args.access_status])
    if args.reuse_scope:
        conditions.append(["reuse_scope", "==", args.reuse_scope])
    if args.status:
        conditions.append(["status", "==", args.status])
    if not conditions:
        return None
    return {"logic": "and", "conditions": conditions}


def build_search_plan(args: argparse.Namespace) -> dict[str, object]:
    filters = {
        "query": args.query,
        "deck_id": args.deck_id,
        "tags": args.tag,
        "scene": args.scene,
        "deck_type": args.deck_type,
        "quality_tier": args.quality_tier,
        "access_status": args.access_status,
        "reuse_scope": args.reuse_scope,
        "status": args.status,
        "limit": args.limit,
    }
    return {
        "mode": "dry-run",
        "operation": "search_decks",
        "base_filters": filters,
        "base_query": {
            "search_fields": SEARCH_FIELDS,
            "select_fields": SELECT_FIELDS,
            "filter_json": build_filter_json(args),
        },
        "ranking_order": [
            "ready online_url and access_status match",
            "exact title/deck_type/scene match",
            "recommended_use and content_summary match",
            "tag and reuse_scope match",
        ],
        "result_shape": {
            "deck_id": "deck_20260704_001",
            "中文名称": "完整客户提案 deck",
            "中文描述": "完整 H5 deck，共 12 页。适合客户提案场景。",
            "title": "Example complete deck",
            "online_url": "https://example.com/deck",
            "cover_thumbnail": "base-attachment://cover",
            "deck_type": "pitch deck",
            "scene": "客户提案",
            "recommended_use": "Use as a complete customer proposal baseline",
            "推荐用法": "可直接作为客户提案参考，也可拆页复用。",
            "reuse_scope": "完整复用",
            "复用范围": "完整复用",
            "quality_tier": "delivery",
            "access_status": "ready",
            "link_health": "ok",
            "链接状态": "可访问",
            "reason": "Why this complete deck matched the query",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search complete deck records in the Decks registry.")
    parser.add_argument("query", help="Natural-language query or keyword.")
    parser.add_argument("--deck-id", help="Filter by exact deck_id for deterministic lookup.")
    parser.add_argument("--tag", action="append", default=[], help="Filter by deck tag. Repeatable.")
    parser.add_argument("--scene", help="Filter by deck usage scene.")
    parser.add_argument("--deck-type", help="Filter by complete deck type.")
    parser.add_argument("--quality-tier", help="Filter by deck quality tier.")
    parser.add_argument("--access-status", default="ready", help="Filter by access status. Defaults to ready.")
    parser.add_argument("--reuse-scope", help="Filter by reuse scope.")
    parser.add_argument("--status", default=None, help="Filter by lifecycle status.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum deck candidates to return.")
    parser.add_argument("--dry-run", action="store_true", help="Print the query plan without calling Base.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Accepted for shared config; not required for deck search.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 50:
        print("search_decks.py: --limit must be between 1 and 50", file=sys.stderr)
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
    errors = config.validation_errors(required=("base_token", "decks_table"))
    if errors:
        print("search_decks.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        result = lark_base.search_decks(
            config,
            keyword=args.query,
            search_fields=SEARCH_FIELDS,
            select_fields=SELECT_FIELDS,
            filter_json=build_filter_json(args),
            limit=args.limit,
        )
    except Exception as exc:
        message = str(exc)
        if "OpenAPISearchRecord limited" not in message and "method：OpenAPISearchRecord limited" not in message:
            print(f"search_decks.py: Feishu Base query failed: {exc}", file=sys.stderr)
            return 1
        result = lark_base.list_decks(
            config,
            select_fields=SELECT_FIELDS,
            filter_json=build_filter_json(args),
            limit=args.limit,
        )
        result.setdefault("warnings", []).append(
            "record-search was limited by the platform; fell back to record-list filters without keyword ranking"
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
