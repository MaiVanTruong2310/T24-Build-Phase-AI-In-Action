---
name: agent-skills
description: Production-grade senior engineering workflows by Addy Osmani (Google). Covers SDLC phases including Define (/spec), Plan (/plan), Build (/build), Verify (/test), Review (/review), Simplify (/code-simplify), and Ship (/ship).
---

# Agent Skills — Senior Engineering Workflows (Addy Osmani)

Curated workflows, quality gates, and anti-excuse checklists designed by Addy Osmani (Google) to bring senior engineering discipline to AI coding agents.

Repository: `https://github.com/addyosmani/agent-skills`
Documentation: `https://skills.addy.ie`

---

## 1. The 7 Engineering Lifecycle Phases

| Command / Phase | Focus | Core Question |
| :--- | :--- | :--- |
| `/spec` (Define) | Requirements & Constraints | *What problem are we truly solving, and what are the edge cases?* |
| `/plan` (Plan) | Task Decomposition | *How do we break this into atomic, independently verifiable tasks?* |
| `/build` (Build) | Incremental Implementation | *Can each change be verified in isolation before proceeding?* |
| `/test` (Verify) | Evidence-Based Correctness | *Where is the proof that this works and regressions were prevented?* |
| `/review` (Review) | Security, Quality, Perf | *Would this pass a strict senior engineer code review?* |
| `/code-simplify` (Simplify) | Clarity over Cleverness | *Can this be made more obvious, with less indirection and dead code?* |
| `/ship` (Ship) | Safe Release Checklist | *Is there a rollback plan, zero breaking changes, and green CI?* |

---

## 2. Anti-Rationalization Table (Guards Against Agent Mistakes)

| Tempting Shortcut / Excuse | Required Senior Agent Behavior |
| :--- | :--- |
| *"The change is too small to need tests."* | Write at least one unit/regression test confirming the bug fix. |
| *"I'll fix the TypeScript error with `any` for now."* | Model the exact type or interface properly. Never introduce `any`. |
| *"I will rewrite this whole module from scratch."* | Use incremental slices. Keep existing working code intact unless asked. |
| *"The build succeeded, so it must work."* | Perform functional runtime verification (test runner, CLI run, curl). |
| *"I'll clean up the code later."* | Run `/code-simplify` before considering any task complete. |

---

## 3. Standard Verification Checklist

Before reporting task completion to the user:
- [ ] Requirements from prompt are 100% fulfilled.
- [ ] No regression introduced to existing tests or builds (`npm run build` / `pytest`).
- [ ] Unused imports, console logs, and temporary comments cleaned up.
- [ ] Error handling covers edge cases (null/undefined, network failures, timeouts).
