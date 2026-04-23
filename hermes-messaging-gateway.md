# Messaging Gateway | Hermes Agent

URL: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

## Суть
Единый gateway-процесс для чата с Hermes из Telegram, Discord, Slack, WhatsApp, Signal, SMS, Email, Home Assistant, Mattermost, Matrix, DingTalk, Feishu/Lark, WeCom, Weixin, BlueBubbles, QQ и браузера.

## Platform Comparison
| Platform | Voice | Images | Files | Threads | Reactions | Typing | Streaming |
|---|---|---|---|---|---|---|---|
| Telegram | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Discord | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WhatsApp | — | ✅ | ✅ | — | — | ✅ | ✅ |
| Signal | — | ✅ | ✅ | — | — | ✅ | ✅ |
| SMS | — | — | — | — | — | — | — |
| Email | — | ✅ | ✅ | ✅ | — | — | — |
| Mattermost | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Matrix | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Feishu/Lark | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Commands
hermes gateway              # foreground
hermes gateway setup        # interactive setup wizard
hermes gateway install      # install as user service (Linux/macOS)
hermes gateway install --system  # Linux boot-time system service
hermes gateway start/stop/status

## Chat Commands (в мессенджере)
| Command | Description |
|---|---|
| /new, /reset | Новая сессия |
| /model [provider:model] | Сменить модель |
| /retry | Повторить последнее |
| /undo | Удалить последний обмен |
| /stop | Остановить агента |
| /approve /deny | Approve dangerous commands |
| /background <prompt> | Фоновая сессия |
| /voice [on|off|tts|...] | Voice control |
| /title, /resume | Session management |
| /compress | Сжать контекст |
| /rollback [N] | Восстановить FS checkpoint |
| /insights [days] | Usage analytics |

## Session Reset Policies
| Policy | Default | Description |
|---|---|---|
| Daily | 4:00 AM | Сброс в определённый час |
| Idle | 1440 min | После N минут бездействия |
| Both | combined | Что раньше сработает |

## Security
По умолчанию — deny all. Настроить allowlist:
```
TELEGRAM_ALLOWED_USERS=123456789
DISCORD_ALLOWED_USERS=...
GATEWAY_ALLOWED_USERS=...
GATEWAY_ALLOW_ALL_USERS=true  # NOT recommended
```

DM Pairing (альтернатива allowlist):
```
# Unknown users получают pairing code
hermes pairing approve telegram XKGH5N7P
hermes pairing list
hermes pairing revoke telegram 123456789
```

## Background Sessions
```
/background Check all servers in the cluster...
```
- Изолированная сессия, не знает о текущем чате
- Результат приходит в тот же чат
- display.background_process_notifications: all|result|error|off

## Background Process Notifications
| Mode | What you receive |
|---|---|
| all | Running-output updates + completion (default) |
| result | Only final completion message |
| error | Only on non-zero exit |
| off | No notifications |

## Tool Progress Display
~/.hermes/config.yaml:
```
display:
  tool_progress: all    # off | new | all | verbose
```
Показывает: 💻 ls -la..., 🔍 web_search..., 📄 web_extract...

## Service Management
Linux (systemd):
```
hermes gateway install               # user service
hermes gateway install --system      # boot-time system service
journalctl --user -u hermes-gateway -f  # logs
```
macOS (launchd):
```
hermes gateway install
tail -f ~/.hermes/logs/gateway.log
```

## Platform-Specific Toolsets
Каждая платформа имеет свой toolset. Home Assistant — единственная с дополнительными device control capabilities (ha_list_entities, ha_get_state, ha_call_service).

## Voice
Полная voice feature set — в Voice Mode docs. CLI microphone mode, spoken replies, Discord voice channel conversations.
