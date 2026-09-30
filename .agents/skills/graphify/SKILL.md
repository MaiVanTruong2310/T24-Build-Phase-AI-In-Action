---
name: graphify
description: Codebase knowledge graph and deterministic AST query engine by Graphify Labs. Use to parse codebases into queryable AST graphs to trace call hierarchies, module dependencies, circular references, and impact analysis without relying on grep.
---

# Graphify — Codebase Knowledge Graph Skill

**Graphify** turns source code, schemas, and architecture into a queryable AST knowledge graph, giving AI coding assistants deterministic structural understanding.

Repository: `https://github.com/Graphify-Labs/graphify`

---

## 1. When to Use

- **Deep Impact Analysis:** Find every function, class, or endpoint affected before making a breaking refactoring.
- **Trace Call Hierarchies:** Identify all callers (upstream) and callees (downstream) for a given symbol.
- **Detect Architectural Violations:** Detect circular dependencies between packages or layered architecture leaks (e.g. controllers importing database sessions directly).
- **Dead Code Elimination:** Identify orphaned methods and exports that have zero incoming references.

---

## 2. Command Reference

```powershell
# Index the current repository into an AST graph
npx @graphify-labs/cli index .

# Query who calls a specific function
npx @graphify-labs/cli query callers --symbol "createSessionId"

# Query what a function depends on
npx @graphify-labs/cli query callees --symbol "sendMessage"

# Inspect circular dependencies in the codebase
npx @graphify-labs/cli audit circular

# Check impact of modifying a specific file
npx @graphify-labs/cli impact --file "src/features/chat/api.ts"
```

---

## 3. Workflow for Agents

1. **Before Large Edits:** Run `npx @graphify-labs/cli impact --file <file>` to discover all consumers.
2. **Understand Unfamiliar Code:** Query the graph for high-degree nodes (core orchestrators) rather than reading files sequentially.
3. **Verify Refactorings:** Check that zero unresolved references or broken AST edges remain after symbol renames.
