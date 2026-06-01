---
title: "Devbox: Fixed the Worst Part of Local Development"
source: youtube
url: https://www.youtube.com/watch?v=U7YDcqP0dlI
date: 2026-01-01
tags: [devbox, nix, developer-tools, dev-environment, local-dev]
---

# Devbox: Fixed the Worst Part of Local Development

Devbox solves one of the most annoying parts of local development: **broken dev environments**, outdated README setup steps, slow Docker workflows, and the classic "works on my machine" problem. It creates reproducible development environments using Nix under the hood — without requiring you to learn Nix.

## Core Concept

> "Your dev environment should not live in a readme, it should live in Git. That's what Devbox does. One devbox.json file, one command, devbox shell, same environment for every dev."

**Key Benefits:**
- No global installs
- No Nix knowledge required
- Project-specific tools
- Environment lives in the repo, not someone's memory

## Quick Start Workflow

```bash
# 1. Initialize a new project
devbox init

# 2. Add required tools (Go, Node, Python, Postgres, etc.)
devbox add go nodejs python311 postgresql

# 3. Enter the reproducible environment
devbox shell

# 4. Run project scripts
devbox run test
```

### Example `devbox.json`

```json
{
  "packages": ["go", "nodejs", "python311", "postgresql"],
  "scripts": {
    "test": "echo 'Running tests' && go test ./..."
  }
}
```

## How It Works

### Two Important Files

| File | Purpose |
|------|---------|
| `devbox.json` | Defines what your environment needs |
| `devbox.lock` | Pins exact versions of installed packages |

Both files should be committed to Git for full reproducibility.

### Technical Foundation

- **Devbox uses Nix under the hood** for reproducibility
- Pins exact tool versions instead of "latest"
- Does **not touch your system** — tools belong to the project
- Works on **macOS, Linux, and WSL**

## Key Features

- Add/search tools via simple CLI commands
- Define scripts within `devbox.json`
- Manage services (databases, etc.)
- VS Code integration
- Export to Docker, Dev Containers, and CI workflows
- Clean exit (just run `exit` to return to normal system)

## Why Devbox Matters

### Problem 1: READMEs Lie

> "It says setup takes 5 minutes, then Node is wrong, Python is wrong, Postgres is missing, Docker is taking forever... You're debugging before you even get started."

### Problem 2: Onboarding Pain

> "You shouldn't need to ask, 'Which Node version do I need?' They should just have to clone the repo, enter the shell, and run the project."

### Problem 3: Global Pollution

> "Trying tools should not wreck your laptop. You want Go 1.22 for this repo? You add it. You want Node 20 here, but something else elsewhere? Fine."

## Devbox vs. Docker

| Aspect | Docker | Devbox |
|--------|--------|--------|
| Setup complexity | High | Low |
| Workflow | Container-based | Direct shell |
| Speed | Slower (containers) | Faster (local) |
| Use case | When you need containers | Tool management |

> "Docker is still great. If you need containers, use containers. But a lot of teams use Docker locally because they don't have a better way to manage tools."

## Downsides & Considerations

1. **First download is slow** — Initial Nix store download takes time
2. **JSON complexity** — Can get ugly with too much setup logic. For complex setup logic, put it in a SH file, then call that from Devbox.
3. **Not a cloud IDE** — If you need browser-based coding with instant preview URLs, consider CodeSpaces instead
4. **Best for local and CI reproducibility** — Not a full development platform

## When to Use Devbox

**Best suited for:**
- Projects with **multiple languages** (e.g., Go + Node + Python)
- Projects with **multiple CLI tools**
- Teams struggling with inconsistent dev environments
- Reducing onboarding time for new developers

> "Devbox is not going to solve every development problem, but it can solve the ones that annoy us the most, which is really just getting the project to run."

## Video Chapters

| Time | Topic |
|------|-------|
| 0:00 | Fix Broken Dev Environments with Devbox |
| 0:35 | What Is Devbox and Why Developers Use It |
| 1:20 | Devbox Demo: Create a Reproducible Dev Environment |
| 2:57 | How Devbox Works with Nix Under the Hood |
| 3:25 | Why READMEs Fail for Local Development Setup |
| 4:30 | Faster Developer Onboarding with Devbox |
| 5:34 | Devbox vs Docker and Dev Containers |
| 5:50 | What Developers Like About Devbox |
| 6:05 | Devbox Downsides and Things to Know |
| 6:30 | Should You Use Devbox for Local Development? |

## Resources

- **Devbox Site:** [jetify.com/devbox](https://www.jetify.com/devbox)
- **Devbox Repo:** [github.com/jetify-com/devbox](https://github.com/jetify-com/devbox)
- **Better Stack:** [betterstack.com](https://betterstack.com)

**TL;DR:** Devbox puts your dev environment in Git via `devbox.json`, enabling `devbox shell` to instantly create reproducible environments with specific tool versions — no global installs, no Nix learning curve. Best for multi-language projects needing consistent local + CI setups.
