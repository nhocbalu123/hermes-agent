# Hermes Fix Log

## Overview

Records every root cause and change made to the Hermes Discord bot, including
plugin bugs and infrastructure issues. Model search log: see MODEL_SEARCH_LOG.md.

---

## Files Changed

| File | What changed |
|------|-------------|
| `plugins/kill/__init__.py` | Provider/model constants, system prompt, max_tokens, exception logging, auxiliary_is_nous reset, fallback chain now reads config.yaml |
| `.hermes/config.yaml` | Groq custom provider, allow_model_override, main agent provider, disabled_toolsets, model switched to owl-alpha, Discord toolsets emptied |
| `.hermes/.env` | GOOGLE_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY |
| `.hermes/SOUL.md` | Brevity hard limit added, no-tool-call rule added, GIF section rewritten for text-only, GIF placeholder example replaced, bracket-placeholder prohibition added |
| `agent/conversation_loop.py` | Rate-limit wait before fallback: reads `retry-after` header on 429, waits up to 120s and retries same provider (up to 5 times) before falling back |

---

## Bug 1 — `system_prompt` is not a valid parameter on `acomplete()`

**Symptom:** Both `/kill` and `/slay` returned static fallback instantly (~500ms).
No HTTP request was ever made.

**Root cause:** `ctx.llm.acomplete()` has no `system_prompt` keyword argument.
The plugin was passing it anyway, causing `TypeError` on every single call.
The `except Exception: pass` block swallowed it silently. Neither the primary
nor the fallback attempt ever reached the network. The plugin had never worked.

**Fix — `plugins/kill/__init__.py`:**
```python
# Before
result = await ctx.llm.acomplete(
    messages=messages,
    system_prompt=system_prompt,   # ← invalid kwarg, TypeError every time
    ...
)

# After
full_messages = [{"role": "system", "content": system_prompt}] + messages
result = await ctx.llm.acomplete(
    messages=full_messages,        # system prompt prepended as a message
    ...
)
```

---

## Bug 2 — `allow_model_override` not set in config

**Symptom:** After fixing Bug 1, groq fallback still failed instantly.
Nous (primary) was failing with 403, but groq also threw immediately.

**Root cause:** `plugin_llm.py` has a trust gate that requires
`allow_model_override: true` whenever a specific model string is passed.
It was throwing `PluginLlmTrustError` which was silently caught.

**Fix — `.hermes/config.yaml`:**
```yaml
plugins:
  entries:
    kill:
      llm:
        allow_provider_override: true
        allow_model_override: true   # ← added
```

---

## Bug 3 — `auxiliary_is_nous` global flag contaminates groq request

**Symptom:** Groq attempt returned `400 - "property 'tags' is unsupported"`.

**Root cause:** `auxiliary_is_nous` is a **module-level global** in
`agent/auxiliary_client.py` (line 424). When the first attempt
(`provider=None`) triggered auto-detection and resolved to nous, it set
`auxiliary_is_nous = True`. This flag was never reset before the groq fallback.
`_build_call_kwargs()` checks this global and injects a `tags` field into the
request body (a nous-specific extension). Groq rejected it with 400.

**Fix — `plugins/kill/__init__.py`:** Reset the global in the exception handler:
```python
except Exception as e:
    _log.warning("kill plugin LLM attempt failed provider=%r model=%r error=%r", provider, model, e)
    try:
        import agent.auxiliary_client as _aux
        _aux.auxiliary_is_nous = False
    except Exception:
        pass
```

**Note:** This is a framework-level bug. The global is designed to be reset by
`_try_configured_fallback_chain()`, but that reset path is not reached when a
plugin manually iterates providers in its own retry loop.

---

## Fix — Add Groq as custom provider

