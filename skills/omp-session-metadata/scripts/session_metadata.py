#!/usr/bin/env python3
"""Inspect and repair persisted OMP session cwd metadata with backups."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

SESSION_ID_RE = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b")


def default_agent_dir() -> Path:
    env = os.environ.get("PI_CODING_AGENT_DIR") or os.environ.get("OMP_AGENT_DIR")
    return Path(env).expanduser() if env else Path.home() / ".omp" / "agent"


def canonical(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def encode_relative(prefix: str, relative: str) -> str:
    encoded = relative.replace("/", "-").replace("\\", "-").replace(":", "-")
    if not encoded:
        return prefix
    return f"{prefix}{encoded}" if prefix.endswith("-") else f"{prefix}-{encoded}"


def encode_legacy_absolute(cwd: Path) -> str:
    text = str(cwd).lstrip("/\\")
    return "--" + text.replace("/", "-").replace("\\", "-").replace(":", "-") + "--"


def session_dir_name(cwd: Path) -> str:
    resolved = canonical(cwd)
    home = canonical(Path.home())
    temp = canonical(Path(os.environ.get("TMPDIR", "/tmp")))
    try:
        home_rel = resolved.relative_to(home)
        return encode_relative("-", str(home_rel))
    except ValueError:
        pass
    try:
        temp_rel = resolved.relative_to(temp)
        return encode_relative("-tmp", str(temp_rel))
    except ValueError:
        return encode_legacy_absolute(resolved)


def sessions_root(agent_dir: Path) -> Path:
    return agent_dir / "sessions"


def history_db(agent_dir: Path) -> Path:
    return agent_dir / "history.db"


def timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S")


def find_session_file(agent_dir: Path, session_id: str) -> Path:
    root = sessions_root(agent_dir)
    matches = sorted(root.glob(f"**/*_{session_id}.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise SystemExit(f"Session file not found under {root}: {session_id}")
    if len(matches) > 1:
        # Prefer the newest, but surface ambiguity in inspect output via all_session_files.
        return matches[0]
    return matches[0]


def all_session_files(agent_dir: Path, session_id: str) -> list[Path]:
    return sorted(sessions_root(agent_dir).glob(f"**/*_{session_id}.jsonl"), key=lambda p: str(p))


def read_jsonl(path: Path) -> list[Any]:
    records: list[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append(line)
    return records


def write_jsonl(path: Path, records: list[Any], dry_run: bool) -> None:
    if dry_run:
        return
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) if not isinstance(r, str) else r for r in records]
    tmp = path.with_suffix(path.suffix + ".tmp-omp-session-metadata")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def session_header(records: list[Any], session_id: str) -> dict[str, Any]:
    for record in records:
        if isinstance(record, dict) and record.get("type") == "session" and record.get("id") == session_id:
            return record
    raise SystemExit(f"Session header not found for {session_id}")


def query_history(agent_dir: Path, session_id: str) -> dict[str, Any]:
    db = history_db(agent_dir)
    if not db.exists():
        return {"history_db": str(db), "history_rows": 0, "history_cwds": {}}
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT cwd, COUNT(*) FROM history WHERE session_id = ? GROUP BY cwd", (session_id,)).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM history WHERE session_id = ?", (session_id,)).fetchone()[0]
    return {"history_db": str(db), "history_rows": total, "history_cwds": {str(k): v for k, v in rows}}


def terminal_breadcrumbs(agent_dir: Path, session_id: str) -> list[dict[str, str]]:
    root = agent_dir / "terminal-sessions"
    if not root.is_dir():
        return []
    matches: list[dict[str, str]] = []
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        if not item.is_file():
            continue
        try:
            lines = item.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        if len(lines) < 2:
            continue
        cwd, session_file = lines[0], lines[1]
        if session_id in session_file:
            matches.append({"terminal": item.name, "cwd": cwd, "session_file": session_file})
    return matches


def safety_report(agent_dir: Path, session_id: str, files: list[Path]) -> dict[str, Any]:
    active = terminal_breadcrumbs(agent_dir, session_id)
    reasons: list[str] = []
    if len(files) > 1:
        reasons.append("duplicate session files exist for this session id")
    if active:
        reasons.append("terminal breadcrumb still points at this session; ask the user to exit OMP first or explicitly request --force-unsafe")
    return {
        "duplicate_session_files": len(files) > 1,
        "active_breadcrumbs": active,
        "safe_to_repair": not reasons,
        "unsafe_reasons": reasons,
    }


def force_allowed_for_report(report: dict[str, Any]) -> bool:
    reasons = report.get("unsafe_reasons")
    if not isinstance(reasons, list):
        return False
    return bool(reasons) and all(
        isinstance(reason, str) and reason.startswith("terminal breadcrumb still points at this session") for reason in reasons
    )


def artifact_dir_for(session_file: Path) -> Path:
    return session_file.with_suffix("")


def inspect(agent_dir: Path, session_id: str) -> dict[str, Any]:
    files = all_session_files(agent_dir, session_id)
    if not files:
        raise SystemExit(f"Session file not found under {sessions_root(agent_dir)}: {session_id}")
    session_file = max(files, key=lambda p: p.stat().st_mtime)
    records = read_jsonl(session_file)
    header = session_header(records, session_id)
    cwd = header.get("cwd")
    expected_dir = sessions_root(agent_dir) / session_dir_name(Path(cwd)) if isinstance(cwd, str) else None
    artifact_dir = artifact_dir_for(session_file)
    return {
        "agent_dir": str(agent_dir),
        "session_id": session_id,
        "session_file": str(session_file),
        "all_session_files": [str(p) for p in files],
        "jsonl_cwd": cwd,
        "expected_session_dir": str(expected_dir) if expected_dir else None,
        "file_in_expected_dir": bool(expected_dir and session_file.parent == expected_dir),
        "artifact_dir": str(artifact_dir),
        "artifact_dir_exists": artifact_dir.is_dir(),
        **query_history(agent_dir, session_id),
        **safety_report(agent_dir, session_id, files),
    }


def backup_sqlite(db_path: Path, backup_dir: Path, stamp: str, dry_run: bool) -> Path | None:
    if not db_path.exists():
        return None
    dest = backup_dir / f"{db_path.name}.bak-set-cwd-{stamp}"
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


def backup_path(path: Path, backup_dir: Path, stamp: str, dry_run: bool) -> Path | None:
    if not path.exists():
        return None
    dest = backup_dir / f"{path.name}.bak-set-cwd-{stamp}"
    if dry_run:
        return dest
    backup_dir.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        shutil.copytree(path, dest)
    else:
        shutil.copy2(path, dest)
    return dest


def update_history(agent_dir: Path, session_id: str, target_cwd: str, dry_run: bool) -> int:
    db = history_db(agent_dir)
    if not db.exists():
        return 0
    with sqlite3.connect(db) as conn:
        if dry_run:
            return conn.execute("SELECT COUNT(*) FROM history WHERE session_id = ?", (session_id,)).fetchone()[0]
        cur = conn.execute("UPDATE history SET cwd = ? WHERE session_id = ?", (target_cwd, session_id))
        conn.commit()
        return cur.rowcount


def set_cwd(agent_dir: Path, session_id: str, target_cwd: Path, dry_run: bool, force_unsafe: bool = False) -> dict[str, Any]:
    target = str(canonical(target_cwd))
    if not Path(target).is_dir():
        raise SystemExit(f"Target cwd does not exist or is not a directory: {target}")
    before = inspect(agent_dir, session_id)
    if not before.get("safe_to_repair"):
        if not force_unsafe or not force_allowed_for_report(before):
            raise SystemExit(
                json.dumps(
                    {
                        "error": "Unsafe to repair active or duplicated OMP session metadata",
                        "hint": "Exit the live OMP session first. Use --force-unsafe only after the user explicitly accepts active-writer risk; duplicate files and destination collisions still require manual resolution.",
                        "inspect": before,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    session_file = Path(before["session_file"])
    records = read_jsonl(session_file)
    header = session_header(records, session_id)
    old_cwd = header.get("cwd")
    if not isinstance(old_cwd, str):
        raise SystemExit("Session header cwd is missing or not a string")

    dest_dir = sessions_root(agent_dir) / session_dir_name(Path(target))
    dest_file = dest_dir / session_file.name
    old_artifact_dir = artifact_dir_for(session_file)
    dest_artifact_dir = artifact_dir_for(dest_file)
    if dest_file.exists() and dest_file != session_file:
        raise SystemExit(f"Destination session file already exists: {dest_file}")
    if dest_artifact_dir.exists() and dest_artifact_dir != old_artifact_dir:
        raise SystemExit(f"Destination artifact directory already exists: {dest_artifact_dir}")

    stamp = timestamp()
    backup_dir = agent_dir / "backups" / "omp-session-metadata"
    backups = {
        "history_db": str(backup_sqlite(history_db(agent_dir), backup_dir, stamp, dry_run)),
        "jsonl": str(backup_path(session_file, backup_dir, stamp, dry_run)),
        "artifact_dir": str(backup_path(old_artifact_dir, backup_dir, stamp, dry_run)),
    }

    header["cwd"] = target
    write_jsonl(session_file, records, dry_run)
    history_rows = update_history(agent_dir, session_id, target, dry_run)

    moved_session_file = False
    moved_artifact_dir = False
    if session_file.parent != dest_dir:
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if old_artifact_dir.is_dir():
                os.replace(old_artifact_dir, dest_artifact_dir)
                moved_artifact_dir = True
            os.replace(session_file, dest_file)
            moved_session_file = True
        else:
            moved_session_file = True
            moved_artifact_dir = old_artifact_dir.is_dir()

    return {
        "dry_run": dry_run,
        "session_id": session_id,
        "old_cwd": old_cwd,
        "target_cwd": target,
        "old_session_file": str(session_file),
        "new_session_file": str(dest_file),
        "history_rows_updated": history_rows,
        "moved_session_file": moved_session_file,
        "moved_artifact_dir": moved_artifact_dir,
        "backups": backups,
    }


def verify(agent_dir: Path, session_id: str, expect_cwd: Path) -> dict[str, Any]:
    expected = str(canonical(expect_cwd))
    payload = inspect(agent_dir, session_id)
    history_cwds = set(payload["history_cwds"].keys())
    ok = (
        payload["jsonl_cwd"] == expected
        and payload["file_in_expected_dir"] is True
        and (not history_cwds or history_cwds == {expected})
    )
    payload["expected_cwd"] = expected
    payload["ok"] = ok
    if not ok:
        raise SystemExit(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", type=Path, default=default_agent_dir())
    sub = parser.add_subparsers(dest="cmd", required=True)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("--session-id", required=True)

    set_p = sub.add_parser("set-cwd")
    set_p.add_argument("--session-id", required=True)
    set_p.add_argument("--target-cwd", type=Path, required=True)
    set_p.add_argument("--dry-run", action="store_true")
    set_p.add_argument("--force-unsafe", action="store_true", help="Bypass active terminal breadcrumb safety checks after explicit user approval")

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--session-id", required=True)
    verify_p.add_argument("--expect-cwd", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agent_dir = canonical(args.agent_dir)
    if args.cmd == "inspect":
        payload = inspect(agent_dir, args.session_id)
    elif args.cmd == "set-cwd":
        payload = set_cwd(agent_dir, args.session_id, args.target_cwd, args.dry_run, args.force_unsafe)
    elif args.cmd == "verify":
        payload = verify(agent_dir, args.session_id, args.expect_cwd)
    else:
        raise AssertionError(args.cmd)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
