---
type: concept
title: Aidesigner Mcp
---

# AIDesigner MCP Server

## URL
https://www.aidesigner.ai/docs/mcp

## What it is
MCP Server for generating and refining production-ready UI designs from Claude Code, Codex, Cursor, VS Code / Copilot, or Windsurf.

## Quick Start
```bash
npx -y @aidesigner/agent-skills init
```

## Installation

### Hosts: Claude Code, Codex, Cursor, VS Code / Copilot, Windsurf

**Project setup:**
```bash
npx -y @aidesigner/agent-skills init
```
Writes: `.mcp.json`, `.claude/agents/aidesigner-frontend.md`, `.claude/commands/aidesigner.md`, `.claude/skills/aidesigner-frontend/SKILL.md`

**User setup:**
```bash
npx -y @aidesigner/agent-skills init claude --scope user
```

### MCP Server Config
```json
{
  "mcpServers": {
    "aidesigner": {
      "type": "http",
      "url": "https://api.aidesigner.ai/api/v1/mcp"
    }
  }
}
```

### Verify
```bash
npx @aidesigner/agent-skills doctor --all
```

### Upgrade
```bash
npx -y @aidesigner/agent-skills upgrade codex --trust-project
```

## Authentication
- OAuth flow for MCP clients (Claude Code, Cursor, etc.)
- Browser opens for sign-in
- Tokens stored and refreshed automatically by client

**REST API fallback (CI/CD):**
```bash
export AIDESIGNER_API_KEY="your-api-key"
npx @aidesigner/agent-skills generate --prompt "landing page hero"
```

### Environment Variables
| Name | Type | Description |
|------|------|-------------|
| AIDESIGNER_BASE_URL | string | API base URL. Defaults to https://api.aidesigner.ai |
| AIDESIGNER_MCP_URL | string | MCP endpoint URL |
| AIDESIGNER_API_KEY | string | API key for non-MCP auth |
| AIDESIGNER_MCP_ACCESS_TOKEN | string | Direct MCP access token (advanced) |

## Rate Limits
- `generate_design` and `refine_design`: 30 / 60s per account
- Concurrent remote generations: 4 in flight per account
- 429 Too Many Requests + Retry-After header

## MCP Tools

### generate_design
**CORE** — Generate new HTML/CSS from text prompt. Returns complete HTML with inline Tailwind CSS.

Parameters:
- `prompt*` (string) — Natural language description
- `repo_context*` (object) — Compact repo summary (framework, tokens, routes)
- `viewport` ("desktop" | "mobile") — Defaults to desktop (1440px)
- `mode` ("inspire" | "clone" | "enhance") — Optional reference mode
- `url` (string) — Reference URL for clone/enhance/inspire

### refine_design
Iterate on previous design using natural language feedback.

Parameters:
- `run_id_or_html*` (string) — Previous run ID or raw HTML
- `feedback*` (string) — What to change
- `repo_context*` (object)
- `viewport` ("desktop" | "mobile")
- `mode` ("inspire" | "clone" | "enhance")
- `url` (string)

### get_credit_status
Check credit balance, usage, subscription status. No params.

### whoami
Returns connected account identity and OAuth scopes. No params.

## Design Modes

| Mode | Use when |
|------|----------|
| `inspire` | "Make something like this but for our brand" |
| `clone` | Near-1:1 recreation |
| `enhance` | Improve existing URL |
| `none` (default) | Pure prompt-driven, no reference URL |

Note: When mode is set, url is required. Website analysis costs 1 credit.

## Artifact Storage
Generated designs saved in `.aidesigner/` at project root:
```
.aidesigner/runs/<run-id>/design.html  # Generated HTML
.aidesigner/runs/<run-id>/repo-context.json
.aidesigner/runs/<run-id>/request.json
.aidesigner/runs/<run-id>/summary.json
.aidesigner/runs/<run-id>/preview.png
.aidesigner/runs/<run-id>/adoption.json
.aidesigner/runs/<run-id>/latest.json
```

Add `.aidesigner/*` and `!.aidesigner/.gitkeep` to .gitignore (init does this automatically).

## Repo Context Analysis
CLI automatically analyzes project: framework (Next.js, React, Vue), styling (Tailwind, CSS variables), component libraries (Radix, shadcn/ui), routes, CSS tokens.

## Adoption Briefs
```bash
aidesigner adopt --id <run-id>
```
Generates structured porting guide — target framework, route placement, CSS tokens, reusable components.

## CLI Reference
| Command | Description |
|---------|-------------|
| `init [host] [--scope user] [--all]` | Install MCP config |
| `upgrade [host] [--scope user] [--all]` | Refresh config |
| `doctor [host] [--all]` | Validate setup |
| `generate --prompt "..."` | Generate design |
| `refine --id <run-id> --prompt "..."` | Refine design |
| `capture --html-file <path> --prompt "..."` | Capture MCP output |
| `preview --id <run-id>` | Render PNG preview |
| `adopt --id <run-id>` | Generate adoption brief |

Common options: `--scope`, `--cwd`, `--out-dir`, `--viewport`, `--mode`, `--url`

## Relevance for Wladimir
- Useful for DevOps dashboards / self-service portal UI prototyping for FUTRUE case
- MCP integration for coding agents (Codex, Claude Code) — could enhance brain coding capabilities
- Terminal-based workflow aligns with DevOps mindset