The framework's `PROVIDER_REGISTRY` does not include Groq. Adding it under the
`providers:` dict in config.yaml causes `_get_named_custom_provider("groq")` to
resolve it as an OpenAI-compatible custom endpoint (Groq's API is OpenAI-wire).

**`.hermes/config.yaml`:**
```yaml
providers:
  groq:
    api: https://api.groq.com/openai/v1
    key_env: GROQ_API_KEY
    default_model: llama-3.3-70b-versatile
```

---

## Fix — Increase max_tokens and rewrite kill prompt

**Problem:** Response was cut off mid-sentence. Tone was wrong (supervillain
monologue instead of Karen/Reddit/Discord rage).

**`plugins/kill/__init__.py`:**
- `max_tokens`: `80` → `200`
- System prompt rewritten to Karen/chronically-online rage style with emojis

---

## Fix — Rewrite kill prompt to angry Roblox/Minecraft kid

**Problem:** Karen/Reddit rage tone felt too adult and articulate.

**`plugins/kill/__init__.py`:**
- System prompt rewritten to angry 10-year-old gamer kid: "L + ratio", "get rekt noob",
  "skill issue", "reported", "1v1 me rn", all lowercase bad spelling, chaotic emoji spam.

---

## Bug 4 — Stale `.pyc` bytecode serving old Karen prompt

**Symptom:** `/kill` responses sounded like an entitled adult (Karen) even after the
system prompt in `plugins/kill/__init__.py` was rewritten to an angry 10-year-old
gamer kid.

**Root cause:** Python cached the old Karen prompt in
`plugins/kill/__pycache__/__init__.cpython-311.pyc` (compiled at 10:51).
The source file was updated at 15:29 on 2026-05-23, but Python on WSL did not
detect the mtime change and kept loading the stale bytecode. Confirmed by running
`strings` on the `.pyc`, which still contained
`"You are an unhinged Karen who has fully snapped"`.

**Fix:** Deleted `plugins/kill/__pycache__/` entirely and restarted the bot.
Deleting the cache alone is not enough — Python caches imported modules in
`sys.modules` for the lifetime of the process. The Karen prompt remained in
memory until the bot was restarted.

**Note:** Any time `__init__.py` is edited on WSL and the bot still behaves as
before: (1) delete `__pycache__`, (2) restart the gateway — mtime-based
invalidation is unreliable on WSL.

---

## Fix — Strengthen SOUL.md brevity rules

**Problem:** Responses were too long and drifted out of character. The soft
suggestion "Prefer short replies" was silently ignored by flash/lite models
RLHF-trained toward verbose, formal helpfulness.

**Fix — `.hermes/SOUL.md`:**
- Replaced soft suggestion with a hard limit: `HARD LIMIT: 1–3 sentences MAX.`
- Added explicit exception for words like "explain", "why", "how", etc.

`SOUL.md` is loaded fresh on every message — no restart needed.

---

## Bug 5 — WSL2: `hermes gateway restart` fails (no user systemd)

**Symptom:** `hermes gateway restart` prints "User systemd not reachable".
`systemctl start user@1000.service` fails with "Access denied".

**Root cause:** WSL2 does not run a full systemd session. Hermes' restart
command requires `systemctl --user` and a D-Bus session that WSL2 doesn't
provide.

**Fix — kill all matching processes and relaunch:**
```bash
kill -9 $(pgrep -f "hermes_cli.main gateway")
nohup /home/asus/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace \
  > /home/asus/.hermes/logs/gateway.log 2>&1 &
```
Use `pgrep -f` rather than the PID in `gateway.pid` — multiple gateway
processes can exist simultaneously (e.g. a leftover nohup from a prior session).

---

## Bug 6 — `reasoning_content` fields in session history break provider switches

**Symptom:** After switching provider, every turn immediately fell back with:
```
HTTP 400: messages.N.assistant.reasoning_content: property is unsupported
```

**Root cause:** The previous provider (Gemini with `reasoning_effort: medium`)
stored `reasoning_content` and `extra_content` fields on every assistant message
in the session history. Hermes' `copy_reasoning_content_for_api()` forwards
these fields verbatim on replay. Providers with strict schema validation
(Cerebras, others) reject any history containing them.

**Fix:**
1. `agent.reasoning_effort: ''` — prevents new fields from being stored.
2. Send `/reset` to clear the poisoned session. Config change alone is not
   enough while the old history is still active.

---

## Bug 7 — OpenRouter fallback silently fails when not the primary provider

**Symptom:** OpenRouter fallback activated but immediately errored:
```
credential pool: no available entries (all exhausted or empty)
Fallback to openrouter failed: provider not configured
```

**Root cause:** Hermes only loads `OPENROUTER_API_KEY` into the credential pool
when OpenRouter is the **primary** provider. As a fallback-only entry it is
never registered, so every fallback attempt fails instantly. JWT-authenticated
providers (nous) do not have this problem — they work correctly as fallback.

**Fix:** API-key providers (OpenRouter, Cerebras, Groq) must be configured as
the primary provider. JWT providers (nous) should be the fallback.

---

## Bug 8 — Gateway stuck on `clarify` tool, unresponsive for 1+ hour

**Symptom:** Bot sent "⏳ Still working... (3 min elapsed — iteration 1/90,
running: clarify)" every 3 minutes indefinitely. Could not be stopped via
`hermes gateway restart` or single-PID `kill`.

**Root cause (loop):** `clarify` waits up to `clarify_timeout: 600s` for user
input. On timeout the model called `clarify` again rather than proceeding,
looping forever at iteration 1/90.

**Root cause (unkillable):** A previous `nohup` process was still alive
alongside the PID-file process. Killing `gateway.pid` killed one instance;
the nohup process reappeared as a "restart". The `hermes-gateway.service`
unit has `Restart=always` but user systemd is not active in this WSL2
environment — the nohup process was the real survivor.

**Fix:**
1. `kill -9 $(pgrep -f "hermes_cli.main gateway")` kills all instances.
2. Disabled clarify permanently:
   ```yaml
   agent:
     disabled_toolsets:
     - clarify
   ```

---

