"""Host detection shared by initiative state and the phase router."""

import os


def detect_host(env=None) -> dict:
    """Who is running this, from the environment; `ARTIFEX_HOST` overrides."""
    env = os.environ if env is None else env
    forced = env.get("ARTIFEX_HOST")
    if env.get("CLAUDECODE") == "1" and forced in (None, "claude-code"):
        return {"host": "claude-code", "entrypoint": env.get("CLAUDE_CODE_ENTRYPOINT"),
                "session_id": env.get("CLAUDE_CODE_SESSION_ID"),
                "host_session_id": env.get("CLAUDE_CODE_HOST_SESSION_ID")}
    codex = [k for k in env if k.startswith("CODEX_") and k != "CODEX_HOME"]
    if (codex and forced is None) or forced == "codex":
        return {"host": "codex", "entrypoint": None,
                "session_id": env.get("CODEX_THREAD_ID") or env.get("CODEX_SESSION_ID"), "host_session_id": None}
    return {"host": forced or "unknown", "entrypoint": None, "session_id": None, "host_session_id": None}
