#!/usr/bin/env python3
"""Thin lark-cli Base wrapper for deck-library commands."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any


DEFAULT_PROFILE = "bytedance"
DEFAULT_IDENTITY = "user"
COMMAND_TIMEOUT_SECONDS: float | None = None


@dataclass(frozen=True)
class BaseConfig:
    base_token: str
    decks_table: str
    slides_table: str
    profile: str = DEFAULT_PROFILE
    identity: str = DEFAULT_IDENTITY

    @classmethod
    def from_env(
        cls,
        *,
        base_token: str | None = None,
        decks_table: str | None = None,
        slides_table: str | None = None,
        profile: str | None = None,
        identity: str | None = None,
    ) -> "BaseConfig":
        return cls(
            base_token=base_token or os.environ.get("DECK_LIBRARY_BASE_TOKEN", ""),
            decks_table=decks_table or os.environ.get("DECK_LIBRARY_DECKS_TABLE", ""),
            slides_table=slides_table or os.environ.get("DECK_LIBRARY_SLIDES_TABLE", ""),
            profile=profile or os.environ.get("DECK_LIBRARY_LARK_PROFILE", DEFAULT_PROFILE),
            identity=identity or os.environ.get("DECK_LIBRARY_LARK_AS", DEFAULT_IDENTITY),
        )

    def validation_errors(self, required: tuple[str, ...] = ("base_token", "decks_table", "slides_table")) -> list[str]:
        errors: list[str] = []
        if "base_token" in required and not self.base_token:
            errors.append("base_token is required")
        if "decks_table" in required and not self.decks_table:
            errors.append("decks_table is required")
        if "slides_table" in required and not self.slides_table:
            errors.append("slides_table is required")
        if self.identity not in {"user", "bot"}:
            errors.append("identity must be user or bot")
        return errors


def _base_command(config: BaseConfig, shortcut: str) -> list[str]:
    return [
        "lark-cli",
        "--profile",
        config.profile,
        "base",
        shortcut,
        "--as",
        config.identity,
        "--base-token",
        config.base_token,
    ]


def build_record_upsert_command(
    *,
    config: BaseConfig,
    table_id: str,
    fields: dict[str, Any],
    record_id: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-upsert")
    command.extend(
        [
            "--table-id",
            table_id,
            "--json",
            json.dumps(fields, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if record_id:
        command.extend(["--record-id", record_id])
    if dry_run:
        command.append("--dry-run")
    return command


def build_record_search_command(
    *,
    config: BaseConfig,
    table_id: str,
    keyword: str,
    search_fields: list[str],
    select_fields: list[str] | None = None,
    filter_json: dict[str, Any] | None = None,
    limit: int = 8,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-search")
    command.extend(["--table-id", table_id, "--keyword", keyword])
    for field in search_fields:
        command.extend(["--search-field", field])
    for field in select_fields or []:
        command.extend(["--field-id", field])
    if filter_json:
        command.extend(["--filter-json", json.dumps(filter_json, ensure_ascii=False, separators=(",", ":"))])
    command.extend(["--limit", str(limit), "--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_record_list_command(
    *,
    config: BaseConfig,
    table_id: str,
    select_fields: list[str] | None = None,
    filter_json: dict[str, Any] | None = None,
    sort_json: list[dict[str, Any]] | None = None,
    limit: int = 100,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-list")
    command.extend(["--table-id", table_id])
    for field in select_fields or []:
        command.extend(["--field-id", field])
    if filter_json:
        command.extend(["--filter-json", json.dumps(filter_json, ensure_ascii=False, separators=(",", ":"))])
    if sort_json:
        command.extend(["--sort-json", json.dumps(sort_json, ensure_ascii=False, separators=(",", ":"))])
    command.extend(["--limit", str(limit), "--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_find_record_command(
    *,
    config: BaseConfig,
    table_id: str,
    key_field: str,
    key_value: str,
    dry_run: bool = False,
) -> list[str]:
    return build_record_list_command(
        config=config,
        table_id=table_id,
        select_fields=[key_field],
        filter_json={"logic": "and", "conditions": [[key_field, "==", key_value]]},
        limit=2,
        dry_run=dry_run,
    )


def build_material_lookup_command(
    *,
    config: BaseConfig,
    table_id: str,
    identifier: str,
    select_fields: list[str],
    dry_run: bool = False,
) -> list[str]:
    return build_record_list_command(
        config=config,
        table_id=table_id,
        select_fields=select_fields,
        filter_json={
            "logic": "or",
            "conditions": [["material_id", "==", identifier], ["material_code", "==", identifier]],
        },
        limit=2,
        dry_run=dry_run,
    )


def build_upload_attachment_command(
    *,
    config: BaseConfig,
    table_id: str,
    record_id: str,
    field_id: str,
    files: list[str],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-upload-attachment")
    command.extend(
        [
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--field-id",
            field_id,
        ]
    )
    for file_path in files:
        command.extend(["--file", file_path])
    command.extend(["--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_record_get_command(
    *,
    config: BaseConfig,
    table_id: str,
    record_id: str,
    field_id: str,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-get")
    command.extend(
        [
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--field-id",
            field_id,
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def build_remove_attachment_command(
    *,
    config: BaseConfig,
    table_id: str,
    record_id: str,
    field_id: str,
    file_tokens: list[str],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-remove-attachment")
    command.extend(
        [
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--field-id",
            field_id,
        ]
    )
    for file_token in file_tokens:
        command.extend(["--file-token", file_token])
    command.extend(["--yes", "--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_download_attachment_command(
    *,
    config: BaseConfig,
    table_id: str,
    record_id: str,
    file_tokens: list[str],
    output: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+record-download-attachment")
    command.extend(
        [
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--output",
            output,
        ]
    )
    for file_token in file_tokens:
        command.extend(["--file-token", file_token])
    if overwrite:
        command.append("--overwrite")
    command.extend(["--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_field_create_command(
    *,
    config: BaseConfig,
    table_id: str,
    field: dict[str, Any],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+field-create")
    command.extend(
        [
            "--table-id",
            table_id,
            "--json",
            json.dumps(field, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if field.get("type") == "lookup":
        command.append("--i-have-read-guide")
    if dry_run:
        command.append("--dry-run")
    return command


def build_field_list_command(
    *,
    config: BaseConfig,
    table_id: str,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+field-list")
    command.extend(["--table-id", table_id, "--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_create_command(
    *,
    config: BaseConfig,
    table_id: str,
    view: dict[str, Any],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-create")
    command.extend(
        [
            "--table-id",
            table_id,
            "--json",
            json.dumps(view, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_list_command(
    *,
    config: BaseConfig,
    table_id: str,
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-list")
    command.extend(["--table-id", table_id, "--format", "json"])
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_set_visible_fields_command(
    *,
    config: BaseConfig,
    table_id: str,
    view_id: str,
    visible_fields: list[str],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-set-visible-fields")
    command.extend(
        [
            "--table-id",
            table_id,
            "--view-id",
            view_id,
            "--json",
            json.dumps({"visible_fields": visible_fields}, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_set_filter_command(
    *,
    config: BaseConfig,
    table_id: str,
    view_id: str,
    filter_json: dict[str, Any],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-set-filter")
    command.extend(
        [
            "--table-id",
            table_id,
            "--view-id",
            view_id,
            "--json",
            json.dumps(filter_json, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_set_group_command(
    *,
    config: BaseConfig,
    table_id: str,
    view_id: str,
    group_json: dict[str, Any],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-set-group")
    command.extend(
        [
            "--table-id",
            table_id,
            "--view-id",
            view_id,
            "--json",
            json.dumps(group_json, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def build_view_set_sort_command(
    *,
    config: BaseConfig,
    table_id: str,
    view_id: str,
    sort_json: list[dict[str, Any]],
    dry_run: bool = False,
) -> list[str]:
    command = _base_command(config, "+view-set-sort")
    command.extend(
        [
            "--table-id",
            table_id,
            "--view-id",
            view_id,
            "--json",
            json.dumps({"sort_config": sort_json}, ensure_ascii=False, separators=(",", ":")),
            "--format",
            "json",
        ]
    )
    if dry_run:
        command.append("--dry-run")
    return command


def run_json(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"lark-cli command timed out after {exc.timeout}s") from exc
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        json_start = completed.stdout.find("{")
        if json_start < 0:
            raise RuntimeError(f"lark-cli returned non-JSON output: {completed.stdout[:200]}") from exc
        try:
            parsed = json.loads(completed.stdout[json_start:])
        except json.JSONDecodeError as nested_exc:
            raise RuntimeError(f"lark-cli returned non-JSON output: {completed.stdout[:200]}") from nested_exc
    if not isinstance(parsed, dict):
        raise RuntimeError("lark-cli JSON output must be an object")
    return parsed


def extract_single_record_id(result: dict[str, Any]) -> str | None:
    data = result.get("data")
    if not isinstance(data, dict):
        return None
    record_ids = data.get("record_id_list") or []
    if not isinstance(record_ids, list):
        return None
    if len(record_ids) > 1:
        raise RuntimeError(f"business key matched multiple records: {record_ids}")
    return str(record_ids[0]) if record_ids else None


def extract_upsert_record_id(result: dict[str, Any]) -> str | None:
    if result.get("record_id"):
        return str(result["record_id"])
    data = result.get("data")
    if not isinstance(data, dict):
        return None
    record_id = data.get("record_id")
    if record_id:
        return str(record_id)
    record = data.get("record")
    if isinstance(record, dict):
        if record.get("record_id"):
            return str(record["record_id"])
        record_ids = record.get("record_id_list") or []
        if isinstance(record_ids, list):
            if len(record_ids) > 1:
                raise RuntimeError(f"upsert returned multiple records: {record_ids}")
            return str(record_ids[0]) if record_ids else None
    return None


def extract_attachment_tokens(result: dict[str, Any]) -> list[str]:
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get("data")
    if not isinstance(rows, list) or not rows:
        return []
    first_row = rows[0]
    if not isinstance(first_row, list) or not first_row:
        return []
    attachments = first_row[0]
    if not isinstance(attachments, list):
        return []
    return [
        str(item["file_token"])
        for item in attachments
        if isinstance(item, dict) and item.get("file_token")
    ]


def find_record_id(
    config: BaseConfig,
    *,
    table_id: str,
    key_field: str,
    key_value: str,
) -> str | None:
    command = build_find_record_command(
        config=config,
        table_id=table_id,
        key_field=key_field,
        key_value=key_value,
    )
    return extract_single_record_id(run_json(command))


def upsert_deck(config: BaseConfig, record: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    record_id = None
    if not dry_run and record.get("deck_id"):
        record_id = find_record_id(
            config,
            table_id=config.decks_table,
            key_field="deck_id",
            key_value=str(record["deck_id"]),
        )
    command = build_record_upsert_command(
        config=config,
        table_id=config.decks_table,
        fields=record,
        record_id=record_id,
        dry_run=dry_run,
    )
    result = run_json(command)
    if record_id:
        result["record_id"] = record_id
    return result


def upsert_slide(config: BaseConfig, record: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    record_id = None
    if not dry_run and record.get("slide_id"):
        record_id = find_record_id(
            config,
            table_id=config.slides_table,
            key_field="slide_id",
            key_value=str(record["slide_id"]),
        )
    command = build_record_upsert_command(
        config=config,
        table_id=config.slides_table,
        fields=record,
        record_id=record_id,
        dry_run=dry_run,
    )
    result = run_json(command)
    if record_id:
        result["record_id"] = record_id
    return result


def search_slides(
    config: BaseConfig,
    *,
    keyword: str,
    search_fields: list[str],
    select_fields: list[str],
    filter_json: dict[str, Any] | None,
    limit: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_record_search_command(
        config=config,
        table_id=config.slides_table,
        keyword=keyword,
        search_fields=search_fields,
        select_fields=select_fields,
        filter_json=filter_json,
        limit=limit,
        dry_run=dry_run,
    )
    return run_json(command)


def search_decks(
    config: BaseConfig,
    *,
    keyword: str,
    search_fields: list[str],
    select_fields: list[str],
    filter_json: dict[str, Any] | None,
    limit: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_record_search_command(
        config=config,
        table_id=config.decks_table,
        keyword=keyword,
        search_fields=search_fields,
        select_fields=select_fields,
        filter_json=filter_json,
        limit=limit,
        dry_run=dry_run,
    )
    return run_json(command)


def list_decks(
    config: BaseConfig,
    *,
    select_fields: list[str],
    filter_json: dict[str, Any] | None,
    limit: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_record_list_command(
        config=config,
        table_id=config.decks_table,
        select_fields=select_fields,
        filter_json=filter_json,
        limit=limit,
        dry_run=dry_run,
    )
    return run_json(command)


def lookup_material(
    config: BaseConfig,
    *,
    identifier: str,
    select_fields: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_material_lookup_command(
        config=config,
        table_id=config.slides_table,
        identifier=identifier,
        select_fields=select_fields,
        dry_run=dry_run,
    )
    return run_json(command)


def list_materials(
    config: BaseConfig,
    *,
    deck_id: str,
    page_roles: list[str] | None,
    select_fields: list[str],
    limit: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    conditions: list[Any] = [["deck_id", "==", deck_id]]
    if page_roles:
        conditions.append({"logic": "or", "conditions": [["page_role", "==", role] for role in page_roles]})
    command = build_record_list_command(
        config=config,
        table_id=config.slides_table,
        select_fields=select_fields,
        filter_json={"logic": "and", "conditions": conditions},
        sort_json=[{"field": "slide_index", "desc": False}],
        limit=limit,
        dry_run=dry_run,
    )
    return run_json(command)


def upload_attachment(
    config: BaseConfig,
    *,
    table_id: str,
    record_id: str,
    field_id: str,
    files: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_upload_attachment_command(
        config=config,
        table_id=table_id,
        record_id=record_id,
        field_id=field_id,
        files=files,
        dry_run=dry_run,
    )
    return run_json(command)


def create_field(config: BaseConfig, *, table_id: str, field: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    return run_json(build_field_create_command(config=config, table_id=table_id, field=field, dry_run=dry_run))


def list_fields(config: BaseConfig, *, table_id: str, dry_run: bool = False) -> dict[str, Any]:
    return run_json(build_field_list_command(config=config, table_id=table_id, dry_run=dry_run))


def create_view(config: BaseConfig, *, table_id: str, view: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    return run_json(build_view_create_command(config=config, table_id=table_id, view=view, dry_run=dry_run))


def list_views(config: BaseConfig, *, table_id: str, dry_run: bool = False) -> dict[str, Any]:
    return run_json(build_view_list_command(config=config, table_id=table_id, dry_run=dry_run))


def set_view_visible_fields(
    config: BaseConfig,
    *,
    table_id: str,
    view_id: str,
    visible_fields: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    return run_json(
        build_view_set_visible_fields_command(
            config=config,
            table_id=table_id,
            view_id=view_id,
            visible_fields=visible_fields,
            dry_run=dry_run,
        )
    )


def set_view_filter(
    config: BaseConfig,
    *,
    table_id: str,
    view_id: str,
    filter_json: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    return run_json(
        build_view_set_filter_command(
            config=config,
            table_id=table_id,
            view_id=view_id,
            filter_json=filter_json,
            dry_run=dry_run,
        )
    )


def set_view_group(
    config: BaseConfig,
    *,
    table_id: str,
    view_id: str,
    group_json: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    return run_json(
        build_view_set_group_command(
            config=config,
            table_id=table_id,
            view_id=view_id,
            group_json=group_json,
            dry_run=dry_run,
        )
    )


def set_view_sort(
    config: BaseConfig,
    *,
    table_id: str,
    view_id: str,
    sort_json: list[dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    return run_json(
        build_view_set_sort_command(
            config=config,
            table_id=table_id,
            view_id=view_id,
            sort_json=sort_json,
            dry_run=dry_run,
        )
    )


def get_attachment_tokens(
    config: BaseConfig,
    *,
    table_id: str,
    record_id: str,
    field_id: str,
) -> list[str]:
    command = build_record_get_command(
        config=config,
        table_id=table_id,
        record_id=record_id,
        field_id=field_id,
    )
    return extract_attachment_tokens(run_json(command))


def remove_attachment(
    config: BaseConfig,
    *,
    table_id: str,
    record_id: str,
    field_id: str,
    file_tokens: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_remove_attachment_command(
        config=config,
        table_id=table_id,
        record_id=record_id,
        field_id=field_id,
        file_tokens=file_tokens,
        dry_run=dry_run,
    )
    return run_json(command)


def replace_attachment(
    config: BaseConfig,
    *,
    table_id: str,
    record_id: str,
    field_id: str,
    files: list[str],
) -> dict[str, Any]:
    existing_tokens = get_attachment_tokens(
        config,
        table_id=table_id,
        record_id=record_id,
        field_id=field_id,
    )
    upload_result = upload_attachment(
        config,
        table_id=table_id,
        record_id=record_id,
        field_id=field_id,
        files=files,
    )
    remove_result = None
    if existing_tokens:
        remove_result = remove_attachment(
            config,
            table_id=table_id,
            record_id=record_id,
            field_id=field_id,
            file_tokens=existing_tokens,
        )
    return {
        "removed": len(existing_tokens),
        "remove_result": remove_result,
        "upload_result": upload_result,
    }


def download_attachment(
    config: BaseConfig,
    *,
    table_id: str,
    record_id: str,
    file_tokens: list[str],
    output: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    command = build_download_attachment_command(
        config=config,
        table_id=table_id,
        record_id=record_id,
        file_tokens=file_tokens,
        output=output,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    return run_json(command)