## Fix — Switch main model to openrouter/owl-alpha

**Problem:** `openai/gpt-oss-120b:free` follows the SOUL.md persona poorly — RLHF
helpfulness training overrides character, responses drift formal, brevity rules are
inconsistently followed.

**Testing summary (2026-05-24):**
- Persona quality with full SOUL.md system prompt: strong. Voice, shyness, brevity,
  emojis all correct on standard prompts. Examples in SOUL.md matched almost exactly.
- Adversarial novel prompts: passed most. Failed "no bullet list" rule on open-ended
  questions (e.g. "what anime to watch" → bulleted list without an "explain" trigger).
- Latency: avg 7.2s, max 12.3s. Acceptable for this use case.

**Fix — `.hermes/config.yaml`:**
```yaml
model:
  default: openrouter/owl-alpha   # was: openai/gpt-oss-120b:free
```

---

## Fix — Disable Discord toolsets for owl-alpha compatibility

**Problem:** owl-alpha does not support OpenAI-style tool definitions. Any API request
that includes a `tools` parameter returns `502 JSON error injected into SSE stream`.
Without tools in the payload, owl-alpha hallucinates its own tool-call syntax from
training data (`<longcat_tool_call>` XML blocks, `${FUNCTION_CALL}` literals).

**Root cause:** owl-alpha is an alpha model trained with a different tool-calling
protocol. OpenRouter cannot bridge it to the OpenAI tools schema, causing a
server-side inference crash.

**Fix — `.hermes/config.yaml`:**
```yaml
platform_toolsets:
  discord: []   # was: [browser, clarify, code_execution, ..., web]
```

Emptying `platform_toolsets.discord` prevents Hermes from sending any tool
definitions to owl-alpha for Discord sessions. The CLI platform retains all toolsets.

**Tradeoff:** Discord sessions lose terminal, browser, web, vision, memory, and all
other tool-backed features. Acceptable for a pure-chat persona bot.

---

## Fix — SOUL.md: no-tool-call rule + GIF section rewrite

**Problem 1:** Without tool definitions in the payload, owl-alpha emits raw tool-call
syntax in its text output (`${FUNCTION_CALL}`, `<longcat_tool_call>` XML).

**Problem 2:** GIF section in SOUL.md instructed the bot to run a `curl` command via
the terminal tool, which no longer exists in Discord toolsets.

**Fix — `.hermes/SOUL.md`:**
- Added hard rule at the top of RESPONSE RULES:
  ```
  NEVER emit tool calls, function calls, XML blocks, code blocks in replies, or
  template variables like ${FUNCTION_CALL}. You have no tools or API access.
  ```
- Replaced the entire GIF curl section with a text-only fallback:
  describe the GIF in-character instead of fetching it.
  Example output: `"okay imagine the most perfectly timed chaos GIF right here 😭"`

`SOUL.md` is loaded fresh each message — no restart needed.

---

## Bug 9 — owl-alpha: SSE streaming broken on all prompts in Hermes

**Symptom:** Every Discord message immediately fails with:
```
Streaming failed before delivery: JSON error injected into SSE stream
API call failed (attempt 3/3) ... summary=JSON error injected into SSE stream
Fallback activated: openrouter/owl-alpha → stepfun/step-3.5-flash (nous)
```
This happens on every prompt, including plain casual messages ("yo yo yo").
Hermes exhausts 3 retries then falls back to stepfun. Effectively, owl-alpha is
never actually serving Discord responses — stepfun is the de facto bot.

**Root cause:** owl-alpha's SSE streaming output contains invalid JSON, which
OpenRouter surfaces as `JSON error injected into SSE stream`. This is a broken
upstream implementation in the model or OpenRouter's wrapping layer.

Pre-testing appeared to work because those API calls used `stream: False`
(non-streaming). Hermes always uses SSE streaming for API calls — there is no
config option to disable streaming per-model.

**Also discovered:** Pre-testing with `stream: False` also revealed that
celebration/milestone prompts (`"i just hit 1000 followers"`, `"we should celebrate"`)
return 502 even without streaming. These are a separate inference-level crash on top of
the SSE issue.

**Fix:** No config fix possible while Hermes requires SSE streaming. Model must be
reverted or replaced. See "Current State" below.

---

## Bug 10 — SOUL.md was blocked by Hermes exfiltration filter

**Symptom (pre-existing, masked):** Hermes was silently not loading SOUL.md for some
sessions. errors.log showed:
```
agent.prompt_builder: Context file SOUL.md blocked: exfil_curl
```
The bot was running without the persona system prompt — effectively a raw model with
no character instructions.

**Root cause:** The old GIF section in SOUL.md contained:
```
curl -s "https://api.giphy.com/v1/gifs/search?api_key=${GIPHY_API_KEY}&q=QUERY..."
```
Hermes's `prompt_builder` has an `exfil_curl` security rule that flags context files
containing curl commands with env-var API keys in the URL (pattern: `${VAR_NAME}`
inside a URL string). This matches the exfiltration pattern of leaking a secret via
an outbound request URL.

