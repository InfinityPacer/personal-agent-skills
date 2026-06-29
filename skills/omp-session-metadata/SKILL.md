---
name: omp-session-metadata
description: Use when OMP/Oh My Pi sessions cannot resume from the expected cwd, appear under the wrong project in /resume, have stale history.db cwd rows, or need persisted OMP session cwd metadata moved between ~/.omp/agent/sessions directories.
---

# OMP Session Metadata

## Purpose

Inspect and repair persisted Oh My Pi (`omp`) session cwd metadata without hand-editing SQLite or JSONL. This skill is for local resume metadata only: it does not change a running process' OS cwd, provider auth, model config, prompts, tool outputs, or secrets.

## Supported Repairs

- `cwd`: change one OMP session's persisted working directory.

The repair updates three coupled stores and creates backups first:

1. `~/.omp/agent/history.db` rows for the session id.
2. The session JSONL header (`type: "session"`) cwd field.
3. The managed session JSONL file and artifact directory location under `~/.omp/agent/sessions/<encoded-cwd>/`.

## Workflow

1. Identify the target session id.
   - Prefer an explicit user-provided session id.
   - Otherwise inspect `~/.omp/agent/sessions/**/<timestamp>_<session-id>.jsonl` and the current `/resume` context.
2. Inspect first unless the request already includes the session id, current cwd, and target cwd. Stop if `safe_to_repair` is false.
3. If the target session is live, duplicated, or colliding, show the inspection result. Ask the user to exit OMP first. If the only unsafe reason is an active terminal breadcrumb and the user explicitly requests a forced repair, rerun `set-cwd` with `--force-unsafe`.
4. Run `scripts/session_metadata.py` with `inspect`, `set-cwd --dry-run`, then `set-cwd`. Use `--force-unsafe` on both write-path commands only after explicit user confirmation.
5. Verify with `verify` or the write command's JSON output.
6. Tell the user that live processes may still show old state until restarted; new `omp --resume <id>` invocations should read the patched metadata.

## Commands

Inspect a session:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py inspect \
  --session-id <session-id>
```

Dry-run a cwd repair:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py set-cwd \
  --session-id <session-id> \
  --target-cwd /path/to/project \
  --dry-run
```

If `inspect` reports `safe_to_repair: false`, stop and report the unsafe reasons. Use `--force-unsafe` only after the user explicitly accepts active terminal breadcrumb risk; duplicate session files and destination collisions still require manual resolution.


Apply a cwd repair:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py set-cwd \
  --session-id <session-id> \
  --target-cwd /path/to/project
```

Force a cwd repair after explicit user approval when the only unsafe reason is an active terminal breadcrumb:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py set-cwd \
  --session-id <session-id> \
  --target-cwd /path/to/project \
  --force-unsafe
```

Verify:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py verify \
  --session-id <session-id> \
  --expect-cwd /path/to/project
```

Use a non-default OMP agent directory:

```bash
python3 skills/omp-session-metadata/scripts/session_metadata.py inspect \
  --agent-dir /path/to/.omp/agent \
  --session-id <session-id>
```

## OMP Storage Rules

- Session files live below `getSessionsDir()`; by default this is `~/.omp/agent/sessions`.
- The directory name is derived from cwd:
  - under home: `-` plus the home-relative path with separators replaced by `-` (example: `~/GitHub/oh-my-pi` -> `-GitHub-oh-my-pi`).
  - under temp: `-tmp` plus the temp-relative path.
  - elsewhere: legacy absolute form `--<absolute-path-with-dashes>--`.
- The authoritative resumed cwd is the JSONL session header `cwd` when that directory still exists.
- Prompt history search and `/resume` labels use `history.db`, so JSONL-only repairs leave stale picker/history behavior.
- Tool artifacts for a session are stored next to the JSONL file in a same-stem directory; moving only the JSONL can break artifact links.

## Boundaries

- Backups are mandatory before writes. The script backs up `history.db` with SQLite's backup API and copies the JSONL plus artifact directory when present.
- `cwd` repair updates only the top-level session header whose `id` matches the target session and `history.db` rows with the same `session_id`.
- Do not rewrite message text, tool arguments, provider config, auth files, model names, token material, logs, or unrelated sessions.
- Do not merge or mutate sessions when the destination JSONL path already exists or duplicate session files exist; stop and report the collision risk. Terminal breadcrumbs block by default and may be bypassed only after explicit user approval because live processes may still show or rewrite old state until restarted.
- If the current sandbox blocks writes under `~/.omp`, rerun the same command with an approved unsandboxed/elevated path.
