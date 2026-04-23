---
title: API Server | Hermes Agent
url: https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server
tags: [hermes, api, openai-compatible, reference]
created: 2026-04-23
updated: 2026-04-23
---

# API Server | Hermes Agent

**URL:** https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server

Hermes Agent API Server — OpenAI-совместимый HTTP endpoint. Любой frontend (Open WebUI, LobeChat, LibreChat, NextChat, ChatBox и др.) подключается как к бэкенду OpenAI.

## Quick Start

```
# 1. ~/.hermes/.env
API_SERVER_ENABLED=true
API_SERVER_KEY=change-me-local-dev
# Опционально для браузерного доступа:
# API_SERVER_CORS_ORIGINS=http://localhost:3000

# 2. Запуск
hermes gateway
# → [API Server] API server listening on http://127.0.0.1:8642

# 3. Connect any OpenAI-compatible client → http://localhost:8642/v1
```

## Endpoints

| Endpoint | Description |
|---|---|
| `POST /v1/chat/completions` | Stateless, full conversation in `messages` array, supports streaming + inline images |
| `POST /v1/responses` | Stateful via `previous_response_id`, server stores full conversation history |
| `GET /v1/responses/{id}` | Retrieve stored response by ID |
| `DELETE /v1/responses/{id}` | Delete stored response |
| `GET /v1/models` | Model discovery (advertises profile name or `hermes-agent`) |
| `GET /health` | Health check `{"status": "ok"}` |
| `GET /health/detailed` | Extended health: active sessions, running agents, resource usage |
| `POST /v1/runs` | Create agent run, returns `run_id` for subscribing to progress |
| `GET /v1/runs/{run_id}/events` | SSE stream of run's tool-call progress, token deltas, lifecycle events |
| `GET /api/jobs` | List scheduled jobs |
| `POST /api/jobs` | Create scheduled job (same shape as `hermes cron`) |
| `GET/PATCH/DELETE /api/jobs/{job_id}` | CRUD на job |
| `POST /api/jobs/{job_id}/pause` | Pause job |
| `POST /api/jobs/{job_id}/resume` | Resume job |
| `POST /api/jobs/{job_id}/run` | Trigger immediate run |

## Auth

- Bearer token: `Authorization: Bearer ***` (key = `API_SERVER_KEY`)
- CORS **выключен по умолчанию**
- Для браузерного доступа: `API_SERVER_CORS_ORIGINS=http://localhost:3000,...`
- Preflight кэшируется 10 минут
- Привязка к `0.0.0.0` — `API_SERVER_KEY` **обязателен**

## Multi-User / Profiles

Изолированные инстансы на разных портах:
```bash
hermes profile create alice
hermes -p alice config set API_SERVER_ENABLED true
hermes -p alice config set API_SERVER_PORT 8643
hermes -p alice config set API_SERVER_KEY alice-secret
hermes -p alice gateway &
# → http://localhost:8643/v1/models → model "alice"
```

## Inline Images

✅ Поддерживаются на `/v1/chat/completions` и `/v1/responses`
❌ Uploaded files (`file`, `input_file`, `file_id`) — **NOT supported** → 400

## Streaming

- `/v1/chat/completions` → SSE + `hermes.tool_progress` event для UI прогресса
- `/v1/responses` → spec-native `function_call` / `function_call_output` output items

## Multi-turn (Responses API)

```json
{"input": "Hello", "conversation": "my-project"}
{"input": "What's in src/?", "conversation": "my-project"}
{"input": "Run the tests", "conversation": "my-project"}
```
Автоматически цепляет к последнему response в conversation.

Или `previous_response_id`:
```json
{"input": "Now show me the README", "previous_response_id": "resp_abc123"}
```

## Env Vars

| Variable | Default | Description |
|---|---|---|
| `API_SERVER_ENABLED` | false | Enable |
| `API_SERVER_PORT` | 8642 | Port |
| `API_SERVER_HOST` | 127.0.0.1 | Bind address |
| `API_SERVER_KEY` | none | Bearer token |
| `API_SERVER_CORS_ORIGINS` | none | Comma-separated allowed origins |
| `API_SERVER_MODEL_NAME` | profile name | Model name on `/v1/models` |

## Security

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Idempotency-Key` header → 5-min response cache deduplication

## Limitations

- Max **100 stored responses** (LRU eviction)
- No file upload (только inline images)
- Model field — cosmetic only, actual model in server config

## Compatible Frontends

Open WebUI (126k⭐), LobeChat (73k), LibreChat (34k), AnythingLLM (56k), NextChat (87k), ChatBox (39k), Jan (26k), HF Chat-UI (8k), big-AGI (7k)

## Proxy Mode

`GATEWAY_PROXY_URL` → forward к этому API server вместо локального агента. Для split deployments (e.g. Docker Matrix E2EE → host agent).