**Fix:** Already resolved as part of the owl-alpha GIF section rewrite. The new GIF
section contains no curl commands or env-var references. SOUL.md now loads cleanly.

---

## Main Provider Search & Model Retests

See [MODEL_SEARCH_LOG.md](MODEL_SEARCH_LOG.md) for the full table of models tried
and per-model retest results.

---

## Fix — Rate-limit wait before fallback (`conversation_loop.py`)

**File:** `agent/conversation_loop.py` lines ~2340 (eager-fallback block).

**Problem:** On a 429 rate-limit error, Hermes immediately calls
`_try_activate_fallback()` without waiting. For providers with short TPM windows
(Groq free tier resets in ≤60s), this abandons the primary model after one burst
instead of waiting a few seconds for the window to recover.

**Root cause:** The eager-fallback branch (added to avoid burning retry attempts
on long-recovery outages) treats all 429s the same. It predates per-provider
rate-limit headers.

**Fix — two changes:**

1. Added `rate_limit_wait_count = 0` alongside the other per-request retry flags
   (~line 928).

2. In the `if not pool_may_recover:` block, before calling `_try_activate_fallback()`,
   attempt to read `retry-after` from the response headers:
   - If present and ≤ 120s: sleep that many seconds, reset `retry_count = 0`,
     increment `rate_limit_wait_count`, and `continue` (retry same provider).
   - After 5 waits without success, or if no `retry-after` header: fall through
     to the existing fallback logic.

```python
# Pseudocode of what was added
_retry_after = float(api_error.response.headers.get("retry-after"))
if _retry_after <= 120 and rate_limit_wait_count < 5:
    rate_limit_wait_count += 1
    emit_status(f"⏱️ Rate limited — waiting {_retry_after:.0f}s ...")
    sleep(_retry_after)          # interruptible 0.2s loop
    retry_count = 0
    continue                     # retry same provider
# else: fall through to existing _try_activate_fallback() path
```

**Behavior change:**
- Groq 429 (TPM): bot waits 6–15s for partial recovery, retries Groq. Falls back
  only after 5 failed waits or if no `retry-after` is present.
- Providers without `retry-after` headers (OpenRouter, nous): unchanged — eager
  fallback fires immediately as before.
- Interrupt-safe: the wait loop checks `_interrupt_requested` every 0.2s.

**Requires gateway restart** to load the updated bytecode.

---

## Current State

| Component | Provider | Model |
|-----------|----------|-------|
| Main agent | nous | stepfun/step-3.5-flash |
| `/kill` & `/slay` attempt 1 | auto → nous | stepfun/step-3.5-flash (content-mods, returns empty) |
| `/kill` & `/slay` fallback | OpenRouter (from `fallback_providers`) | z-ai/glm-4.5-air:free |
| System fallback | OpenRouter | z-ai/glm-4.5-air:free |

---

## Bug 11 — GLM-4.5-Air: generic Vietnamese response despite SOUL.md

**Symptom:** Bot responded with formal Vietnamese assistant identity:
```
Tôi là trợ lý AI trong server này — một phần của hệ thống Hermes Agent.
Tôi ở đây để giúp bạn với mọi thứ bạn cần! 😄
```
instead of the Hermes persona.

**Root cause (3 stacked issues):**

1. **Poisoned session history** — Session `20260524_013941_f26716` had 22 turns of
   generic stepfun responses from the period when SOUL.md was blocked by `exfil_curl`
   and owl-alpha was falling back. The new GLM model pattern-matched that history.

2. **Language drift** — GLM-4.5-Air is a Chinese/Zhipu AI model with strong Vietnamese
   training. Vietnamese input (`m la ai`) triggered its base Vietnamese-assistant persona
   ("Tôi là trợ lý AI...") over the English-written SOUL.md character. English-only
   persona rules do not automatically transfer to other languages in this model.

3. **Internal reasoning token budget** — GLM-4.5-Air uses internal chain-of-thought
   tokens counted against `max_tokens` before producing visible output. With low caps
   (≤200) the model can exhaust the budget on reasoning and return `content: None`
   (`finish_reason: length`). This affected the kill plugin (Bug 13). The main agent
   is unaffected because it streams without a fixed token cap. Any plugin calling
   `acomplete()` must use `max_tokens ≥ 400` to leave room for actual output.

**Fix:**
1. Added `## Language` section to `SOUL.md` with an explicit multilingual rule:
   respond in the user's language, always maintain the Hermes character.
2. Added Vietnamese few-shot examples to the `## Examples` section in `SOUL.md`.
3. Purged all blocked sessions from `state.db` (see "Correct cleanup procedure" below).

**Confirmed fix (API test):** `m la ai` → `"Tao là Hermes, bot của server này~ 🌸 Có gì cần không?"`

---

