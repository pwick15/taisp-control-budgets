"""Fail fast on credential problems, before a run spends anything.

Import and call `check_credentials()` at the top of any script that runs an
eval. It costs one tiny model call and turns a class of failure that is
expensive and misleadingly reported into an immediate, actionable error.

The failure this exists for
---------------------------
Inspect loads `.env` from the working directory with dotenv, which by design
does **not** override a variable that is already set in the environment. So an
`ANTHROPIC_API_KEY` exported in your shell silently wins over the one in
`.env`. If the exported key is stale, revoked, or out of credit, every sample
in the run fails with a per-sample API error, the eval still "completes", and
the log reports 100% of samples unscored. The README's advice for auth errors
("check ANTHROPIC_API_KEY is set in .env") is exactly the wrong thing to check
in that case, because it is set there and is being ignored.

This module therefore does two things that the eval framework will not:

1. Reports when the environment and `.env` disagree, and says which one wins.
2. Makes one real generate call through Inspect's own model path, so what gets
   verified is the credential the eval will actually use, not a guess at it.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _reason(exc: Exception) -> str:
    """Pull the provider's own message out of a verbose wrapper exception.

    Inspect's ModelGenerateError embeds the entire request JSON, which buries
    the one line that says what went wrong (e.g. "credit balance is too low").
    """
    text = str(exc)
    for pattern in (r"'message':\s*'([^']{3,400})'", r'"message":\s*"([^"]{3,400})"'):
        found = re.findall(pattern, text)
        if found:
            return found[-1]
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return first[:400] if first else text[:400]


def _dotenv_values(path: Path) -> dict[str, str]:
    """Minimal `.env` reader. Avoids a dependency just to diff two strings."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip("'\"")
    return out


def _report_shadowing(models: list[str], env_path: Path) -> None:
    """Warn when an exported var shadows a different value in `.env`."""
    dotenv = _dotenv_values(env_path)
    if not dotenv:
        return
    providers = {m.split("/", 1)[0] for m in models if "/" in m}
    for provider in sorted(providers):
        var = PROVIDER_KEYS.get(provider)
        if not var:
            continue
        shell_val, file_val = os.environ.get(var), dotenv.get(var)
        if not shell_val or not file_val or shell_val == file_val:
            continue
        print(
            f"WARNING: {var} differs between your shell and {env_path.name}.\n"
            f"  shell: {shell_val[:12]}... ({len(shell_val)} chars)  <-- THIS ONE IS USED\n"
            f"  {env_path.name}:  {file_val[:12]}... ({len(file_val)} chars)\n"
            f"  dotenv does not override an already-set variable. To use the\n"
            f"  {env_path.name} value instead:  unset {var}\n"
            f"  or:  set -a && . ./{env_path.name} && set +a",
            file=sys.stderr,
        )


def check_credentials(*models: str, env_file: str = ".env") -> None:
    """Verify every given model is reachable, or exit(1) with the reason.

    Args:
        models: Inspect model strings, e.g. "anthropic/claude-haiku-4-5-20251001".
            Duplicates are fine and are only checked once.
        env_file: Path to the dotenv file, relative to the working directory.
    """
    from inspect_ai.model import GenerateConfig, get_model

    wanted = sorted(set(m for m in models if m and not m.startswith("mockllm")))
    if not wanted:
        return

    _report_shadowing(wanted, Path(env_file))

    async def probe(name: str) -> tuple[str, str | None]:
        try:
            model = get_model(name, config=GenerateConfig(max_tokens=4))
            await model.generate("Reply with the single word: ok")
            return name, None
        except Exception as exc:  # noqa: BLE001 - the message is the payload
            return name, f"{type(exc).__name__}: {_reason(exc)}"

    results = asyncio.run(_probe_all(probe, wanted))

    failed = [(n, e) for n, e in results if e]
    for name, _ in [r for r in results if not r[1]]:
        print(f"preflight: {name} reachable")
    if not failed:
        return

    print("\npreflight FAILED, not starting the run:", file=sys.stderr)
    for name, err in failed:
        print(f"  {name}\n    {err}", file=sys.stderr)
    print(
        "\nCommon causes:\n"
        "  - the key in your shell is stale and shadows the one in .env (see above)\n"
        "  - the account is out of credit ('credit balance is too low')\n"
        "  - the model id is not served to this account; list what is with:\n"
        "      curl -s https://api.anthropic.com/v1/models \\\n"
        "        -H \"x-api-key: $ANTHROPIC_API_KEY\" -H 'anthropic-version: 2023-06-01'",
        file=sys.stderr,
    )
    sys.exit(1)


async def _probe_all(probe, names: list[str]) -> list[tuple[str, str | None]]:
    return list(await asyncio.gather(*(probe(n) for n in names)))
