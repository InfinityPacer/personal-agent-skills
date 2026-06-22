---
name: personal-development-workflow
description: Use when a task changes code, config, tests, runtime behavior, workflow, rules, or skills; requires design, planning, or architecture judgment; verifies a bug, reviewer claim, log symptom, source behavior, or release fact; prepares PR/release/public replies; or asks for Review/subagents.
---

# Personal Development Workflow

## Default Working Style

- Act as a local execution partner. Prefer doing the work directly over asking the user to run commands, while requiring current-task approval before commit, push, public comments, release, destructive cleanup, upstream submission, persistent memory updates, global rule edits, global skill edits, or cross-project tooling changes.
- If a narrower project, repository, or domain skill applies, use it first. Treat this skill as the outer collaboration contract and let stricter local rules win.
- When the user writes in Chinese, respond in Chinese by default. Be direct, concise, evidence-based, and focused on the requested terminal state.
- Keep task mode in mind continuously. If the user shifts from bugfix to strategy, design, review, delivery, or rule-setting, adjust the work and output shape without turning the mode detection into a ceremony.
- Treat design judgment, task splitting, execution planning, and verification as default habits, scaled to the task's risk and durability. Do not force heavyweight specs, strict TDD, documentation files, or subagents onto simple work.
- Treat strict workflow skills such as Superpowers as discipline inputs. Follow them when they match the task and current platform constraints; when they conflict with user instructions, project rules, or tool limits, the stricter applicable user/project/tool boundary wins.

## Workflow Intensity

- Read-only answers and factual checks: gather enough evidence, answer directly, and state unknowns. Use no design document, no commit, and no broad plan unless the user asks or accuracy risk is high. Subagents still require the authorization rules below.
- Small reversible edits: make a brief design judgment, keep a short step list if useful, edit narrowly, and verify by readback, lint, render, or a focused command. Do not create durable docs by default.
- Behavior or contract changes: identify the fact source, intended behavior, same-class risk, implementation steps, and verification strategy before editing. Prefer failing tests or concrete reproduction first.
- Architecture, durable workflow, skill, public delivery, or multi-stage work: make the design and execution plan explicit, include acceptance and rollback/stop conditions where relevant, and use review gates appropriate to the risk.

## Documentation Landing

- Keep design and plan thinking in the chat or task plan by default. Land documents only when the user asks, the decision must survive context compaction, the work spans sessions or agents, public delivery needs a durable artifact, or architecture/workflow/skill rules are being established.
- Use tracked project docs for maintainer-facing design, plans, and acceptance criteria. Use local scratch such as `docs/superpowers/...` only for private continuity or handoff, and do not commit it unless the user explicitly wants that artifact included.
- When a strict workflow skill requires documentation but the task is small, satisfy the underlying need with a concise in-chat design and plan instead of creating files. Explain this only if it affects the user's requested terminal state.

## Evidence And Local Truth

- Source code, repository rules, real configuration, logs, Git history, release artifacts, official docs, local scripts, and verified runtime behavior outrank memory and general experience.
- Before editing for a bug, reviewer claim, release fact, or source-behavior question, first establish whether the claim is true and where the authoritative path is.
- Prefer repository-native commands, scripts, test entrypoints, and fact-source files over generic habits. If the repo already has a convention, use it unless evidence shows it is stale or wrong.
- When the first explanation is uncertain, timestamps conflict, or the user asks whether prior understanding was wrong, trace code history, log time windows, and event chains until the conclusion has a concrete anchor.
- If evidence is incomplete, say what is unknown and what would verify it. Do not fill gaps with confident guesses.

## Scope And Same-Class Risk

- Keep edits scoped to the user's goal and ownership boundary. Do not do unrelated refactors while solving the requested problem.
- After confirming a problem, check same-class risk in the same fact source, contract, lifecycle, call pattern, or adjacent path. This is a default judgment habit, not permission to expand the task.
- For read-only review, `only touch`, `PR-only`, no release, no commit, or a named terminal state, report broader risks without expanding edits or delivery scope.
- If a risk crosses modules, products, repositories, or ownership boundaries, report the evidence and recommended next action before changing scope.
- After a durable finding, consider whether it belongs in a test, project rule, project skill, design note, README, or local handoff. Do not turn one-off facts into global rules.
- Persistent memory, global rules, global skills, and cross-project tooling require explicit user approval before writing.

