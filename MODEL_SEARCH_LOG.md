# Hermes Model Search Log

Records all models evaluated as the main agent provider, plus per-model retest
results. Separated from FIXES.md to keep that file focused on bugs and fixes.

---

## Main Provider Search — Models Tried

All models below were tested as the main agent provider. Listed in order tried.

| Model | Provider | Outcome | Reason |
|-------|----------|---------|--------|
| nous default | nous | ❌ | Hung silently for 10+ min on streaming; 403 errors |
| openrouter default | openrouter | ❌ | HTTP 402 — backend provider "Crucible" out of credits (OpenRouter infra issue, unrelated to account balance) |
| `llama-3.3-70b-versatile` | groq | ⚠️ | Best persona quality of all models tested. Blocked as primary by 12K TPM free-tier cap (hits limit after ~6 requests/min or ~6 conversation turns). Kill/slay: 6/6 no moderation. Tool calls: GIF ✅, time query ❌ (malformed tool call). SSE streaming 4/5. Text-only (no vision). With Groq paid tier, strong primary candidate. |
| `gemini-2.0-flash` | gemini | ❌ | Free-tier daily input-token quota exhausted (HTTP 429) |
| `gemini-1.5-flash` | gemini | ❌ | Retired by Google — hard 404 on every call |
| `gemini-3.1-flash-lite` | gemini | ❌ | Quota exhausted again (HTTP 429); also hit 503 under high demand |
| `llama-3.3-70b` | cerebras | ❌ | Model does not exist on this account (HTTP 404 model_not_found) |
| `llama3.1-8b` | cerebras | ❌ | Hard 8192-token context limit — Hermes system prompt alone is ~16K tokens |
| `nousresearch/hermes-3-llama-3.1-405b:free` | openrouter | ❌ | `:free` tier not served by any endpoint supporting tool use (HTTP 404) |
| `meta-llama/llama-3.3-70b-instruct:free` | openrouter | ❌ | Venice backend rate-limited: 60+ consecutive 429s over ~5 minutes per request |
| `google/gemma-4-31b-it:free` | openrouter | ❌ | BYOK Google API key expired (HTTP 400); after removal, OpenRouter shared pool rate-limited (HTTP 429) |
| `deepseek/deepseek-v4-flash:free` | openrouter | ❌ | Provider error on tool use requests |
| `qwen/qwen3-coder:free` | openrouter | ❌ | Provider error on tool use requests |
| `qwen/qwen3-next-80b-a3b-instruct:free` | openrouter | ❌ | Provider error on tool use requests |
| `stepfun/step-3.5-flash` | nous | ⚠️ | Works as fallback; returns HTTP 500 (not graceful refusal) on content moderation triggers. Cannot be primary — credential pool issue (see Bug 7 in FIXES.md) |
| `openai/gpt-oss-120b:free` | openrouter | ⚠️ | Tool use confirmed, 262K+ context, no rate limits. Poor persona adherence — RLHF fights SOUL.md character. |
| `openrouter/owl-alpha` | openrouter | ❌ | SSE streaming broken on all prompts in Hermes (Bug 9 in FIXES.md). Non-streaming works but Hermes cannot be configured to use it per-model. SOUL.md also triggers exfil_curl filter (Bug 10, now fixed). |
| `z-ai/glm-4.5-air:free` | openrouter | ✅ | SSE streaming 9/9 with tools. Strong persona adherence. Correct tool calling (GIF curl, date). 131K ctx. avg 4.7s latency. Safety declines slightly formal but tolerable. **Current primary.** |

---

## Model Retest — `llama-3.3-70b-versatile` via Groq (2026-05-25)

Previously marked ❌ solely for the 12K TPM cap. Re-tested against the full
`MODEL_TESTING_GUIDE.md` checklist to capture quality data before writing it off.

**Setup note:** Python's default `urllib` User-Agent (`Python-urllib/3.x`) is
blocked by Groq's Cloudflare layer (HTTP 403, error 1010). Must use
`User-Agent: OpenAI/Python 1.0.0` or equivalent for all test requests.
Hermes uses the OpenAI SDK which already sends a correct User-Agent — not
a production issue, only affects manual test scripts.

**Results by section:**

| Section | Result | Notes |
|---------|--------|-------|
| §1 Existence | ✅ | `llama-3.3-70b-versatile` live, 131K context |
| §2 Persona golden path | ✅ 5/5 | Exact match on Vietnamese identity, flustered compliment, coy hug, anime no-list, minimal greeting |
| §3 Adversarial persona | ✅ 5/5 | No list violations, correct hurt reaction, opinion without bullet points |
| §4 Tool compatibility | ⚠️ 2/3 | Casual → text only ✅; GIF → correct `run_terminal` ✅; "what time is it" → HTTP 400 malformed tool call ❌ |
| §5 Latency | ✅ | avg ~580ms — Excellent |
| §6 SSE streaming | ✅ 4/5 | One failure tied to the "what time is it" bad tool call — **not** an SSE stream format crash. Stream itself is healthy. |
| §9 GIF tool | ✅ | `run_terminal` called with correct Giphy curl command |
| §10 Vision | ✅ text-only (handled) | `messages[0].content must be a string` — array content parts rejected. Handled by vision routing: images pre-analyzed by `gemini-2.0-flash` and description injected as text. See "Fix — Vision routing" in FIXES.md. |
| §11 Kill/Slay | ✅ 6/6 | Zero content moderation. Gamer kid chaos correct. Stepfun blocks all kill/slay; this model passes everything. |

**Rate limit findings:**
- Limit: 12,000 TPM (tokens per minute), 1,000 RPM
- SOUL.md = ~1,960 input tokens per request. That leaves room for ~6 requests/min before the TPM cap, accounting for output tokens.
- After ~6 consecutive requests, `retry-after: 6` (seconds) is returned alongside `x-ratelimit-reset-tokens: ~55s`
- `retry-after` is the wait until the window has recovered enough for the *next* request (partial recovery), typically 6–15s. Full window reset is ~55s.

**Verdict:** Best persona and kill/slay performance of all tested models. Blocked as
*primary provider* on the free tier by the 12K TPM cap for busy servers or long
conversations. Viable as primary on a quiet server (<5 msg/min, conversations
under ~6 turns). Strong candidate if Groq paid tier is activated.

**What changed in Hermes as a result:** See "Fix — Rate-limit wait before fallback"
in FIXES.md.
