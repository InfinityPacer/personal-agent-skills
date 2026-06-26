#!/usr/bin/env python3
"""Inspect and repair persisted Codex session metadata with backups."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SESSION_ID_RE = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def detect_current_session_id() -> str | None:
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "pid,command"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    candidates: list[tuple[int, str]] = []
    for line in out.splitlines():
        if "codex resume" not in line:
            continue
        match = SESSION_ID_RE.search(line)
        if not match:
            continue
        try:
            pid = int(line.strip().split(None, 1)[0])
        except Exception:
            pid = 0
        candidates.append((pid, match.group(0)))
    if not candidates:
        return None
    return sorted(candidates)[-1][1]


def connect_state_db(codex_home: Path, explicit: Path | None) -> Path:
    if explicit:
        return explicit.expanduser()
    candidates = sorted(codex_home.glob("state_*.sqlite"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit(f"No state_*.sqlite found under {codex_home}")
    return candidates[0]


def fetch_thread(db_path: Path, session_id: str) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "select id, cwd, rollout_path, model_provider, title from threads where id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        raise SystemExit(f"Session id not found in {db_path}: {session_id}")
    return {
        "id": row[0],
        "cwd": row[1],
        "rollout_path": str(Path(row[2]).expanduser()),
        "model_provider": row[3],
        "title": row[4],
    }


def timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S")


def backup_state_db(db_path: Path, backup_dir: Path, stamp: str, reason: str, dry_run: bool) -> Path:
    dest = backup_dir / f"{db_path.stem}-before-{reason}-{stamp}.sqlite"
    if dry_run:
        return dest
    backup_dir.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(db_path)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def backup_jsonl(jsonl_path: Path, stamp: str, reason: str, dry_run: bool) -> Path:
    dest = jsonl_path.with_name(jsonl_path.name + f".bak-{reason}-{stamp}")
    if not dry_run:
        shutil.copy2(jsonl_path, dest)
    return dest


def rewrite_cwd_fields(value: Any, old_cwd: str, new_cwd: str) -> int:
    count = 0
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if key == "cwd" and item == old_cwd:
                value[key] = new_cwd
                count += 1
            else:
                count += rewrite_cwd_fields(item, old_cwd, new_cwd)
    elif isinstance(value, list):
        for item in value:
            count += rewrite_cwd_fields(item, old_cwd, new_cwd)
    return count


def rewrite_session_meta_provider(value: Any, session_id: str, old_provider: str, new_provider: str) -> int:
    if not isinstance(value, dict):
        return 0
    if value.get("type") != "session_meta":
        return 0
    payload = value.get("payload")
    if not isinstance(payload, dict):
        return 0
    if payload.get("id") != session_id and payload.get("session_id") != session_id:
        return 0
    if payload.get("model_provider") != old_provider:
        return 0
    payload["model_provider"] = new_provider
    return 1


def rewrite_jsonl(
    jsonl_path: Path,
    *,
    old_cwd: str | None = None,
    new_cwd: str | None = None,
    session_id: str | None = None,
    old_provider: str | None = None,
    new_provider: str | None = None,
    dry_run: bool = False,
) -> int:
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    changed_fields = 0
    new_lines: list[str] = []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        if old_cwd is not None and new_cwd is not None:
            changed_fields += rewrite_cwd_fields(data, old_cwd, new_cwd)
        if session_id is not None and old_provider is not None and new_provider is not None:
            changed_fields += rewrite_session_meta_provider(data, session_id, old_provider, new_provider)
        new_lines.append(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    if changed_fields and not dry_run:
        tmp = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp-session-metadata")
        tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        os.replace(tmp, jsonl_path)
    return changed_fields


def collect_cwd_values(value: Any, counts: dict[str, int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "cwd" and isinstance(item, str):
                counts[item] = counts.get(item, 0) + 1
            collect_cwd_values(item, counts)
    elif isinstance(value, list):
        for item in value:
            collect_cwd_values(item, counts)


def read_jsonl_metadata(jsonl_path: Path, session_id: str) -> dict[str, Any]:
    cwd_counts: dict[str, int] = {}
    session_meta_providers: list[str | None] = []
    session_meta_count = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        collect_cwd_values(data, cwd_counts)
        if data.get("type") == "session_meta" and isinstance(data.get("payload"), dict):
            payload = data["payload"]
            if payload.get("id") == session_id or payload.get("session_id") == session_id:
                session_meta_count += 1
                if "model_provider" in payload:
                    session_meta_providers.append(payload.get("model_provider"))
    return {
        "jsonl_cwd_counts": dict(sorted(cwd_counts.items())),
        "jsonl_session_meta_provider": session_meta_providers[-1] if session_meta_providers else None,
        "jsonl_session_meta_providers": session_meta_providers,
        "jsonl_session_meta_count": session_meta_count,
    }


def inspect_payload(db_path: Path, session_id: str) -> dict[str, Any]:
    thread = fetch_thread(db_path, session_id)
    rollout_path = Path(thread["rollout_path"])
    jsonl = read_jsonl_metadata(rollout_path, session_id)
    jsonl_cwd_counts = jsonl["jsonl_cwd_counts"]
    sqlite_cwd = thread["cwd"]
    jsonl_providers = set(jsonl["jsonl_session_meta_providers"])
    return {
        "session_id": session_id,
        "state_db": str(db_path),
        "rollout_path": str(rollout_path),
        "sqlite_cwd": sqlite_cwd,
        "sqlite_model_provider": thread["model_provider"],
        "title": thread["title"],
        **jsonl,
        "cwd_consistent": bool(jsonl_cwd_counts) and set(jsonl_cwd_counts) == {sqlite_cwd},
        "provider_consistent": bool(jsonl_providers) and jsonl_providers == {thread["model_provider"]},
    }


def update_thread_cwd(db_path: Path, session_id: str, new_cwd: str, dry_run: bool) -> int:
    if dry_run:
        return 1
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "update threads set cwd = ? where id = ?",
            (new_cwd, session_id),
        )
        conn.commit()
        return cur.rowcount


def update_thread_provider(db_path: Path, session_id: str, provider: str, dry_run: bool) -> int:
    if dry_run:
        return 1
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "update threads set model_provider = ? where id = ?",
            (provider, session_id),
        )
        conn.commit()
        return cur.rowcount


def common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-id", help="Codex session/thread id. Defaults to current codex resume process")
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--state-db", type=Path, help="Explicit state_*.sqlite path")


def resolve_inputs(args: argparse.Namespace) -> tuple[str, Path, Path]:
    session_id = args.session_id or detect_current_session_id()
    if not session_id:
        raise SystemExit("Could not detect a current session id; pass --session-id explicitly")
    codex_home = args.codex_home.expanduser()
    db_path = connect_state_db(codex_home, args.state_db)
    return session_id, codex_home, db_path


def run_inspect(args: argparse.Namespace) -> int:
    session_id, _, db_path = resolve_inputs(args)
    print(json.dumps(inspect_payload(db_path, session_id), ensure_ascii=False, indent=2))
    return 0


def run_verify(args: argparse.Namespace) -> int:
    session_id, _, db_path = resolve_inputs(args)
    payload = inspect_payload(db_path, session_id)
    checks: dict[str, bool] = {
        "cwd_consistent": payload["cwd_consistent"],
        "provider_consistent": payload["provider_consistent"],
    }
    if args.expect_cwd:
        expected_cwd = str(Path(args.expect_cwd).expanduser().resolve())
        checks["sqlite_cwd_matches_expected"] = payload["sqlite_cwd"] == expected_cwd
        checks["jsonl_has_expected_cwd"] = payload["jsonl_cwd_counts"].get(expected_cwd, 0) > 0
    if args.expect_provider:
        checks["sqlite_provider_matches_expected"] = payload["sqlite_model_provider"] == args.expect_provider
        checks["jsonl_provider_matches_expected"] = payload["jsonl_session_meta_provider"] == args.expect_provider
    payload["checks"] = checks
    payload["status"] = "verified" if all(checks.values()) else "mismatch"
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "verified" else 2


def run_set_cwd(args: argparse.Namespace) -> int:
    session_id, codex_home, db_path = resolve_inputs(args)
    target_cwd = str(Path(args.target_cwd).expanduser().resolve())
    if not Path(target_cwd).is_dir():
        raise SystemExit(f"Target cwd is not a directory: {target_cwd}")

    thread = fetch_thread(db_path, session_id)
    old_cwd = thread["cwd"]
    rollout_path = Path(thread["rollout_path"])
    if old_cwd == target_cwd:
        payload = inspect_payload(db_path, session_id)
        payload.update({"status": "unchanged", "cwd": target_cwd})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["cwd_consistent"] else 2

    planned_jsonl_fields = rewrite_jsonl(rollout_path, old_cwd=old_cwd, new_cwd=target_cwd, dry_run=True)
    if planned_jsonl_fields <= 0:
        raise SystemExit(f"No matching cwd fields found in rollout JSONL: {rollout_path}")

    stamp = timestamp()
    backup_dir = codex_home / "session-backups"
    db_backup = backup_state_db(db_path, backup_dir, stamp, "cwd", args.dry_run)
    jsonl_backup = backup_jsonl(rollout_path, stamp, "cwd", args.dry_run)
    db_rows = update_thread_cwd(db_path, session_id, target_cwd, args.dry_run)
    jsonl_fields = planned_jsonl_fields if args.dry_run else rewrite_jsonl(
        rollout_path,
        old_cwd=old_cwd,
        new_cwd=target_cwd,
        dry_run=False,
    )
    payload = {} if args.dry_run else inspect_payload(db_path, session_id)
    payload.update({
        "status": "dry-run" if args.dry_run else "updated",
        "session_id": session_id,
        "old_cwd": old_cwd,
        "new_cwd": target_cwd,
        "state_db": str(db_path),
        "rollout_path": str(rollout_path),
        "db_rows_updated": db_rows,
        "jsonl_cwd_fields_updated": jsonl_fields,
        "state_backup": str(db_backup),
        "jsonl_backup": str(jsonl_backup),
        "note": "Live codex process argv may still show the original -C until restarted or resumed.",
    })
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0
    if db_rows != 1 or jsonl_fields <= 0 or not payload["cwd_consistent"]:
        return 2
    return 0


def run_set_provider(args: argparse.Namespace) -> int:
    session_id, codex_home, db_path = resolve_inputs(args)
    provider = args.provider.strip()
    if not provider:
        raise SystemExit("Provider cannot be empty")

    thread = fetch_thread(db_path, session_id)
    old_provider = thread["model_provider"]
    rollout_path = Path(thread["rollout_path"])
    if old_provider == provider:
        payload = inspect_payload(db_path, session_id)
        payload.update({"status": "unchanged", "provider": provider})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["provider_consistent"] else 2

    planned_jsonl_fields = rewrite_jsonl(
        rollout_path,
        session_id=session_id,
        old_provider=old_provider,
        new_provider=provider,
        dry_run=True,
    )
    if planned_jsonl_fields <= 0:
        raise SystemExit(f"No matching session_meta model_provider found in rollout JSONL: {rollout_path}")

    stamp = timestamp()
    backup_dir = codex_home / "session-backups"
    db_backup = backup_state_db(db_path, backup_dir, stamp, "provider", args.dry_run)
    jsonl_backup = backup_jsonl(rollout_path, stamp, "provider", args.dry_run)
    db_rows = update_thread_provider(db_path, session_id, provider, args.dry_run)
    jsonl_fields = planned_jsonl_fields if args.dry_run else rewrite_jsonl(
        rollout_path,
        session_id=session_id,
        old_provider=old_provider,
        new_provider=provider,
        dry_run=False,
    )
    payload = {} if args.dry_run else inspect_payload(db_path, session_id)
    payload.update({
        "status": "dry-run" if args.dry_run else "updated",
        "session_id": session_id,
        "old_provider": old_provider,
        "new_provider": provider,
        "state_db": str(db_path),
        "rollout_path": str(rollout_path),
        "db_rows_updated": db_rows,
        "jsonl_provider_fields_updated": jsonl_fields,
        "state_backup": str(db_backup),
        "jsonl_backup": str(jsonl_backup),
        "note": "This only changes local resume metadata; it does not change provider config or auth.",
    })
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0
    if db_rows != 1 or jsonl_fields <= 0 or not payload["provider_consistent"]:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one session")
    common_parser(inspect_parser)
    inspect_parser.set_defaults(func=run_inspect)

    verify_parser = subparsers.add_parser("verify", help="Verify one session")
    common_parser(verify_parser)
    verify_parser.add_argument("--expect-cwd", help="Expected persisted cwd")
    verify_parser.add_argument("--expect-provider", help="Expected persisted model_provider")
    verify_parser.set_defaults(func=run_verify)

    cwd_parser = subparsers.add_parser("set-cwd", help="Rewrite session cwd metadata")
    common_parser(cwd_parser)
    cwd_parser.add_argument("--target-cwd", required=True, help="Absolute cwd to persist for the session")
    cwd_parser.add_argument("--dry-run", action="store_true")
    cwd_parser.set_defaults(func=run_set_cwd)

    provider_parser = subparsers.add_parser("set-provider", help="Rewrite session provider metadata")
    common_parser(provider_parser)
    provider_parser.add_argument("--provider", required=True, help="Provider bucket name to persist for the session")
    provider_parser.add_argument("--dry-run", action="store_true")
    provider_parser.set_defaults(func=run_set_provider)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
