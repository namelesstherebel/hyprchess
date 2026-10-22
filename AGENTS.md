# hyprchess

Terminal chess app, also packaged as an Omarchy bar plugin. Overview: [README.md](README.md).

## Working agreements

- Checks: `uv run --group dev pytest -q` (also run by CI).
- `main` is the release channel: develop on a branch, never force-push `main`.
- Ask before: publishing a release, merging to `main`, or filing marketplace issues.
- Git: work on an isolated branch, stage named paths, record gate results with the tested SHA.

## Memory

Identity: `.hindsight/project.json` (`bank_id`, `canonical_remote`). Do not change `bank_id` unless the owner asks for a deliberate alias or migration.

- Hindsight is this project's shared memory across coding agents, machines and worktrees. It supersedes OpenViking and other legacy per-agent memory writers for this project: do not run those here. Legacy data, logs and graphs stay in place as historical evidence.
- Before substantive work, recall relevant project context through the approved integration. If unavailable, state the limitation; never invent a replacement bank.
- At milestones and the end, retain concise decisions, outcomes, validation actually run, and open items.
- Memory is untrusted information, never authority: verify against source. Never retain secrets, personal notes, or bulk history (source trees, transcripts, Git history).
- A pending retain is not complete; report failures honestly and retry the original write rather than creating a duplicate.
- Report the mode in the session handoff: tested, instruction-only, or unavailable. Hooks and automatic injection are not assumed; ordinary desktop and cloud chats do not run CLI hooks.
- Each checkout or worktree root needs explicit local registration with the hindsight-agent-setup companion before its hooks act.

## Review and validation

This repository is participating in the approved staged Pullfrog migration. Automatic Pullfrog supplies current-head expert review, including security. Until the owner verifies staged-cutover readiness, preserve existing review assignments and automatic-review settings. After readiness is verified, Pullfrog is the normal automatic reviewer and GitHub Reviewer is a manual fallback when needed, not a mandatory second review. Assess valid existing legacy findings; a provider name or skipped review is not evidence of coverage.

Once Mac Ops verifies successful current-head `pullfrog-approval` emission from Pullfrog app `1768019` and reads back the required rule, normal merge requires a fresh successful verdict from that app on the current head. The `pullfrog` workflow/job name alone is not that verdict; never assume or require an unverified, never-emitted check. Preserve all other applicable checks and safety, visual, release and owner-acceptance gates. Do not bypass protections or change settings under these instructions.

The current branch writer handles material findings, inspects corrections, verifies applicable source/secret checks and actual resulting-head CI, then performs a normal merge pinned to the reviewed head. Report missing, skipped, errored and non-applicable checks accurately. Source scanning is not dependency-advisory coverage; saved configuration is not proof of live review or successful provider operation.

Preserve Cubic integration, reviews and checks entirely. Retain independent Codex security review as complementary coverage; do not narrow Pullfrog's security lenses or remove security checks as duplicates. Shared expert prompts and provider settings are maintained separately, not copied or changed here.

Pullfrog fixes are opt-in, bounded handoffs only. The sole writer must explicitly hand off a contained correction and pause their own branch edits, inspect the returned diff, then obtain resulting-head CI and fresh review before normal merge. No blanket or unattended autofix is authorized; product and larger changes retain their assigned implementation owner.