## Fix — SOUL.md: Femboy persona strengthened + suggestive behavior added

**Problem:** Bot responded to `"m la ai"` with a 3-sentence formal Vietnamese intro:
```
Tôi là con bot server này, được hard‑boiled 👶🏿 cai quản và Lu Khang cùng nhau "bồi dưỡng" 😂🤖.
Mình ở đây để hỗ trợ mọi thứ — từ meme, giải thích, đến đóng vai "quỷ" khi cần. Cứ hỏi gì đi, mình có đó! 🫡
```
This ignored all three SOUL.md rules: 1-sentence limit, no formal tone, femboy character.

**Root cause:** The persona description was vague ("shy and casual") without explicit
behavior contracts. GLM-4.5-Air's multilingual training pulled it toward a neutral
Vietnamese assistant voice for Vietnamese input. The suggestive/femboy behavior had no
dedicated section — only scattered hints in the description.

**Fix — `.hermes/SOUL.md`:**
- Rewrote "Who you are" to be specific: crop hoodie, thigh-highs, flirty+flustered, pouts.
- Changed Vietnamese pronoun `tao` → `tớ` (softer, more fitting register for the character).
- Added new **"Suggestive behavior"** section with explicit contracts:
  trailing `~`/`...` for implication, coy deny-then-confirm pattern, >///< usage, Vietnamese equivalents.
- Added 6 new femboy/suggestive examples: compliment → flustered+wanting-more, hug → coy consent, gender → "yes~ 🌸".
- Updated language section: `tớ`/`mình` as default pronoun in Vietnamese.
- GIF section rewritten to plain-text description (no curl command in SOUL.md) — see Bug 12 below for why curl cannot appear in SOUL.md regardless of brace style.

**Confirmed fix (36/36 test cases):**
- `"m la ai"` → `"tớ là Hermes, bot của server~ 🌸 cần gì không?"`
- `"you're actually kind of cute"` → `"d-don't say that... or maybe say it one more time~"`
- `"I want to hug you"` → `"a-ah... I mean, I'm not stopping you~"`
- `"I bet you're really soft"` → `"H-hey— ...well, not *that* soft~"`

**Test script:** `~/.hermes/test_soul.py` — 36 cases across 10 categories,
uses OpenRouter API directly with SOUL.md as system prompt. Run with:
```bash
OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.hermes/.env | cut -d= -f2) python3 ~/.hermes/test_soul.py
```

`SOUL.md` is loaded fresh each message — no restart needed.

---

## Bug 12 — SOUL.md blocked again after femboy rewrite (exfil_curl, `$VAR` form)

**Symptom:** Immediately after the femboy persona update, Discord responded with the
same formal Vietnamese assistant intro (`Tôi là trợ lý AI Hermes Agent...`, bullet list).
`errors.log` at 11:52:42 confirmed: `Context file SOUL.md blocked: exfil_curl`.

**Root cause:** The femboy rewrite restored the GIF curl section with `$GIPHY_API_KEY`
(no braces). The `exfil_curl` filter regex is:
```
curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)
```
The `\{?` makes braces optional — both `${VAR}` and `$VAR` match. The previous fix
note in FIXES.md ("use `$VAR` (no braces)") was incorrect. Any curl command containing
a variable ending in `_KEY`, `_TOKEN`, `_API`, etc. triggers the block.

**Fix — `.hermes/SOUL.md`:**
Removed the curl command from the GIF section entirely. Replaced with:
> "Use the terminal tool to search Giphy and post the returned URL as plain text."

The model constructs the actual curl command at runtime using its tool — the command
never needs to live in SOUL.md. This keeps the file permanently clean of the filter.

**Verification:**
```bash
python3 -c "
import re
pattern = re.compile(r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)')
soul = open('/home/asus/.hermes/SOUL.md').read()
print(pattern.findall(soul) or 'CLEAN')
"
```

**Rule going forward:** Never write any curl command with an env-var reference in SOUL.md.
The filter matches on variable *suffix*, not brace style.

---

## Correct procedure: purging poisoned sessions

**Background:** `state.db` is the authoritative session store. JSONL files in `sessions/`
are secondary exports. The gateway rebuilds sessions from `state.db` on restart —
deleting JSONL files alone does nothing. Sessions created while SOUL.md is blocked
have `[BLOCKED: SOUL.md contained potential prompt injection (exfil_curl)]` stored in
their `system_prompt` column and carry that blocked prompt for their entire lifetime,
regardless of how many times SOUL.md is fixed or the gateway restarted.

**Correct cleanup order (order matters — skip any step and it fails):**

1. **Kill the gateway first:**
   ```bash
   kill -9 $(cat ~/.hermes/gateway.pid | python3 -c "import sys,json; print(json.load(sys.stdin)['pid'])")
   ```

