#!/usr/bin/env python3
"""Plan or apply Base schema/view improvements for deck-library."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import lark_base


DECK_VISIBLE_FIELDS = [
    "cover_thumbnail",
    "中文名称",
    "行业",
    "中文描述",
    "适用场景",
    "推荐用法",
    "复用范围",
    "链接状态",
    "online_url",
    "owner",
    "quality_tier",
    "access_status",
    "link_health",
    "last_checked_at",
    "slide_count",
    "deck_id",
    "title",
    "deck_type",
    "scene",
    "tags",
    "recommended_use",
    "reuse_scope",
    "source",
    "status",
    "validation_status",
    "created_at",
    "created_by",
    "version",
    "theme",
    "accent",
    "content_summary",
    "source_run_path",
    "content_hash",
    "deck_json",
    "inline_html",
    "assets_zip",
]

MATERIAL_VISIBLE_FIELDS = [
    "thumbnail",
    "Deck中文名",
    "行业",
    "素材名称",
    "素材描述",
    "page_role",
    "reuse_status",
    "material_code",
    "slide_index",
    "关联Deck",
    "适用场景",
    "页面价值",
    "视觉类型",
    "关键词",
    "edit_notes",
    "is_representative_page",
    "quality_tier",
    "status",
    "deck_id",
    "material_id",
    "material_type",
    "fidelity_notes",
    "motion_tier",
    "motion_notes",
    "title",
    "page_description",
    "layout",
    "slide_key",
    "slide_payload_json",
    "source_artifact_ref",
    "content_hash",
]


def text_field(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "type": "text", "description": description}


def number_field(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "type": "number", "description": description}


def checkbox_field(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "type": "checkbox", "description": description}


def attachment_field(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "type": "attachment", "description": description}


def deck_fields() -> list[dict[str, Any]]:
    return [
        text_field("deck_id", "Stable deck key used by automation."),
        text_field("中文名称", "Human-facing Chinese deck title for Base browsing."),
        text_field("行业", "Inferred or human-maintained industry label for deck/material picking."),
        text_field("中文描述", "完整 deck 的中文说明，供人工浏览和 Agent 检索。"),
        text_field("推荐用法", "说明适合谁、什么时候用、怎么复用。"),
        text_field("适用场景", "逗号或顿号分隔的中文场景标签，保持与 CLI 字符串写入兼容。"),
        text_field("复用范围", "完整复用、页面拆用或仅参考；保持文本字段避免自动写入类型不匹配。"),
        text_field("链接状态", "线上链接的人类可读状态。"),
        text_field("title", "Human-readable deck title."),
        text_field("online_url", "Direct online link for the complete deck."),
        text_field("deck_type", "Complete deck type such as pitch deck or 客户提案."),
        text_field("source", "Deck source such as feishu-deck-h5."),
        text_field("scene", "Usage scene."),
        text_field("tags", "Comma/顿号-separated search tags."),
        text_field("recommended_use", "How the complete deck should be reused or referenced."),
        text_field("reuse_scope", "完整复用、页面拆用 or 仅参考."),
        text_field("access_status", "ready、draft、broken 或 deprecated。"),
        text_field("quality_tier", "draft、standard 或 delivery。"),
        text_field("link_health", "unknown、ok 或 failed。"),
        text_field("last_checked_at", "Last time the online link was checked."),
        number_field("slide_count", "Count from deck.json.slides."),
        text_field("theme", "Palette/style summary."),
        text_field("accent", "Primary accent color if known."),
        text_field("content_summary", "Compact deck summary for search."),
        text_field("source_run_path", "Local provenance/debug path only."),
        text_field("content_hash", "Hash of deck.json and artifact manifest for dedupe."),
        text_field("validation_status", "unknown、passed、warning or failed."),
        attachment_field("deck_json", "Original deck.json source of truth."),
        attachment_field("assets_zip", "Zipped assets/pages bundle."),
        attachment_field("inline_html", "Rendered HTML preview/handoff."),
        attachment_field("cover_thumbnail", "First-slide thumbnail for gallery view."),
        text_field("created_at", "Archive time."),
        text_field("owner", "Person or team responsible for the complete deck."),
        text_field("created_by", "User who archived the deck."),
        number_field("version", "Archive version."),
        text_field("status", "draft、final、archived or deprecated."),
    ]


def material_fields(decks_table: str) -> list[dict[str, Any]]:
    return [
        text_field("material_id", "Stable material ID: <deck_id>:<material_code>."),
        text_field("material_code", "Short human-facing selector such as M001."),
        text_field("素材名称", "Chinese human-facing material name."),
        text_field("素材描述", "Chinese material description."),
        text_field("slide_id", "Stable slide ID: <deck_id>:<slide_key>."),
        text_field("deck_id", "Stable deck key used by automation."),
        text_field("Deck中文名", "Denormalized Chinese deck title for browsing Materials without opening the linked Deck."),
        text_field("行业", "Inferred or human-maintained industry label copied from the source Deck."),
        {"name": "关联Deck", "type": "link", "link_table": decks_table, "description": "可选人工关联字段；deck_id 文本键仍是自动化主键。"},
        text_field("适用场景", "逗号或顿号分隔的中文场景标签。"),
        text_field("页面价值", "Chinese explanation of what this page helps communicate or decide."),
        text_field("视觉类型", "页面视觉类型，保持与 archive.py 的 layout 字符串兼容。"),
        text_field("关键词", "Chinese/English keywords and synonyms for retrieval."),
        text_field("slide_key", "Value from deck.json.slides[].key."),
        number_field("slide_index", "1-based frame index in the source deck."),
        text_field("title", "Visible slide title when available."),
        text_field("page_description", "Searchable page description."),
        text_field("layout", "Layout name from deck.json."),
        text_field("screen_label", "Display-only screen label."),
        text_field("tags", "Comma/顿号-separated slide tags."),
        text_field("scene", "Slide-specific usage scenario."),
        text_field("content_summary", "Compact summary for search/ranking."),
        text_field("visual_summary", "Visual description from screenshot or layout metadata."),
        text_field("material_type", "replica_screenshot or native_h5."),
        text_field("quality_tier", "draft、standard or delivery."),
        text_field("reuse_status", "可直接复用、需轻改、仅参考或不建议复用。"),
        text_field("edit_notes", "Human-maintained notes describing what to adjust before reuse."),
        text_field("page_role", "封面、目录、问题定义、方案、案例、数据页或收尾。"),
        checkbox_field("is_representative_page", "True when this page is a strong preview card."),
        text_field("fidelity_notes", "Explanation of reuse limits and native H5 upgrade recommendations."),
        checkbox_field("has_motion", "True when the material has validated CSS-only bespoke motion."),
        text_field("motion_tier", "none、subtle 或 expressive。"),
        text_field("motion_notes", "Explanation of motion behavior or exclusion."),
        text_field("theme", "Palette/style summary."),
        text_field("accent", "Slide accent color if known."),
        attachment_field("thumbnail", "Per-slide screenshot."),
        text_field("slide_payload_json", "Low-level slide JSON copied from deck.json."),
        text_field("source_artifact_ref", "Stable reference such as base://deck/<deck_id>."),
        text_field("content_hash", "Hash of slide payload and dependencies."),
        text_field("status", "active、hidden or deprecated."),
    ]


def build_migration_plan(base_token: str, decks_table: str, materials_table: str) -> dict[str, Any]:
    return {
        "operation": "migrate_schema",
        "base_token_configured": bool(base_token),
        "tables": {"decks": decks_table, "materials": materials_table},
        "fields": {
            "decks": deck_fields(),
            "materials": material_fields(decks_table),
        },
        "visible_fields": {
            "decks": DECK_VISIBLE_FIELDS,
            "materials": MATERIAL_VISIBLE_FIELDS,
        },
        "views": {
            "decks": [
                {"name": "表格", "type": "grid", "filter": {"conditions": []}},
                {"name": "可直接使用", "type": "grid", "filter": {"logic": "and", "conditions": [["access_status", "==", "ready"]]}},
                {"name": "待补链接", "type": "grid", "filter": {"logic": "or", "conditions": [["link_health", "==", "failed"], ["online_url", "empty"]]}},
                {"name": "测试样本", "type": "grid", "filter": {"logic": "and", "conditions": [["中文名称", "intersects", "测试"]]}},
                {"name": "Deck Covers", "type": "gallery", "filter": {"conditions": []}},
            ],
            "materials": [
                {"name": "Grid View", "type": "grid", "filter": {"conditions": []}},
                {"name": "Slides Gallery", "type": "gallery", "filter": {"conditions": []}},
                {"name": "Materials Gallery", "type": "gallery", "filter": {"logic": "and", "conditions": [["status", "==", "active"]]}},
                {
                    "name": "挑页｜按Deck",
                    "type": "grid",
                    "filter": {"logic": "and", "conditions": [["status", "==", "active"]]},
                    "group": {"group_config": [{"field": "Deck中文名", "desc": False}, {"field": "page_role", "desc": False}, {"field": "reuse_status", "desc": False}]},
                    "sort": [{"field": "Deck中文名", "desc": False}, {"field": "slide_index", "desc": False}],
                },
                {
                    "name": "挑页｜按行业",
                    "type": "grid",
                    "filter": {"logic": "and", "conditions": [["status", "==", "active"]]},
                    "group": {"group_config": [{"field": "行业", "desc": False}, {"field": "page_role", "desc": False}, {"field": "reuse_status", "desc": False}]},
                    "sort": [{"field": "行业", "desc": False}, {"field": "slide_index", "desc": False}],
                },
                {
                    "name": "挑页｜可复用",
                    "type": "grid",
                    "filter": {"logic": "and", "conditions": [["status", "==", "active"]]},
                    "group": {"group_config": [{"field": "reuse_status", "desc": False}, {"field": "行业", "desc": False}, {"field": "page_role", "desc": False}]},
                    "sort": [{"field": "reuse_status", "desc": False}, {"field": "slide_index", "desc": False}],
                },
                {"name": "按Deck下钻", "type": "grid", "filter": {"logic": "and", "conditions": [["status", "==", "active"]]}},
                {"name": "可直接复用页面", "type": "grid", "filter": {"logic": "and", "conditions": [["reuse_status", "==", "可直接复用"]]}},
                {"name": "代表页", "type": "gallery", "filter": {"logic": "and", "conditions": [["is_representative_page", "==", True]]}},
            ],
        },
    }


def collect_names(result: dict[str, Any], *, kind: str) -> set[str]:
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    candidates = data.get("items") or data.get("fields") or data.get("views") or []
    names: set[str] = set()
    if not isinstance(candidates, list):
        return names
    for item in candidates:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("field_name") or item.get("view_name")
        if name:
            names.add(str(name))
    return names


def collect_field_ids(result: dict[str, Any]) -> dict[str, str]:
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    candidates = data.get("items") or data.get("fields") or []
    field_ids: dict[str, str] = {}
    if not isinstance(candidates, list):
        return field_ids
    for item in candidates:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("field_name")
        field_id = item.get("id") or item.get("field_id")
        if name and field_id:
            field_ids[str(name)] = str(field_id)
    return field_ids


def call_or_noop(function):
    try:
        return function()
    except Exception as exc:
        message = str(exc)
        if "no operation produced" in message:
            return {"action": "noop", "reason": message}
        raise


def set_view_visible_fields_ordered(
    config: lark_base.BaseConfig,
    *,
    table_id: str,
    view_id: str,
    visible_fields: list[str],
) -> dict[str, Any]:
    if len(visible_fields) > 3:
        # Some Base views report "no operation produced" when expanding from an
        # all-fields default. Shrinking first makes the subsequent ordered write stick.
        call_or_noop(
            lambda: lark_base.set_view_visible_fields(
                config,
                table_id=table_id,
                view_id=view_id,
                visible_fields=visible_fields[:3],
            )
        )
        # Expanding directly from a short prefix to the full list can also be
        # treated as a no-op by Base for existing views. Grow the visible prefix
        # in chunks so both visibility and order are persisted reliably.
        for length in range(6, len(visible_fields), 6):
            call_or_noop(
                lambda length=length: lark_base.set_view_visible_fields(
                    config,
                    table_id=table_id,
                    view_id=view_id,
                    visible_fields=visible_fields[:length],
                )
            )
            time.sleep(0.8)
    return call_or_noop(
        lambda: lark_base.set_view_visible_fields(
            config,
            table_id=table_id,
            view_id=view_id,
            visible_fields=visible_fields,
        )
    )


def apply_plan(config: lark_base.BaseConfig, plan: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fields": {"decks": [], "materials": []}, "views": {"decks": [], "materials": []}}
    table_ids = {"decks": config.decks_table, "materials": config.slides_table}

    for table_key, table_id in table_ids.items():
        field_result = lark_base.list_fields(config, table_id=table_id)
        existing_fields = collect_names(field_result, kind="field")
        field_ids = collect_field_ids(field_result)
        for field in plan["fields"][table_key]:
            if field["name"] in existing_fields:
                results["fields"][table_key].append({"name": field["name"], "action": "skip_existing"})
                continue
            results["fields"][table_key].append(
                {
                    "name": field["name"],
                    "action": "created",
                    "result": call_or_noop(lambda field=field, table_id=table_id: lark_base.create_field(config, table_id=table_id, field=field)),
                }
            )

            field_result = lark_base.list_fields(config, table_id=table_id)
            field_ids = collect_field_ids(field_result)
        existing_views = collect_names(lark_base.list_views(config, table_id=table_id), kind="view")
        for view in plan["views"][table_key]:
            view_name = view["name"]
            action = "skip_existing"
            if view_name not in existing_views:
                call_or_noop(lambda view=view, table_id=table_id: lark_base.create_view(config, table_id=table_id, view={"name": view_name, "type": view.get("type", "grid")}))
                action = "created"
            visible_fields = [
                field_ids.get(field_name, field_name)
                for field_name in plan["visible_fields"][table_key]
            ]
            visible_result = call_or_noop(
                lambda table_id=table_id, view_name=view_name, visible_fields=visible_fields: set_view_visible_fields_ordered(
                    config,
                    table_id=table_id,
                    view_id=view_name,
                    visible_fields=visible_fields,
                )
            )
            filter_json = view.get("filter") or {"conditions": []}
            filter_result = call_or_noop(
                lambda table_id=table_id, view_name=view_name, filter_json=filter_json: lark_base.set_view_filter(
                    config,
                    table_id=table_id,
                    view_id=view_name,
                    filter_json=filter_json,
                )
            )
            group_result = None
            if "group" in view:
                group_result = call_or_noop(
                    lambda table_id=table_id, view_name=view_name, view=view: lark_base.set_view_group(
                        config,
                        table_id=table_id,
                        view_id=view_name,
                        group_json=view["group"],
                    )
                )
            sort_result = None
            if "sort" in view:
                sort_result = call_or_noop(
                    lambda table_id=table_id, view_name=view_name, view=view: lark_base.set_view_sort(
                        config,
                        table_id=table_id,
                        view_id=view_name,
                        sort_json=view["sort"],
                    )
                )
            results["views"][table_key].append(
                {
                    "name": view_name,
                    "action": action,
                    "visible_fields": visible_result,
                    "filter": filter_result,
                    "group": group_result,
                    "sort": sort_result,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply deck-library Base schema and view improvements.")
    parser.add_argument("--dry-run", action="store_true", help="Print the migration plan without writing.")
    parser.add_argument("--write", action="store_true", help="Create missing fields/views and update view configuration.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        print("migrate_schema.py: choose either --dry-run or --write, not both", file=sys.stderr)
        return 2

    config = lark_base.BaseConfig.from_env(
        base_token=args.base_token,
        decks_table=args.decks_table,
        slides_table=args.slides_table,
        profile=args.profile,
        identity=args.identity,
    )
    plan = build_migration_plan(config.base_token, config.decks_table, config.slides_table)

    if not args.write:
        plan["mode"] = "dry-run"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    errors = config.validation_errors()
    if errors:
        print("migrate_schema.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        results = apply_plan(config, plan)
    except Exception as exc:
        print(f"migrate_schema.py: Base migration failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"mode": "write", "operation": "migrate_schema", "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