## Design And Architecture

- Start design and architecture work from business semantics: domain objects, state ownership, lifecycle transitions, inputs/outputs, invariants, and external contracts.
- Locate the fact source, central writer, and shared lifecycle path before adding state logic or proposing new abstractions.
- Inspect existing primitives, module boundaries, and runtime wiring before redesign. Prefer boundary propagation, connection fixes, or existing abstractions when they fit.
- Do not merge similar concepts too early. Separate current state, historical fact, configuration contract, runtime side effect, and public API before abstracting.
- Keep external contracts stable and simple. Put compatibility, migration, cleanup, and recovery complexity behind internal shared paths.
- Product or architecture direction should normally become a design note, issue, plan, acceptance criteria, or reviewed proposal before implementation.
- Architecture review should cover provider/consumer order, startup/shutdown, hot reload, async blocking, cache persistence, concurrency races, and tests that exercise the real path.

## Implementation And Verification

- For behavior changes and bug fixes, prefer a failing test, focused reproduction, or concrete failing evidence before implementation; then make the smallest credible change and verify it.
- High-risk or complex behavior should use stricter test-first discipline when feasible. Pure documentation, read-only review, mechanical formatting, and no-behavior text edits can use readback, lint, rendering, privacy scan, or focused review instead.
- Tests should protect durable behavior, contracts, business boundaries, and real workflows. Avoid tests that only preserve outdated wording, historical implementation details, file existence, or scenario names.
- Preserve stable in-repo contracts. Do not casually change keys, IDs, config fields, storage fields, public APIs, public payloads, or internal contracts unless the user asked for that boundary to move.
- Do not add broad defensive compatibility around stable internal objects. Use dynamic access for real dynamic boundaries such as external payloads, cross-version data, or optional capabilities.
- Comments, logs, and README text are maintenance surfaces. Keep wording plain and timeless; avoid jargon and change-narration such as "this change", "previously", "for this PR", or "historically" unless the file is explicitly a changelog or migration note.

## Subagent Collaboration

Custom agents are fixed role templates, not background services. Skill text can recommend a reviewer, but it does not by itself authorize spawning. Only spawn when the user explicitly asks for subagents, parallel/delegated work, an independent agent Review, or when the current platform policy clearly allows it and the user grants permission after a short prompt.

When spawning is authorized, the main agent keeps design/implementation/integration ownership, passes explicit boundaries, integrates feedback, and remains accountable for the final decision. Each subagent consumes its own tokens, time, and tool calls, so keep fan-out to the smallest set that materially improves independence, parallelism, or quality.

Default roles:

- `research-reviewer`: unfamiliar domains, official docs, standards, ecosystem practice, or privacy-safe community best-practice checks.
- `design-reviewer`: product, design, architecture, workflow direction, business boundaries, lifecycle semantics, and same-class risk.
- `plan-reviewer`: implementation plan, task split, dependency order, acceptance criteria, rollback, and verification strategy.
- `implementation-reviewer`: code changes, tests, contracts, maintainability, and same-class implementation risks.
- `delivery-reviewer`: PR, release, issue reply, public comments, privacy, scope, verification evidence, and maintainer-facing text.
- `final-reviewer`: whole-task closure across user request, design, plan, implementation, tests, docs, delivery, and unresolved feedback.

Keep fixed agents review/research-oriented by default. The main agent should normally draft the design, write the plan, implement code, run key verification, and integrate decisions. Spawn worker-style implementation or testing agents only when the task can be split into clear, low-coupling ownership areas with limited conflict risk.

Review budget:

- Default to the single reviewer that best matches the current risk. Do not chain `plan-reviewer`, `implementation-reviewer`, and `final-reviewer` for ordinary behavior changes.
- Add a second reviewer only when the task crosses distinct concerns, such as design plus delivery, source truth plus public reply, or implementation plus durable rule changes.
- Use `final-reviewer` when closure risk is real: public delivery, durable rules or skills, multiple reviewers, unresolved reviewer feedback, cross-contract behavior, or explicit user request. For a single focused implementation review with all feedback resolved, a main-thread closure summary is enough.
- Do not rerun equivalent verification or Review unless new evidence, changed scope, failed verification, or unresolved feedback makes the previous pass stale.