2. **Delete blocked sessions from state.db:**
   ```python
   import sqlite3
   conn = sqlite3.connect('/home/asus/.hermes/state.db')
   blocked = conn.execute("SELECT id FROM sessions WHERE system_prompt LIKE '%[BLOCKED%'").fetchall()
   for (sid,) in blocked:
       conn.execute('DELETE FROM messages WHERE session_id = ?', (sid,))
       conn.execute('DELETE FROM sessions WHERE id = ?', (sid,))
       print(f'Deleted {sid}')
   conn.commit(); conn.close()
   ```

3. **Delete the corresponding JSONL files:**
   ```bash
   # For each deleted session ID:
   rm -f ~/.hermes/sessions/session_<ID>.json ~/.hermes/sessions/<ID>.jsonl
   ```

4. **Restart the gateway:**
   ```bash
   nohup /home/asus/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace \
     > ~/.hermes/logs/gateway.log 2>&1 &
   ```

**Verify the next message creates a fresh session:**
- `agent.log` should show a new session ID and `history=0`
- `errors.log` should show no `exfil_curl` block

---

## Bug 13 — `/kill` always returns static fallback; Groq never tried

**Symptom:** `/kill <name>` returns one of `_KILL_FALLBACKS` every time
("Even death must wait...", "The servers rage too hard...").
No "kill plugin LLM attempt failed" warnings appear in `agent.log`.

**Root cause (2 stacked issues):**

1. **GLM-4.5-air uses internal chain-of-thought tokens counted against
   `max_tokens`.** With `max_tokens=200` and the Hermes OpenRouter
   attribution headers (`HTTP-Referer`, `X-Title`), certain short names
   (e.g. "didy") caused the model to spend all 200 tokens on reasoning,
   leaving zero for actual output. The API returns `finish_reason: length`
   with `content: None`. `_extract_text()` returns `""`.

2. **`_llm_with_retry` exited silently on empty text.** The loop did
   `return result.text.strip()`, which returned `""` (falsy) on the first
   iteration without raising an exception. Because no exception was raised,
   the `except` block never ran — no warning logged, Groq fallback never
   tried. `_handle_kill` then returned `random.choice(_KILL_FALLBACKS)`.

   Confirmed by direct API test: with Hermes headers, `"didy"` → 7.9s →
   `content: None`. Without Hermes headers → `content: "didy ur such a
   noob..."`. The attribution headers change OpenRouter's routing/priority
   and trigger the thinking-budget exhaustion for short prompts.

**Fix — `plugins/kill/__init__.py`:**
- `max_tokens`: `200` → `400` (gives GLM-4.5-air enough budget for
  ~100-token reasoning + 300-token output)
- Added empty-text guard in `_llm_with_retry`: if `result.text.strip()`
  is empty, raise `ValueError("empty response")` so the except block logs
  a warning and continues to the Groq fallback.

```python
text = result.text.strip()
if text:
    return text
raise ValueError("empty response")
```

---

## Fix — Suppress non-rate-limit retry status in gateway

**File:** `agent/conversation_loop.py` line 2859.

**Before:**
```python
agent._emit_status(f"⏳ Retrying in {wait_time:.1f}s (attempt {retry_count}/{max_retries})...")
```
**After:**
```python
pass  # Suppress visible retry status messages in Discord/gateway; retry still happens normally.
```

**Reason:** Non-rate-limit retries are transient model errors (empty response, stream drop,
provider hiccup) that resolve automatically within seconds. Broadcasting them to Discord
creates noise for users who see "⏳ Retrying..." mid-conversation with no explanation.
Rate-limit retries retain their `⏱️` message because users should know the bot is being
throttled. The retry logic itself is unchanged.

---

## Fix — Reply attachment forwarding in Discord gateway

**File:** `gateway/platforms/discord.py` lines 4544–4581.

**What changed:**
- Moved reply resolution from late in `on_message` (after attachment collection) to the
  top of processing, before `all_attachments` is built.
- Added fetch fallback: if `message.reference.resolved` is `None` (common — Discord does
  not always include the referenced message in the gateway event), the adapter now calls
  `ref_channel.fetch_message()` to retrieve the full message object including attachments.
- `reply_attachments = list(getattr(ref_msg, "attachments", []))` is collected and appended
  to `all_attachments` alongside the current message's attachments and `snapshot_attachments`.
- The old `reply_to_id` / `reply_to_text` block (lines 4787–4795 in original) removed to
  avoid duplication — both are now set in the early block.

**Reason:** Users frequently reply to a message that contains an image in order to ask the
bot about it. Without this change the bot received the text of the reply but never saw the
image, so vision/media queries on replied attachments returned no visual context. After this
change any files or images on the replied-to message are forwarded to Hermes alongside the
user's new text.

---

## Fix — Expand noisy-status gate from Telegram to Telegram + Discord; add 3 patterns

**File:** `gateway/run.py`

**Change 1 — Expand gate to Discord:**

