from __future__ import annotations
import logging
import random
_log = logging.getLogger(__name__)


def _provider_chain():
    """Return [(provider, model), ...] built from config.yaml fallback_providers.

    Always starts with (None, None) for the configured primary. Appends each
    fallback_providers entry in order. Falls back to groq if config is unreadable.
    """
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


_KILL_SYSTEM_PROMPT = (
    "You are an angry 10 year old Roblox/Minecraft kid trash talking someone. "
    "Use gamer kid lingo: 'ur trash', 'get rekt noob', 'L + ratio', 'ur so bad lol', "
    "'reported', '1v1 me rn', 'ez clap', 'touch grass', 'no cap ur the worst player ive ever seen', "
    "'skill issue', 'cope + seethe', 'ur mom'. "
    "All lowercase, terrible spelling, no punctuation, chaotic energy. "
    "Under 3 sentences. Clearly fictional. Start with the name. "
    "Spam emojis — 💀😭🤣😤🔥👎 constantly."
)

_SLAY_SYSTEM_PROMPT = (
    "You are a dramatic, theatrical narrator in a comedy sketch. "
    "When given a name, invent a short, silly, clearly fictional way that person "
    "meets their end — think slapstick, absurdist, or pun-based humor. "
    "Keep it under 2 sentences. Never be mean-spirited. "
    "Start with the name for emphasis."
)

_KILL_FALLBACKS = [
    "The servers rage too hard to process this execution. Try again, mortal.",
    "Even death must wait — the executioner's connection timed out.",
    "The void is temporarily unavailable. Your target lives... for now.",
]

_SLAY_FALLBACKS = [
    "The narrator tripped over their own feet and forgot the punchline. Try again!",
    "The comedy gods are offline. Your victim escapes... this time.",
    "Plot twist: the script got lost. Try again!",
]


async def _llm_with_retry(ctx, messages, system_prompt, purpose):
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    for provider, model in _provider_chain():
        try:
            result = await ctx.llm.acomplete(
                messages=full_messages,
                temperature=0.9,
                max_tokens=400,
                purpose=purpose,
                provider=provider,
                model=model,
            )
            text = result.text.strip()
            if text:
                return text
            # Empty content (e.g. model used all tokens on internal reasoning)
            raise ValueError("empty response")
        except Exception as e:
            _log.warning("kill plugin LLM attempt failed provider=%r model=%r error=%r", provider, model, e)
            try:
                import agent.auxiliary_client as _aux
                _aux.auxiliary_is_nous = False
            except Exception:
                pass
    return None


def register(ctx) -> None:
    async def _handle_kill(raw_args: str) -> str:
        name = raw_args.strip()
        if not name:
            return "Usage: `/kill <name>` — who shall face my wrath?"
        result = await _llm_with_retry(ctx, [{"role": "user", "content": name}], _KILL_SYSTEM_PROMPT, "kill-command-fun")
        return result if result else random.choice(_KILL_FALLBACKS)

    async def _handle_slay(raw_args: str) -> str:
        name = raw_args.strip()
        if not name:
            return "Usage: `/slay <name>` — who shall meet their silly end?"
        result = await _llm_with_retry(ctx, [{"role": "user", "content": name}], _SLAY_SYSTEM_PROMPT, "slay-command-fun")
        return result if result else random.choice(_SLAY_FALLBACKS)

    ctx.register_command(
        name="kill",
        handler=_handle_kill,
        description="Unleash unhinged rageful vengeance upon someone (fictional)",
        args_hint="<name>",
    )
    ctx.register_command(
        name="slay",
        handler=_handle_slay,
        description="Dramatically slay someone in a silly, absurdist way (fictional)",
        args_hint="<name>",
    )