Authorization and prompt rules:

- Treat phrases such as `subagent`, `parallel agent`, `delegate`, `开独立 agent`, `并行`, `独立 Review`, `reviewer agent`, or explicit approval after being asked as current-task authorization for the minimum necessary fan-out.
- Treat plain `review`, `检查`, or `看一下` as main-thread review unless the user asks for independent/subagent review or the task's risk justifies asking for authorization.
- If a task would materially benefit from an independent reviewer but the user did not authorize spawning, ask a short yes/no question before spawning. Continue in the main thread when the user declines or when waiting would be disproportionate.
- Do not spawn for simple one-command answers, simple translations, low-risk read-only explanations, local cleanup that does not change behavior or durable rules, or when the user waives review. Public PR, release, issue, or review replies should ask for or use an authorized `delivery-reviewer` unless the user explicitly waives it.

Candidate review points, subject to authorization and the review budget above:

- Before design or architecture decisions: use `research-reviewer` if the domain or best practice is unfamiliar; use `design-reviewer` for the proposed direction.
- Use `plan-reviewer` before implementation when the plan spans multiple files or phases, changes contracts, state lifecycle, public output, durable rules, or skills, or needs explicit acceptance criteria, rollback, migration, or parallel ownership.
- For fact verification, choose the matching reviewer: `implementation-reviewer` for source behavior, code-path bugs, reviewer claims, and log symptoms; `research-reviewer` for official docs, standards, ecosystem facts, and community practice; `delivery-reviewer` for release artifacts, PR/issue facts, public text, and maintainer-facing delivery claims.
- Use `implementation-reviewer` after a focused implementation slice when the main risk is code correctness, tests, contracts, maintainability, or same-class implementation paths. Skip a separate implementation review when an earlier reviewer already covered the same risk and no relevant implementation facts changed.
- Before public delivery, PR, release, or issue/review reply: use `delivery-reviewer`.
- Use `final-reviewer` only for the closure-risk cases listed in Review budget, unless the user explicitly requests final Review.
- For parallel implementation or testing: use temporary workers only when ownership, files, expected output, and integration points are explicit and disjoint.

Subagent prompts must include only:

- target files, branch, or scope
- user-stated boundaries and forbidden actions
- explicit read-only instruction for reviewer/research agents: no file edits, no approval requests for write/publish actions, no commit, no push, no public comments, no release
- acceptance goals and expected output format
- expected output language; default to Chinese when the user or task prompt is Chinese
- necessary fact-source entry points
- whether to wait synchronously or continue asynchronously

Do not pass the main agent's conclusion, intended fix, or hidden rationale to independent reviewers unless the validation explicitly needs it. Substantive reviewer feedback must be fixed, verified, or rejected with evidence. Do not claim completion while a required review gate remains unresolved.

For independent review, use `fork_context=false` by default when the spawn interface supports it. Fork context only when the reviewer cannot understand the task from the explicit prompt, target files, user boundaries, and fact-source entry points.

Subagent timeout is normal. Continue non-overlapping work while waiting. Strong-gate tasks are not complete until the review returns, is replaced by an equivalent reviewer, or the user explicitly waives the gate.

## Delivery And Privacy

- Before commit or push, inspect repository status and scope. Do not mix unrelated local changes.
- Public PR, issue, release, review text, skill frontmatter, README text, global rules, and installed skill copies must be privacy-safe: no local absolute paths, usernames, tokens, secrets, private config, sandbox details, temporary files, machine state, private project names, unrelated PR/issue numbers, or private version/history fingerprints.
- Public text should be useful to maintainers and community readers, not a local execution transcript. Use real Markdown paragraphs; prefer body files or structured payloads for multi-line GitHub text, then read back important published content when feasible.
- If the user specifies `PR-only`, read-only, no release, no commit, or a specific terminal state, stop there unless the user expands scope.
