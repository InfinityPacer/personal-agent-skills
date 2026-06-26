---
name: codex-session-metadata
description: Safely inspect or repair local Codex session metadata. Use when the user mentions $codex-session-metadata, Codex session metadata, session cwd/current working directory, resume session provider buckets, model_provider, state_*.sqlite, rollout JSONL, changing a session from one provider to another, or repairing a Codex session so it appears under the expected cwd or provider.
---

# Codex Session Metadata

## Purpose

Inspect and repair persisted local Codex session metadata without hand-editing SQLite or JSONL. This skill is for local resume metadata only: it does not change a running process' argv, OS cwd, remote account ownership, provider auth, model config, or tokens.

## Supported Repairs

- `cwd`: change the persisted working directory for one session.
- `provider`: change the persisted provider bucket for one session.

Both repairs update `~/.codex/state_*.sqlite` and the matching rollout JSONL, create backups first, and verify afterward.

## Workflow

1. Identify the target session id.
   - Prefer an explicit user-provided session id.
   - Otherwise use the current `codex resume ... <session-id>` process when available.
2. Inspect first unless the current request already includes all needed values.
3. Run `scripts/session_metadata.py` with the appropriate subcommand.
4. Verify with `verify` or the write command's JSON output. A write command must fail if either SQLite or rollout JSONL cannot be updated consistently.
5. Tell the user if the live process may still show old launch arguments. New resumes should read the patched metadata.

## Commands

Inspect a session:

```bash
python3 ~/.codex/skills/codex-session-metadata/scripts/session_metadata.py inspect \
  --session-id <session-id>
```

Change cwd:

```bash
python3 ~/.codex/skills/codex-session-metadata/scripts/session_metadata.py set-cwd \
  --session-id <session-id> \
  --target-cwd /path/to/project
```

Change provider:

```bash
python3 ~/.codex/skills/codex-session-metadata/scripts/session_metadata.py set-provider \
  --session-id <session-id> \
  --provider <provider-name>
```

Verify:

```bash
python3 ~/.codex/skills/codex-session-metadata/scripts/session_metadata.py verify \
  --session-id <session-id> \
  --expect-provider <provider-name> \
  --expect-cwd /path/to/project
```

Dry run:

```bash
python3 ~/.codex/skills/codex-session-metadata/scripts/session_metadata.py set-provider \
  --session-id <session-id> \
  --provider <provider-name> \
  --dry-run
```

## Boundaries

- Backups are mandatory before writes. The script backs up the SQLite database with SQLite's backup API and copies the rollout JSONL.
- `cwd` repair updates structured JSON fields named `cwd` in the target rollout whose value matches the old cwd. It does not rewrite arbitrary text.
- `provider` repair updates only `threads.model_provider` and `session_meta.payload.model_provider` for the target session.
- Do not rewrite free text, command strings, historical user messages, provider config, auth files, model names, or token material.
- If the current sandbox blocks writes under `~/.codex`, rerun the same command with escalation.
- Do not modify unrelated sessions unless the user explicitly names that session id.
