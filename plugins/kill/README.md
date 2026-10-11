# kill plugin

Adds `/kill <name>` and `/slay <name>` fun commands to Hermes.

## Commands

| Command | Tone |
|---------|------|
| `/kill <name>` | Angry 10-year-old Roblox/Minecraft kid. Lowercase, chaotic emojis, "L + ratio", "skill issue", "reported". |
| `/slay <name>` | Dramatic theatrical narrator. Absurdist, slapstick, overwrought. |

## How it works

1. **Primary:** calls `ctx.llm.acomplete()` with auto-detected provider (inherits the main agent model).
2. **Fallback:** Groq `llama-3.3-70b-versatile` if the primary attempt returns empty or errors.
3. **Static fallback:** one of `_KILL_FALLBACKS` / `_SLAY_FALLBACKS` if both LLM attempts fail.

## Known constraints

- **`max_tokens` must be ≥ 400.** GLM-4.5-Air (current primary) uses internal chain-of-thought
  tokens before producing visible output; lower limits cause `finish_reason: length` with
  `content: None`. See Bug 13 in FIXES.md.
- **`auxiliary_is_nous` global reset.** The exception handler resets
  `agent.auxiliary_client.auxiliary_is_nous = False` to prevent nous-specific `tags` from
  leaking into the Groq fallback request (HTTP 400). Framework-level bug workaround — see
  Bug 3 in FIXES.md.
- **Groq must be a custom provider.** It is not in Hermes's built-in `PROVIDER_REGISTRY`.
  Configure it via `providers:` in `.hermes/config.yaml` — see below.

## Required `.hermes/config.yaml` entries

```yaml
providers:
  groq:
    api: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
    default_model: llama-3.3-70b-versatile

plugins:
  entries:
    kill:
      llm:
        allow_provider_override: true
        allow_model_override: true
```

`GROQ_API_KEY` must be set in `.hermes/.env`.
