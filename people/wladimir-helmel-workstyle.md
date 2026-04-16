---
slug: wladimir-helmel-workstyle
created: 2026-04-16
updated: 2026-04-16
tags: [person, wladimir, workstyle, tools, setup, n8n, claude-code, hermes, how-i-work]
links: [wladimir-helmel, german/language-learning]
---

# Как я работаю — Wladimir Helmel

## Мой стек

### AI-ассистенты (моя команда)
| Инструмент | Роль | Зачем |
|------------|------|-------|
| **Hermes** (me) | Second brain, router, scheduler | Знания, контекст, память, напоминания |
| **Claude Code** | Programming agent | Код пишет сам, я ставлю задачу |
| **ChatGPT / o4-mini** | Reasoning, brainstorming | Быстрые вопросы, прототипы |
| **Perplexity** | Research | Факты, компании, технологии |

### Операционка
| Инструмент | Зачем |
|------------|-------|
| **n8n** | Workflow automation. Единственный, который я ставлю на прод. Держу на VPS |
| **GitHub / GitLab** | Code, CI/CD, infra as code |
| **Telegram** | Коммуникация с Hermes (и не только) |
| **1Password** | Пароли, secrets |
| **Notion / Obsidian** | Заметки, документация |

### Для программирования
- **VS Code + Claude Code extension** — основная IDE
- **Cursor** — для быстрых правок
- **Python** — основной язык для автоматизации
- **Bash / Zsh** — CLI everywhere
- **Docker** — контейнеризация

### Мониторинг
- **Grafana + Prometheus** — если есть
- **Sentry** — ошибки продакшена
- **CloudWatch / GCP logs** — если на облаках

---

## Как я работаю с задачами

### Level 1: Быстрая задача (< 30 мин)
Сам. Claude Code если нужен код. Hermes для поиска.

### Level 2: Средняя задача (30 мин — 2 часа)
Обсуждаю с Claude Code, потом сам доделываю.

### Level 3: Большая задача (2+ часа / проект)
1. Ставлю задачу Claude Code
2. Промежуточные результаты — в brain
3. Финальный результат — review + commit

### Level 4: Поток информации
```
RSS → blogwatcher → gbrain → Hermes morning briefing
```
Не читаю ленту каждый день. Получаю сводку утром.

---

## Как я работаю с процессами

### Принцип: Automate or Kill

Если процесс повторяется 3 раза:
1. Документирую
2. Автоматизирую если стоит усилий
3. Если автоматизация сложнее процесса — упрощаю процесс

### Документация

- **Не пишу documentation ради documentation**
- Пишу только то, что сэкономит время в будущем
- Каждая страница в brain имеет: контекст, что делать, линки

---

## Как я усилю вашу команду

### Боль, которую я решаю

| Проблема | Решение |
|----------|---------|
| "У нас 5 разных систем и данные не сходятся" | Интеграции, единый источник правды |
| "DevOps занимает 50% времени рутиной" | Автоматизация deployment, monitoring, alerting |
| "Онбординг нового сотрудника = 2 недели" | Self-service portal, IaC, документация в brain |
| "Мониторинг есть, но никто не понимает что происходит" | Dashboards, alerts с контекстом |
| "Автоматизация сломалась и никто не заметил" | Observability: качество, latency, стоимость |

### Что вы получите от меня

**Day 1:**
- Понимание где Bottlenecks
- Быстрые победы (low-hanging fruit)
- Видение архитектуры

**Day 30:**
- Работающий MVP ключевой проблемы
- Приоритизированный roadmap
- Команда знает что делать

**Day 90:**
- Измеримый результат (время / деньги / ошибки)
- Процессы на автопилоте
- Следующие 3 проблемы понятны

---

## Мой подход к архитектуре

```
Prefer: Simple > Elegant > Complex
Prefer: Fast MVP > Perfect design
Prefer: Observable > "it works"
```

Не строю rocket science там, где достаточно rocket.

---

## Что меня отличает

1. **Я вижу процесс, а не технологию** — мне не нужно "внедрить Kubernetes". Мне нужно решить проблему. Kubernetes может быть решением, может и не быть.
2. **Я строю на будущее** — каждая автоматизация today — это задел для tomorrow
3. **Я говорю правду** — если решение плохое, я скажу. Не потому что хочу спорить, а потому что потом будет хуже
4. **Я не боюсь legacy** — работал с SAP, с 15-летними системами, с данными в Excel. Знаю как улучшать, не ломая.

---

## Контакт

📧 helmelwa@gmail.com
📱 +491****1341
🔗 linkedin.com/in/helmelwa
🌍 Munich, Germany (CEST/UTC+2)

---

## Links
- [[wladimir-helmel]] — моя история / мотивация
- [[german/language-learning]] — German setup
