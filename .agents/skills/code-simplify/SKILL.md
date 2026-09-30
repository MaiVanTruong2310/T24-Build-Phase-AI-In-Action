---
name: code-simplify
description: Code simplification and cognitive load reduction workflow from Addy Osmani's agent skills. Use to refactor complex code, eliminate dead code, flatten nested conditionals, and prioritize obvious clarity over cleverness.
---

# Code Simplify — Clarity Over Cleverness

Inspired by Addy Osmani's `/code-simplify` workflow: simplify code so that any developer can understand and maintain it instantly.

---

## 1. Principles of Code Simplification

1. **Flatten Deep Nesting:**
   - Use early returns / guard clauses instead of 4 levels of `if (a) { if (b) { if (c) { ... } } }`.
2. **Remove Dead & Redundant Code:**
   - Delete unreachable branches, unused variables, abandoned functions, and commented-out code blocks.
3. **Explicit Over Clever:**
   - Avoid cryptic one-liners, overly dense regular expressions, or nested ternary operators (`a ? b ? c : d : e`).
4. **Cohesion & Single Responsibility:**
   - If a function does 3 distinct things, split it into 3 small, well-named functions.
5. **No Needless Indirection:**
   - If a function only calls another function with the same parameters and does nothing else, inline or simplify it.

---

## 2. Simplification Checklist

- [ ] Replaced nested `if/else` with early `return` or `continue`.
- [ ] Eliminated redundant state variables that can be derived from existing props/state.
- [ ] Removed unused imports and dead code.
- [ ] Verified that all unit tests still pass after refactoring.
