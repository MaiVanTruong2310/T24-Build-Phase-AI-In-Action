---
name: ponytail
description: The Lazy Senior Developer philosophy by Dietrich Gebert. Use to write minimal, maintainable code by leveraging platform-native APIs, standard libraries, and avoiding bloatware, over-engineering, and unnecessary dependencies.
---

# Ponytail — The Lazy Senior Developer Skill

The **Ponytail** philosophy is inspired by experienced senior engineers who prefer doing things simply, cleanly, and without unnecessary code or dependencies.

> "The best code is the code you never had to write, debug, or maintain."

---

## 1. Core Principles

1. **Platform Native First (YAGNI):**
   - Always prefer built-in language and web platform APIs before reaching for an external library.
   - If modern browsers or standard runtimes already do it natively, do NOT install an npm package or pip library.

2. **Surgical Precision:**
   - Modify the minimum lines of code required to achieve the goal.
   - Avoid rewrites or refactoring unrelated files during bug fixes.
   - Preserve existing architectural conventions and style.

3. **No Over-Engineering:**
   - Don't build abstract factory wrappers around a 3-line function.
   - Don't build generic multi-tenant plugin architectures for a feature that only has one use case today.
   - Avoid deep inheritance or complex generic type acrobatics when simple types suffice.

---

## 2. Common Native Replacements

| Instead of (Bloatware) | Use (Native Platform) | Why |
| :--- | :--- | :--- |
| `axios` / `request` | `fetch` (built-in) | Native in all modern browsers and Node 18+ |
| `lodash` (map, filter, clone) | `Array.map`, `structuredClone`, `Object.assign` | Zero runtime overhead |
| `qs` / `query-string` | `new URLSearchParams()` | Standard Web API |
| `crypto-js` | `crypto.subtle` / `crypto.randomUUID()` | Built into browser and Node |
| `moment.js` / `date-fns` | `Intl.DateTimeFormat` / native `Date` | Built-in localization, 0 kB bundle |
| Complex state libraries | React `useState` / `useReducer` / URL search params | Built-in, simpler mental model |
| Custom CSS grid frameworks | Native CSS Grid & Flexbox | Supported everywhere natively |

---

## 3. Checklist Before Committing Code

- [ ] Can this be solved with standard library features instead of installing a new package?
- [ ] Did I delete unnecessary temporary code, commented-out blocks, or debug console logs?
- [ ] Is the solution easy to understand for another developer reading it 6 months from now?
- [ ] Did I avoid modifying files that were working and unrelated to the task?
