#!/usr/bin/env python3
"""Check Decks.online_url health and update deck-library status fields."""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

import lark_base


SELECT_FIELDS = [
    "deck_id",
    "中文名称",
    "online_url",
    "access_status",
    "link_health",
    "链接状态",
    "last_checked_at",
]

ALLOWED_HOST_SUFFIXES = (
    "larkoffice.com",
    "feishu.cn",
    "feishu.net",
    "aiforce.cloud",
    "bytedance.com",
    "bytedance.net",
)


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def classify_link_health(
    url: str | None,
    *,
    status_code: int | None = None,
    error: str | None = None,
) -> tuple[str, str]:
    if not url:
        return "failed", "无线上链接"
    if error:
        return "failed", f"链接检查失败: {error}"
    if status_code is not None and 200 <= status_code < 400:
        if status_code >= 300:
            return "failed", "链接跳转未验证"
        return "ok", "可访问"
    return "failed", "链接失效或无权限"


def build_update_fields(
    url: str | None,
    *,
    status_code: int | None = None,
    error: str | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    link_health, human_status = classify_link_health(url, status_code=status_code, error=error)
    fields: dict[str, Any] = {
        "link_health": link_health,
        "链接状态": human_status,
        "last_checked_at": checked_at or now_string(),
    }
    if link_health == "ok":
        fields["access_status"] = "ready"
    elif url:
        fields["access_status"] = "broken"
    else:
        fields["access_status"] = "draft"
    return fields


def is_private_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def url_safety_error(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "unsafe scheme: only http/https links are checked"
    hostname = parsed.hostname
    if not hostname:
        return "unsafe URL: missing hostname"
    normalized = hostname.lower().strip(".")
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return "unsafe private host: localhost"
    if is_private_address(normalized):
        return "unsafe private host: private IP address"
    if not any(normalized == suffix or normalized.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES):
        return "unsafe untrusted host: link checker only probes trusted deck hosting domains"
    try:
        addresses = socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return None
    for item in addresses:
        address = item[4][0]
        if is_private_address(address):
            return "unsafe private host: DNS resolves to private IP address"
    return None


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def probe_url(url: str, *, timeout: float = 8.0) -> tuple[int | None, str | None]:
    safety_error = url_safety_error(url)
    if safety_error:
        return None, safety_error
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "deck-library-link-check/1.0"})
    try:
        opener = urllib.request.build_opener(NoRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), None
    except urllib.error.HTTPError as exc:
        if exc.code in {405, 501}:
            return probe_url_get(url, timeout=timeout)
        return int(exc.code), None
    except Exception as exc:  # pragma: no cover - covered through classify/build unit tests
        return None, str(exc)


def probe_url_get(url: str, *, timeout: float = 8.0) -> tuple[int | None, str | None]:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "deck-library-link-check/1.0"})
    try:
        opener = urllib.request.build_opener(NoRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), None
    except urllib.error.HTTPError as exc:
        return int(exc.code), None
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def extract_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    fields = data.get("fields")
    rows = data.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return []
    record_ids = data.get("record_id_list")
    if not isinstance(record_ids, list):
        record_ids = []
    extracted: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, list):
            continue
        record = {str(field): value for field, value in zip(fields, row)}
        if index < len(record_ids):
            record["_record_id"] = str(record_ids[index])
        extracted.append(record)
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Decks.online_url and update link health fields.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without querying Base or URLs.")
    parser.add_argument("--write", action="store_true", help="Update Decks link health fields.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--base-token", help="Feishu Base token. Defaults to DECK_LIBRARY_BASE_TOKEN.")
    parser.add_argument("--decks-table", help="Decks table ID/name. Defaults to DECK_LIBRARY_DECKS_TABLE.")
    parser.add_argument("--profile", default=None, help="lark-cli profile. Defaults to DECK_LIBRARY_LARK_PROFILE or bytedance.")
    parser.add_argument("--as", dest="identity", default=None, help="lark-cli identity: user or bot.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        print("check_links.py: choose either --dry-run or --write, not both", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "operation": "check_links",
                    "limit": args.limit,
                    "select_fields": SELECT_FIELDS,
                    "planned_updates": ["link_health", "链接状态", "last_checked_at", "access_status"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    config = lark_base.BaseConfig.from_env(
        base_token=args.base_token,
        decks_table=args.decks_table,
        slides_table="unused",
        profile=args.profile,
        identity=args.identity,
    )
    errors = config.validation_errors(required=("base_token", "decks_table"))
    if errors:
        print("check_links.py: " + "; ".join(errors), file=sys.stderr)
        return 2

    try:
        result = lark_base.list_decks(
            config,
            select_fields=SELECT_FIELDS,
            filter_json={"logic": "and", "conditions": [["status", "!=", "deprecated"]]},
            limit=args.limit,
        )
        rows = extract_rows(result)
        updates = []
        for row in rows:
            deck_id = str(row.get("deck_id") or "")
            record_id = str(row.get("_record_id") or "")
            url = str(row.get("online_url") or "")
            status_code, error = probe_url(url, timeout=args.timeout) if url else (None, None)
            fields = build_update_fields(url, status_code=status_code, error=error)
            update_result: dict[str, Any] | str = "skipped"
            if args.write:
                if record_id:
                    update_result = lark_base.run_json(
                        lark_base.build_record_upsert_command(
                            config=config,
                            table_id=config.decks_table,
                            record_id=record_id,
                            fields=fields,
                        )
                    )
                else:
                    update_result = "skipped: missing record_id"
            updates.append(
                {
                    "deck_id": deck_id,
                    "record_id": record_id,
                    "url": url,
                    "status_code": status_code,
                    "error": error,
                    "fields": fields,
                    "update_result": update_result,
                }
            )
    except Exception as exc:
        print(f"check_links.py: link check failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"mode": "write" if args.write else "check-only", "operation": "check_links", "updates": updates}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
