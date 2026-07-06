#!/usr/bin/env python3
"""Archive planner and Base writer for feishu-deck-h5 deck outputs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import lark_base


ATTACHMENT_FIELDS = {"cover_thumbnail", "thumbnail", "deck_json", "inline_html", "assets_zip"}
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def load_deck(deck_json: Path) -> dict[str, object]:
    with deck_json.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("slides"), list):
        raise ValueError("deck.json must contain a slides array")
    return data


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_page_thumbnail(output_dir: Path, slide_index: int) -> Path | None:
    for suffix in ("jpg", "jpeg", "png"):
        candidate = output_dir / "pages" / f"page-{slide_index:02d}.{suffix}"
        if candidate.exists():
            return candidate
    return None


def material_code(index: int) -> str:
    return f"M{index:03d}"


def plain_text_from_html(value: object) -> str:
    if not isinstance(value, str):
        return ""
    without_tags = TAG_RE.sub(" ", value)
    return WHITESPACE_RE.sub(" ", html.unescape(without_tags)).strip()


def humanize_key(key: str) -> str:
    return WHITESPACE_RE.sub(" ", key.replace("-", " ").replace("_", " ")).strip()


def describe_slide(slide: dict[str, object], key: str, title: object) -> str:
    data = slide.get("data") if isinstance(slide.get("data"), dict) else {}
    html_text = plain_text_from_html(data.get("html") if isinstance(data, dict) else "")
    alt_text = humanize_key(str(data.get("alt") or "")) if isinstance(data, dict) else ""
    source_page = data.get("source_page") if isinstance(data, dict) else None
    parts = [
        str(title).strip() if title else "",
        html_text,
        humanize_key(key),
        alt_text,
        f"screen {slide.get('screen_label')}" if slide.get("screen_label") else "",
        f"page {source_page}" if source_page else "",
        f"layout: {slide.get('layout', 'raw')}",
        f"key: {key}",
    ]
    return " | ".join(part for part in parts if part)


def chinese_material_fields(
    *,
    slide: dict[str, object],
    key: str,
    title: object,
    page_description: str,
) -> dict[str, str]:
    name = str(title).strip() if title else humanize_key(key)
    layout = str(slide.get("layout", "raw"))
    keywords = "、".join(part for part in [name, humanize_key(key), layout] if part)
    return {
        "素材名称": name,
        "素材描述": f"{name}。{page_description}",
        "适用场景": "汇报材料、客户提案、素材复用",
        "页面价值": f"用于说明{name}相关内容，支持在新演示材料中复用。",
        "视觉类型": layout,
        "关键词": keywords,
    }


def deck_title(deck: dict[str, object], output_dir: Path) -> str:
    meta = deck.get("deck") if isinstance(deck.get("deck"), dict) else {}
    title = meta.get("title") if isinstance(meta, dict) else None
    if isinstance(title, str) and title.strip():
        return title.strip()
    legacy_title = deck.get("title")
    if isinstance(legacy_title, str) and legacy_title.strip():
        return legacy_title.strip()
    return output_dir.parent.name


def chinese_deck_fields(*, title: str, records: list[dict[str, object]]) -> dict[str, str]:
    summaries = [
        str(record.get("素材名称") or record.get("title") or "").strip()
        for record in records[:3]
        if str(record.get("素材名称") or record.get("title") or "").strip()
    ]
    description = f"完整 H5 deck，共 {len(records)} 页。"
    if summaries:
        description += " 主要页面：" + "、".join(summaries) + "。"
    return {
        "中文名称": title,
        "中文描述": description,
        "适用场景": "汇报材料、客户提案、素材复用",
        "推荐用法": "可作为完整 deck 浏览，也可下钻到 Materials 按页复用。",
        "复用范围": "完整复用、页面拆用",
        "链接状态": "待补充线上链接",
    }


def infer_industry_from_deck_name(title: str) -> str:
    rules = [
        ("医院", "医疗"),
        ("医疗", "医疗"),
        ("教育", "教育"),
        ("职校", "教育"),
        ("芯片", "芯片"),
        ("制造", "制造"),
        ("游戏", "游戏"),
        ("餐饮", "餐饮"),
        ("鞋服", "鞋服"),
        ("消费", "消费"),
        ("电商", "电商"),
        ("汽车产业链", "汽车"),
        ("汽车", "汽车"),
    ]
    for marker, industry in rules:
        if marker in title:
            return industry
    return "未分类"


def is_full_bleed_image_replica(slide: dict[str, object]) -> bool:
    data = slide.get("data") if isinstance(slide.get("data"), dict) else {}
    page_image = data.get("page_image") if isinstance(data, dict) else None
    if slide.get("layout") == "replica" and isinstance(page_image, str) and page_image:
        return True
    html_value = data.get("html") if isinstance(data, dict) else ""
    if not isinstance(html_value, str):
        return False
    normalized = html_value.lower()
    return (
        "material-replica" in normalized
        and "<img" in normalized
        and "pages/page-" in normalized
    )


def classify_material_quality(slide: dict[str, object]) -> dict[str, str]:
    if is_full_bleed_image_replica(slide):
        return {
            "material_type": "replica_screenshot",
            "quality_tier": "draft",
            "fidelity_notes": "截图 replica 素材：适合快速预览和组合，正式交付前建议升级为 native H5。",
        }
    return {
        "material_type": "native_h5",
        "quality_tier": "delivery",
        "fidelity_notes": "真实 HTML/CSS 素材：保留文本、布局和样式层，可作为较高质量 H5 交付基础。",
    }


def classify_motion_quality(slide: dict[str, object], quality_fields: dict[str, str]) -> dict[str, object]:
    css = slide.get("custom_css") if isinstance(slide.get("custom_css"), str) else ""
    has_motion = "animation:" in css or "@keyframes" in css
    if quality_fields.get("material_type") != "native_h5" or quality_fields.get("quality_tier") != "delivery":
        return {
            "has_motion": False,
            "motion_tier": "none",
            "motion_notes": "截图或非交付素材默认不加动效；如需高级动效，先升级为 native H5。",
        }
    if has_motion:
        return {
            "has_motion": True,
            "motion_tier": "subtle",
            "motion_notes": "native H5 素材包含 CSS-only 动效，适合高质量 H5 交付。",
        }
    return {
        "has_motion": False,
        "motion_tier": "none",
        "motion_notes": "native H5 素材当前无 bespoke motion；可在高质量交付前添加 subtle CSS motion。",
    }


def artifact_files(output_dir: Path) -> dict[str, str | None]:
    assets_zip = output_dir / "assets.zip"
    has_asset_bundle = any((output_dir / name).exists() for name in ("assets", "pages"))
    return {
        "deck_json": str(output_dir / "deck.json"),
        "inline_html": str(output_dir / "index.html"),
        "assets_zip": str(assets_zip) if assets_zip.exists() or has_asset_bundle else None,
    }


def prepare_artifacts_for_upload(output_dir: Path, artifacts: dict[str, str | None]) -> dict[str, str | None]:
    prepared = dict(artifacts)
    bundle_dirs = [output_dir / name for name in ("assets", "pages")]
    assets_zip = output_dir / "assets.zip"
    if any(path.exists() and path.is_dir() for path in bundle_dirs):
        with zipfile.ZipFile(assets_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive_zip:
            for bundle_dir in bundle_dirs:
                if not bundle_dir.exists() or not bundle_dir.is_dir():
                    continue
                for path in sorted(bundle_dir.rglob("*")):
                    if path.is_file():
                        archive_zip.write(path, path.relative_to(output_dir))
        prepared["assets_zip"] = str(assets_zip)
    elif not assets_zip.exists():
        prepared["assets_zip"] = None
    return prepared


def slide_records(
    deck_id: str,
    deck: dict[str, object],
    output_dir: Path,
    *,
    deck_chinese_name: str | None = None,
    industry: str | None = None,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, slide in enumerate(deck["slides"], start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"slide {index} must be an object")
        key = str(slide.get("key") or f"slide-{index:02d}")
        code = material_code(index)
        data = slide.get("data") if isinstance(slide.get("data"), dict) else {}
        title = data.get("title") if isinstance(data, dict) else None
        thumbnail = find_page_thumbnail(output_dir, index)
        page_description = describe_slide(slide, key, title)
        user_fields = chinese_material_fields(
            slide=slide,
            key=key,
            title=title,
            page_description=page_description,
        )
        quality_fields = classify_material_quality(slide)
        motion_fields = classify_motion_quality(slide, quality_fields)
        records.append(
            {
                "material_id": f"{deck_id}:{code}",
                "material_code": code,
                "slide_id": f"{deck_id}:{key}",
                "deck_id": deck_id,
                "Deck中文名": deck_chinese_name or "",
                "行业": industry or "",
                "slide_key": key,
                "slide_index": index,
                "layout": slide.get("layout", "raw"),
                "screen_label": slide.get("screen_label"),
                "title": title,
                "page_description": page_description,
                "content_summary": title or key,
                "visual_summary": slide.get("layout", "raw"),
                **user_fields,
                **quality_fields,
                **motion_fields,
                "thumbnail": str(thumbnail) if thumbnail else None,
                "slide_payload_json": json.dumps(slide, ensure_ascii=False, separators=(",", ":")),
                "source_artifact_ref": f"base://deck/{deck_id}",
                "status": "active",
            }
        )
    return records


def build_archive_plan(output_dir: Path, deck_id: str | None, *, limit_slides: int | None = None) -> dict[str, object]:
    deck_json = output_dir / "deck.json"
    index_html = output_dir / "index.html"
    if not deck_json.exists():
        raise FileNotFoundError(f"missing required file: {deck_json}")
    if not index_html.exists():
        raise FileNotFoundError(f"missing required file: {index_html}")

    deck = load_deck(deck_json)
    resolved_deck_id = deck_id or f"deck_{file_sha256(deck_json)[:12]}"
    if limit_slides is not None:
        if limit_slides < 1:
            raise ValueError("limit_slides must be greater than 0")
        deck = dict(deck)
        deck["slides"] = deck["slides"][:limit_slides]
    title = deck_title(deck, output_dir)
    industry = infer_industry_from_deck_name(title)
    records = slide_records(resolved_deck_id, deck, output_dir, deck_chinese_name=title, industry=industry)
    cover_thumbnail = records[0].get("thumbnail") if records else None

    return {
        "mode": "plan",
        "operation": "archive",
        "deck_record": {
            "deck_id": resolved_deck_id,
            "title": title,
            **chinese_deck_fields(title=title, records=records),
            "行业": industry,
            "slide_count": len(records),
            "content_hash": file_sha256(deck_json),
            "deck_json": str(deck_json),
            "inline_html": str(index_html),
            "cover_thumbnail": cover_thumbnail,
            "source_run_path": str(output_dir),
            "source": "feishu-deck-h5",
            "validation_status": "unknown",
            "access_status": "draft",
            "link_health": "unknown",
            "quality_tier": "draft",
            "reuse_scope": "页面拆用",
            "status": "archived",
            "version": 1,
        },
        "slide_records": records,
        "artifact_files": artifact_files(output_dir),
        "planned_writes": {
            "feishu_base_decks": 1,
            "feishu_base_slides": len(records),
            "feishu_drive_uploads": ["deck.json", "index.html", "assets.zip if assets/ exists"],
        },
    }


def upload_preview_attachments(
    config: lark_base.BaseConfig,
    *,
    deck_result: dict[str, Any],
    slide_results: list[dict[str, Any]],
    deck_record: dict[str, Any],
    slide_records: list[dict[str, Any]],
) -> dict[str, Any]:
    uploads: dict[str, Any] = {"deck_cover": None, "slides": []}
    deck_record_id = lark_base.extract_upsert_record_id(deck_result)
    cover_thumbnail = deck_record.get("cover_thumbnail")
    if deck_record_id and cover_thumbnail:
        try:
            uploads["deck_cover"] = lark_base.replace_attachment(
                config,
                table_id=config.decks_table,
                record_id=deck_record_id,
                field_id="cover_thumbnail",
                files=[attachment_upload_path(str(cover_thumbnail))],
            )
        except Exception as exc:
            uploads["deck_cover"] = {"uploaded": False, "reason": str(exc)}

    for result, record in zip(slide_results, slide_records):
        record_id = lark_base.extract_upsert_record_id(result)
        thumbnail = record.get("thumbnail")
        if not record_id or not thumbnail:
            uploads["slides"].append(
                {
                    "slide_id": record.get("slide_id"),
                    "uploaded": False,
                    "reason": "missing record_id or thumbnail",
                }
            )
            continue
        try:
            result = lark_base.replace_attachment(
                    config,
                    table_id=config.slides_table,
                    record_id=record_id,
                    field_id="thumbnail",
                    files=[attachment_upload_path(str(thumbnail))],
                )
            uploads["slides"].append(
                {
                    "slide_id": record.get("slide_id"),
                    "uploaded": True,
                    "result": result,
                }
            )
        except Exception as exc:
            uploads["slides"].append(
                {
                    "slide_id": record.get("slide_id"),
                    "uploaded": False,
                    "reason": str(exc),
                }
            )
    return uploads


def upload_deck_artifacts(
    config: lark_base.BaseConfig,
    *,
    deck_result: dict[str, Any],
    artifact_files: dict[str, str | None],
) -> dict[str, Any]:
    uploads: dict[str, Any] = {}
    deck_record_id = lark_base.extract_upsert_record_id(deck_result)
    for field_id in ("deck_json", "inline_html", "assets_zip"):
        local_path = artifact_files.get(field_id)
        if not deck_record_id or not local_path:
            uploads[field_id] = {
                "uploaded": False,
                "reason": "missing record_id or local artifact",
            }
            continue
        try:
            result = lark_base.replace_attachment(
                config,
                table_id=config.decks_table,
                record_id=deck_record_id,
                field_id=field_id,
                files=[attachment_upload_path(str(local_path))],
            )
            uploads[field_id] = {"uploaded": True, "result": result}
        except Exception as exc:
            uploads[field_id] = {"uploaded": False, "reason": str(exc)}
    return uploads


def attachment_upload_path(path: str) -> str:
    return os.path.relpath(path, Path.cwd())


def record_without_attachment_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in ATTACHMENT_FIELDS
    }


def skipped_attachment_results(reason: str) -> dict[str, Any]:
    return {"skipped": True, "reason": reason}


def write_archive_plan(
    config: lark_base.BaseConfig,
    *,
    output_dir: Path,
    plan: dict[str, Any],
    metadata_only: bool = False,
) -> dict[str, Any]:
    deck_record = record_without_attachment_fields(plan["deck_record"])
    slide_records = [
        record_without_attachment_fields(record)
        for record in plan["slide_records"]
    ]
    deck_result = lark_base.upsert_deck(config, deck_record)
    if metadata_only:
        artifact_results: dict[str, Any] = skipped_attachment_results("metadata-only")
    else:
        artifact_results = upload_deck_artifacts(
            config,
            deck_result=deck_result,
            artifact_files=prepare_artifacts_for_upload(output_dir, plan["artifact_files"]),
        )
    slide_results = [
        lark_base.upsert_slide(config, record)
        for record in slide_records
    ]
    if metadata_only:
        attachment_results: dict[str, Any] = skipped_attachment_results("metadata-only")
    else:
        attachment_results = upload_preview_attachments(
            config,
            deck_result=deck_result,
            slide_results=slide_results,
            deck_record=plan["deck_record"],
            slide_records=plan["slide_records"],
        )

    return {
        "mode": "write",
        "operation": "archive",
        "deck_result": deck_result,
        "slide_results": slide_results,
        "artifact_results": artifact_results,
        "attachment_results": attachment_results,
        "written": {
            "decks": 1,
            "slides": len(slide_results),
            "deck_artifacts": 0
            if metadata_only
            else sum(1 for item in artifact_results.values() if item.get("uploaded")),
            "slide_thumbnails": 0
            if metadata_only
            else sum(1 for item in attachment_results["slides"] if item.get("uploaded")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan archiving a deck output into the deck library.")
    parser.add_argument("output_dir", type=Path, help="Directory containing deck.json and index.html.")
    parser.add_argument("--deck-id", help="Stable deck ID to use for the archive record.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing Base/Drive.")
    parser.add_argument("--write", action="store_true", help="Write deck and slide records to Feishu Base.")
    parser.add_argument("--metadata-only", action="store_true", help="Write Decks/Materials metadata only; skip deck artifacts and thumbnails.")
    parser.add_argument("--limit-slides", type=int, help="Archive only the first N slides for smoke tests.")
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--materials-table", "--slides-table", dest="slides_table", help="Materials table ID/name. Defaults to DECK_LIBRARY_SLIDES_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        print("archive.py: choose either --dry-run or --write, not both", file=sys.stderr)
        return 2

    try:
        plan = build_archive_plan(args.output_dir.resolve(), args.deck_id, limit_slides=args.limit_slides)
    except Exception as exc:
        print(f"archive.py: {exc}", file=sys.stderr)
        return 1

    if not args.write:
        plan["mode"] = "dry-run"
        if args.metadata_only:
            plan["attachment_mode"] = "metadata-only"
        print(json.dumps(plan, ensure_ascii=False, indent=2))
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
        print("archive.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        result = write_archive_plan(
            config,
            output_dir=args.output_dir.resolve(),
            plan=plan,
            metadata_only=args.metadata_only,
        )
    except Exception as exc:
        print(f"archive.py: Feishu Base write failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
