# Brain Schema — Page Conventions and Templates

## Two-Layer Page Structure

Every brain page has two layers, separated by `---`:

**Above the line — Compiled Truth.** Current state, executive summary, structured fields, open threads, see also.

**Below the line — Timeline.** Append-only reverse-chronological evidence log.

## Standard Fields

```yaml
---
slug: entity-slug
aliases: [variant names, emails, handles]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## Standard Sections (above the line)

1. **Executive Summary** — 1 paragraph, what matters most
2. **State** — key current facts
3. **Open Threads** — active items (removed when resolved)
4. **See Also** — cross-links to related pages

## Citation Format

Every claim below the line must cite source:
- `[claim] — source: [type], date`
- Types: meeting, email, tweet, article, interview, observed, self-described, inferred

## Quality Rules

- No placeholder dates (e.g. "March 2024" not "last month")
- Use [[page-slug]] for internal links
- One entity per page — aliases handle variants
- Never duplicate content across pages — use cross-references instead