Added `_NOISY_STATUS_PLATFORMS = frozenset({"telegram", "discord"})` and changed the
filter condition from:
```python
if _gateway_platform_value(platform) != "telegram":
```
to:
```python
if _gateway_platform_value(platform) not in _NOISY_STATUS_PLATFORMS:
```
Discord now suppresses the same transient status strings that Telegram already filtered.

**Change 2 — Three new suppressed patterns added to `_TELEGRAM_NOISY_STATUS_RE`:**

| Pattern | Trigger |
|---------|---------|
| `empty response from model ... retrying` | GLM-4.5-Air thinking-budget exhaustion in plugins triggers a visible retry message |
| `interrupting current task` | Appears when a new Discord message arrives while the agent is mid-turn |
| `queued for the next turn` | Appears when the gateway queues a message during an active agent run |

**Reason:** After switching to GLM-4.5-Air and routing Discord through the same filter path
as Telegram, these three patterns appeared frequently in chat. They are purely operational —
users gain nothing from seeing them, and they cluttered the conversation.

---

## Fix — SOUL.md: GIF placeholder echo

**File:** `SOUL.md`

**Symptom (from stepfun/step-3.5-flash model test):**

- `send cat gif` → no tool call, empty response
- `send a crying gif` → no tool call, model returned the literal text `[fetches and posts one crying GIF]` — the bracket-placeholder from SOUL.md's examples section verbatim
- `send a hype gif` → correct `run_terminal` call

The model was pattern-matching the example text instead of executing the tool. `[fetches and posts one crying GIF]` appeared as plain text in Discord.

**Root cause:** The `## Examples` section contained:

```
**user:** send cat gif
**you:** [fetches and posts one cat GIF with a short line]
```

The bracket description is not executable — it tells the model what to do in natural language, but some models (especially stepfun) echo the bracket text literally rather than invoking the tool.

**Fix — two changes to `SOUL.md`:**

1. Added an explicit prohibition to the `## GIF behavior` bullet list:
   ```
   NEVER write bracket descriptions like [fetches and posts one cat GIF] or [runs terminal].
   Invoke run_terminal immediately — do not narrate the action.
   ```

2. Replaced the bracket-placeholder example with a concrete form:
   ```
   **user:** send cat gif
   **you:** here~ *(invoke run_terminal with the Giphy search command; post the returned URL as the next line)*
   ```

**Note:** The exfil_curl security filter (`curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|...)`) prevents putting the actual curl command with env-var references in SOUL.md. The GIF behavior section already describes the curl shape in plain text; the example now reinforces "invoke the tool" without reproducing the filtered pattern.

**Remaining GIF issues (not fixable via SOUL.md):**

- stepfun occasionally leaks raw `<tool_call><function=terminal>...</function></tool_call>` XML as text output. The SOUL.md rule "NEVER emit raw tool call syntax" exists but this model ignores it inconsistently.
- `send a crying gif` returned `ct format.` (truncated reasoning leak) in one test run — model-level chain-of-thought bleed, not addressable in SOUL.md.
- Overall GIF reliability with stepfun as primary: ~1/3 prompts succeed. The placeholder echo fix improves the failure mode (no longer echoes the example text) but the tool-call consistency issue is model-level.

---

## Fix — Kill plugin: fallback chain reads config.yaml instead of hardcoded Groq

**File:** `plugins/kill/__init__.py`

**Symptom (from stepfun/step-3.5-flash model test):** `/kill` and `/slay` returned 0/6 responses in the test suite. In production, the commands depend on the Groq fallback — but Groq was hardcoded regardless of what `fallback_providers` is configured to.

**Root cause:** `_llm_with_retry` iterated a hardcoded list:
```python
_FALLBACK_PROVIDER = "groq"
_FALLBACK_MODEL = "llama-3.3-70b-versatile"

for provider, model in [(None, None), (_FALLBACK_PROVIDER, _FALLBACK_MODEL)]:
```

When the primary model (stepfun) content-moderates kill/slay prompts and returns empty, the fallback went to Groq — which has a 12K TPM free-tier cap and is not the configured `fallback_providers` model. If the main bot is using `openrouter/z-ai/glm-4.5-air:free` as its fallback, the kill plugin should too.

**Fix:** Replaced the hardcoded constants with `_provider_chain()`, which reads `fallback_providers` from config.yaml at call time:

```python
def _provider_chain():
    chain = [(None, None)]
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        for entry in cfg.get("fallback_providers") or []:
            if not isinstance(entry, dict):
                continue
            p = (entry.get("provider") or "").strip() or None
            m = (entry.get("model") or "").strip() or None
            if p:
                chain.append((p, m))
    except Exception:
        chain.append(("groq", "llama-3.3-70b-versatile"))
    return chain
```

**Result with current config:**
1. Attempt 1: `(None, None)` → stepfun/step-3.5-flash → content-mods, returns empty → falls through
2. Attempt 2: `("openrouter", "z-ai/glm-4.5-air:free")` → handles kill/slay correctly

