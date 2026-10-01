---
name: playwright-cli
description: Official Microsoft Playwright CLI browser automation toolkit. Use to automate browser testing, take screenshots, inspect DOM elements, capture network traffic, and evaluate UI states via token-efficient command-line actions without heavy MCP context bloat.
---

# Playwright CLI Browser Automation Skill

This skill teaches the agent how to use Microsoft's standalone `@playwright/cli` to automate, test, and visually inspect web applications via the command line.

## Key Benefits
- **Token Efficient:** Avoids streaming massive DOM accessibility trees into the model's context window. Uses discrete CLI calls and saves snapshots/screenshots to disk.
- **Fast & Deterministic:** Direct browser manipulation via headless/headed Chromium, Firefox, or WebKit.
- **Full DevTools Access:** Network inspection, console logging, localStorage/sessionStorage management, and video/trace recording.

---

## 1. Quick Start & Execution

Run commands using `npx @playwright/cli <command>`:

```powershell
# Open browser and navigate to a URL
npx @playwright/cli goto http://localhost:5173

# Take an inspection snapshot to obtain element refs
npx @playwright/cli snapshot

# Click an element
npx @playwright/cli click "button[type='submit']"

# Fill text into an input field
npx @playwright/cli fill "input[name='search']" "React"

# Capture a screenshot
npx @playwright/cli screenshot ./artifacts/screenshot.png

# Close browser session
npx @playwright/cli close
```

---

## 2. Command Reference

### Core Actions
| Command | Arguments | Description |
| :--- | :--- | :--- |
| `goto` | `<url>` | Navigate to target web page |
| `click` | `<target>` | Click on a button, link, or element |
| `dblclick` | `<target>` | Double-click an element |
| `fill` | `<target> <text>` | Clear and fill text into input/textarea |
| `type` | `<text>` | Type text into currently focused element |
| `hover` | `<target>` | Hover mouse over element (triggers tooltips/menus) |
| `select` | `<target> <val>` | Select value from dropdown `<select>` |
| `check` / `uncheck` | `<target>` | Toggle checkboxes or radio buttons |
| `snapshot` | `[target]` | Capture page DOM snapshot to obtain element references |
| `find` | `[text]` | Search page snapshot for text or regex |
| `eval` | `<func> [target]` | Evaluate JavaScript expression on page or element |

### Verification & Artifacts
| Command | Arguments | Description |
| :--- | :--- | :--- |
| `screenshot` | `[path]` | Capture full-page or element screenshot |
| `pdf` | `[path]` | Export page to PDF |
| `console` | `[min-level]` | Read browser console logs (`error`, `warn`, `info`) |
| `requests` | — | List all network requests made by the page |
| `request` | `<index>` | Inspect headers, body, and status of request #index |

### State & Storage
| Command | Arguments | Description |
| :--- | :--- | :--- |
| `localstorage-list` | — | List all localStorage key-values |
| `localstorage-set` | `<key> <val>` | Seed localStorage (e.g. auth tokens, theme) |
| `cookie-list` | — | List cookies for current domain |
| `set-color-scheme` | `light \| dark` | Emulate light or dark mode in browser |
| `resize` | `<width> <height>` | Emulate mobile/tablet viewport (e.g. `375 667`) |

---

## 3. Workflow for Web Testing

When testing a web application locally:
1. Verify the local server is running (e.g., `http://localhost:5173`).
2. Run `npx @playwright/cli goto http://localhost:5173`.
3. Check for runtime errors: `npx @playwright/cli console error`.
4. Perform interactions: `click`, `fill`, etc.
5. Capture proof: `npx @playwright/cli screenshot output.png`.
6. Terminate session: `npx @playwright/cli close`.
