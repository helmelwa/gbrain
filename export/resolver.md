---
type: concept
title: Resolver
---

# Brain Resolver — Master Filing Decision Tree

Before creating any new page, read this resolver. Every page goes through this decision tree.

## The Tree

1. **Is it a human being?** → `people/`
2. **Is it an organization/company?** → `companies/`
3. **Is it a financial transaction with terms?** → `deals/`
4. **Is it a record of a specific meeting event?** → `meetings/`
5. **Is it something being actively built with a repo/team?** → `projects/`
6. **Is it a possibility nobody is building yet?** → `ideas/`
7. **Is it a mental model or framework you'd teach?** → `concepts/`
8. **Is it a prose artifact (essay, draft, philosophy)?** → `writing/`
9. **Is it a major life workstream?** → `programs/`
10. **Is it about your institution's strategy/ops?** → `org/`
11. **Is it political landscape/policy/government?** → `civic/`
12. **Is it public narrative/content ops/social?** → `media/`
13. **Is it private notes/health/personal reflection?** → `personal/`
14. **Is it domestic operations/properties?** → `household/`
15. **Is it a candidate pipeline/evaluation?** → `hiring/`
16. **Is it raw data import or archived snapshot?** → `sources/`
17. **Is it an unsorted quick capture?** → `inbox/`
18. **Nothing fits?** → `inbox/` and flag for schema evolution

## Key Disambiguation Rules

- **Concept vs. Idea:** Could you *teach* it as a framework? → concept. Could you *build* it? → idea.
- **Concept vs. Personal:** Would you share it professionally? → concept. Private reflection? → personal.
- **Idea vs. Project:** Anyone working on it? Yes → project. No → idea.
- **Writing vs. Media:** Writing is the artifact (essay). Media is the production/distribution infrastructure.
- **Person vs. Company:** About *them as a human*? → people/. About *the organization*? → companies/.
- **Household vs. Personal:** Would a PA execute on it? → household. Private reflection? → personal.

## Filing Rules

- One directory per knowledge domain
- One file per entity
- Every directory has a README.md resolver
- Primary home only — use backlinks for cross-references
- When in doubt, inbox it — it's a signal the schema needs evolution
