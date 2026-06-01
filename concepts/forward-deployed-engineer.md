---
type: concept
title: "Forward Deployed Engineer (FDE)"
created: 2026-06-01
updated: 2026-06-01
tags: [fde, roles, anthropic, palantir, applied-ai, yc]
links: [companies/anthropic]
---

# Forward Deployed Engineer (FDE)

## Concept

FDE — forward deployed engineer — это гибридная инженерно-консалтинговая роль. Встраиваешься в команду клиента как инженер, строишь продакшн-приложения на базе AI/LLM, но при этом работаешь от лица вендора.

Отличие от professional services / consulting: FDE — это не процесс-консалтинг, а **building**. Ты пишешь код, строишь пайплайны, поставляешь работающий продукт. При этом клиент получает "white glove" поддержку от вендора напрямую.

## Происхождение: Palantir

Модель изобретена в Palantir для работе с разведкой. Проблема: **никто не знает шпионов**, и шпионы не расскажут что делают. Стандартный процесс:
1. Built a demo
2. Took it to customers → "This is terrible, this isn't related to what we do at all"
3. Founder Stefan Cohen спрашивал: "How would you like it to be different?"
4. Клиенты описывали изменения — он записывал всё

**Ключевой инсайт Sean Shankar (Palantir CTO):** Instead of building two products or building the exact right feature for each site, they built a **platform** that could be customized. Это создало потребность в людях на каждом сайте = FDE.

**Переворорот:** Исторически services — это то, что хочешь минимизировать. Sean понял что можно **перевернуть и сделать services ценным**.

## Echo Team vs Delta Team

### Echo Team (Embedded Analysts)

- Go to customer site
- Speak to users
- Figure out what demo/use case makes sense
- Also account managers managing relationships

**Profile:** Domain experts — former army officers, people with deep healthcare experience. Нужны **еретики/rebels** — люди которые понимают как сейчас делается работа и знают что это недостаточно.

> "They need to be someone who understands how things are done right now and recognizes that it's insufficient. If their perspective is 'it was great,' then they're never going to be able to figure out the step function change."

**Ключевое требование:** If you can't make a **3x or 10x change** within that organization, there was no reason to go through all the effort.

### Delta Team (Deployed Engineers)

- Software engineers extremely good at writing code quickly
- "Eating a lot of pain"
- Take ideas and build solutions, prototypes, deploy for customer

**Profile:** Prototypers. Not craftsmen who want perfect abstractions.

> "Someone who's a craftsman, who really loves making sure the abstractions are exactly right" — wrong profile. They may write code that has to be thrown away. That's not the job.

### Аналогия с основателем стартапа

> "It sounds a lot like a founding team... You're a startup founder where you have access to some very powerful piece of product leverage."

Это почему Palantir породил так много стартапов. FDE training = startup founder skills.

## Как отличить real software от consulting

Тест на то, настоящий ли это software, не consulting:

1. **Early:** You may be losing money at new deployments
2. **Over time:** Product gets better suited to what customers do (no longer need large teams at each site)
3. **Over time:** You're earning the right to access more important problems at the customer site
4. **Result:** Cost per value of outcome goes down → profit margins start negative, become positive

> "If you look at it from that perspective, you can see that you're actually delivering real repeatable value."

## Key Characteristics

- **Встраивание в клиента**: физически/удалённо присутствуешь в команде заказчика на уровне strategic customer
- **Production building**: MCP servers, sub-agents, agent skills — всё продакшн, не прототипы
- **Autonomy under ambiguity**: клиенты — сложные организации, много неопределённости, нет готовых ответов
- **Forward-deployed motion**: формируешь саму практику —初期 сотрудники этой функции
- **Travel**: до 25% на site клиента

## Technical Scope

- Building production applications with Claude models
- MCP servers, sub-agents, agent skills
- Enterprise deployment patterns
- Advanced prompt engineering, agent development, evaluation frameworks
- Python as primary language

## FDE vs adjacent roles

| | FDE | Professional Services | Solutions Engineer | Technical Founder |
|---|---|---|---|---|
| Who they work for | AI vendor | AI vendor | AI vendor | Startup |
| What they build | Production AI systems | Implementations | Demos/POCs | Everything |
| Customer relationship | Embedded, long-term | Project-based | Pre-sales | Own product |
| Autonomy | High | Medium | Medium | High |

## FDE at Anthropic (Applied AI)

Anthropic FDE встраивается в стратегических клиентов и строит продакшн-приложения на Claude. Это founding FDE — формируешь саму практику.

**Salary range:** $200K–$300K USD
**Locations:** Boston, NYC, Seattle, San Francisco, Washington DC (hybrid, ≥25% in-office)
**Travel:** up to 25%

## Adoption

Модель стала доминирующей структурой для AI agent стартапов. YC job board: **100+ стартапов** нанимают FDE роли — было практически 0 три года назад.

## Sources

[Source: Anthropic job posting — Forward Deployed Engineer, Applied AI, 2026-06-01](https://job-boards.greenhouse.io/anthropic/jobs/4985877008)
[Source: Y Combinator YouTube — The FDE Playbook for AI Startups with Bob McGrew, 2026-06-01](https://youtu.be/Zyw-YA0k3xo) — Bob McGrew, early Palantir engineer, former CRO at OpenAI (led ChatGPT, GPT-4, o1)