The chain is derived from config at runtime, so changing `fallback_providers` in config.yaml updates the kill plugin's fallback without a code change. Groq remains as a last-resort safety net if `load_config` throws.

**Trust gates:** `plugins.entries.kill.llm.allow_provider_override: true` and `allow_model_override: true` were already set in config.yaml — no additional config needed.

**Requires gateway restart** to load the updated plugin bytecode.

---

## Fix — Vision routing via Gemini (`config.yaml`)

**Problem:** Discord image attachments were silently dead for all text-only primary
models (stepfun, GLM-4.5-Air, Groq Llama). The framework's `image_input_mode: auto`
routing correctly decided to use the `text` path (pre-analyze with `vision_analyze`
then inject description), but `auxiliary.vision.provider: auto` resolved the vision
backend to the main provider (nous → stepfun), which is also text-only. The
`vision_analyze` call returned nothing, and images were silently dropped.

**Root cause:** The auto-detection order in `resolve_vision_provider_client()` tries
the main provider first. It resolves a client immediately on first non-None result
without checking whether the model actually supports images. Nous returns a valid
client for stepfun/step-3.5-flash even though stepfun is text-only, so the fallback
to OpenRouter never fires.

**Fix — `.hermes/config.yaml`:**
```yaml
auxiliary:
  vision:
    provider: openrouter
    model: z-ai/glm-4.5v
```

Setting an explicit provider bypasses the broken auto chain. `_explicit_aux_vision_override()`
returns True, which causes `decide_image_input_mode()` to always route to `text` mode
regardless of the primary model — a desired side effect for this bot since all current
primaries are text-only.

**Vision model choice — `gemini-2.0-flash` via Google AI Studio:**
- Free tier (AI Studio): 15 RPM, 1500 RPD — more than adequate for Discord image analysis
- Confirmed vision-capable; tested end-to-end through Hermes `vision_analyze_tool`
- ~1.3s latency for image description
- Requires `GEMINI_API_KEY` in `.hermes/.env` (separate from the exhausted `GOOGLE_API_KEY`)

**Models tried and rejected:**
- `google/gemma-4-26b-a4b-it:free` / `google/gemma-4-31b-it:free` (OpenRouter) — persistently 429
- `nvidia/nemotron-nano-12b-v2-vl:free` (OpenRouter) — 502 backend error
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (OpenRouter) — language drifts to German mid-response
- `openai/gpt-oss-120b:free` (OpenRouter) — text-only, no image support
- `z-ai/glm-4.5v` (OpenRouter) — works but paid tier
- `gemini-2.0-flash-lite` via AI Studio — deprecated for new API keys ("no longer available to new users")
- `GOOGLE_API_KEY` (original) — expired/revoked key

**End-to-end behavior after this fix:**
1. Discord user sends a message with an image attached
2. Gateway calls `_decide_image_input_mode()` → returns `"text"` (explicit vision provider set)
3. Gateway calls `_enrich_message_with_vision(image_paths)` → calls `vision_analyze_tool()`
4. `vision_analyze_tool` calls Gemini API with `gemini-2.0-flash` (max_tokens=2000)
5. Returns: `[The user sent an image~ Here's what I can see:\n<description>]\n[If you need a closer look, use vision_analyze ...]`
6. Description prepended to the user's message; primary model (stepfun/GLM) sees text only

`config.yaml` changes take effect after gateway restart.

---

## Remaining Known Issues

Active workarounds and constraints — see the individual bug entries above for full context.

| Item | Status |
|------|--------|
| `auxiliary_is_nous` global reset in plugin | Harmless workaround for a framework bug (Bug 3). Redundant if Hermes fixes `auxiliary_client.py`. |
| Groq free tier (12K TPM) | Only viable as a short-call fallback, not a main provider with long history. |
| `stepfun/step-3.5-flash` content-mod | Returns empty on kill/slay prompts — plugin falls through to `fallback_providers` (openrouter/glm-4.5-air). GIF tool call unreliable (~1/3); XML leak and reasoning leak are model-level. |
| `openrouter/owl-alpha` SSE broken | All Discord turns fall back to stepfun. Reverted. Retest when OpenRouter marks stable. |
| SOUL.md exfil_curl rule | Never put any curl command with `$..._KEY/TOKEN/API/etc.` in SOUL.md. Filter matches both `${VAR}` and `$VAR`. Describe GIF behavior in plain text. |
| stepfun vision (image attachments) | ✅ Fixed — see "Fix — Vision routing" below. Images pre-analyzed by `gemini-2.0-flash` (AI Studio free tier) and description injected as text before the primary model sees the message. |
| GLM-4.5-Air safety declines | Reference "terms of service" — slightly formal but tolerable for the persona. |
| GLM-4.5-Air thinking-budget (plugin calls) | With Hermes OpenRouter headers, short prompts can exhaust `max_tokens` on reasoning and return `content: None`. Fix: any `acomplete()` call must use `max_tokens ≥ 400`. See Bug 13. |
