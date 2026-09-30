---
name: ship-checklist
description: Pre-launch release and shipping checklist from Addy Osmani's agent skills. Use before merging to main, deploying to production, or marking feature development complete to ensure zero breaking regressions.
---

# Ship Checklist — Production Readiness Workflow

Inspired by Addy Osmani's `/ship` workflow: verify all safety, quality, and operational criteria before releasing code to production.

---

## Pre-Flight Quality Gates

### 1. Build & Compilation Gate
- [ ] TypeScript/Linter: `npm run build` or `ruff check` exits with code 0 without suppressed errors.
- [ ] Dependencies: No outdated, vulnerable, or duplicate packages introduced.

### 2. Test Verification Gate
- [ ] Existing automated test suite passes 100% (`pytest` / `npm test`).
- [ ] New feature or bug fix has direct automated test coverage.
- [ ] Edge cases tested (empty lists, null inputs, network timeouts, offline mode).

### 3. Security & Safety Gate
- [ ] No API keys, passwords, or secrets committed in git history or code files.
- [ ] All inputs sanitized and validated against injection/XSS.
- [ ] Environment variables documented in `.env.example`.

### 4. User Experience & Responsive Gate
- [ ] Mobile responsive check (no horizontal scrollbar on 375px viewport).
- [ ] Dark Mode and Light Mode tested for visual contrast and readable typography.
- [ ] Loading and empty states handled gracefully.
