# API Server | Hermes Agent

URL: https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server

## Суть
Hermes Agent как OpenAI-совместимый HTTP-сервер. Любой frontend (Open WebUI, LobeChat, LibreChat, NextChat, ChatBox и др.) подключается как к OpenAI.

## Быстрый старт
1. ~/.hermes/.env:
   API_SERVER_ENABLED=true
   API_SERVER_KEY=change-me-local-dev
2. Запуск: hermes gateway → слушает http://127.0.0.1:8642
3. Клиент: http://localhost:8642/v1

## Endpoints
- POST /v1/chat/completions — OpenAI Chat Completions, stateless (full conversation in messages array)
- POST /v1/responses — OpenAI Responses API, stateful (server stores history via previous_response_id)
  - previous_response_id для multi-turn
  - conversation=... параметр для named conversations
- GET /v1/responses/{id} — получить сохранённый response
- DELETE /v1/responses/{id} — удалить
- GET /v1/models — discovery для frontends
- GET /health + GET /health/detailed
- POST /v1/runs + GET /v1/runs/{id}/events — streaming-friendly runs API
- GET/POST/PATCH/DELETE /api/jobs + pause/resume/run — Jobs API для cron jobs

## Streaming
- Chat Completions: hermes.tool_progress event для UX прогресса инструментов
- Responses: spec-native function_call/function_call_output items в SSE

## Auth
Bearer token: Authorization: Bearer *** через API_SERVER_KEY
CORS: API_SERVER_CORS_ORIGINS=http://localhost:3000 (по умолчанию выключен)

## Env vars
| Variable | Default |
|---|---|
| API_SERVER_ENABLED | false |
| API_SERVER_PORT | 8642 |
| API_SERVER_HOST | 127.0.0.1 |
| API_SERVER_KEY | none |
| API_SERVER_CORS_ORIGINS | none |
| API_SERVER_MODEL_NAME | profile name |

## Multi-user
hermes profile create alice → hermes -p alice config set API_SERVER_PORT 8643
Каждый profile = изолированный Hermes с отдельным memory/skills.

## Limitations
- Max 100 stored responses (LRU eviction)
- No file upload (inline images only) — uploaded files return 400
- config.yaml пока не поддерживается

## Compatible frontends
Open WebUI (126k★), LobeChat (73k), LibreChat (34k), AnythingLLM (56k), NextChat (87k), ChatBox (39k), Jan, HF Chat-UI, big-AGI
