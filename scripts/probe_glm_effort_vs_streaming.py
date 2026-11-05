"""Does streaming, not effort, drive GLM-5.3's generation length? (Answer: no, effort does.)

The study's GLM effort ladder crosses a serving boundary: the two high-token rungs
(default and effort=none) were sent streamed, the two low-token rungs (low, high) were
not. No existing arm varies streaming at fixed effort, so the logs cannot separate them.
This replays 50 real monitor prompts from the effort=high run through a 2x2 of
{effort=high, no effort field} x {stream off, stream on}.

    python scripts/probe_glm_effort_vs_streaming.py smoke   # 2 prompts x 4 cells, 8 calls
    python scripts/probe_glm_effort_vs_streaming.py full    # 50 prompts x 4 cells, 200 calls

Findings and the numbers this produced: results/analysis/GLM-EFFORT-VS-STREAMING.md
"""
import asyncio, json, os, statistics, sys, time
from pathlib import Path
import httpx

CACHE = Path("results/analysis/glm-probe-prompts.json")
OUT = Path("results/analysis/glm-probe-results.json")
SOURCE_LOG = "logs/dataset-glm53-efforthigh-tm-n500-strip/trusted_monitoring"


def extract_prompts(per_mode: int = 25) -> list[dict]:
    """The study's own monitor prompts, read back out of the eval log.

    Inspect replaces large message content with an `attachment://` reference, so the
    request record alone is not replayable; the sample's `attachments` map resolves it.
    Using the logged prompts rather than rebuilding them from the template guarantees the
    probe varies only the two parameters under test.
    """
    from inspect_ai.log import list_eval_logs, read_eval_log
    out = []
    for entry in list_eval_logs(SOURCE_LOG):
        log = read_eval_log(entry.name)
        taken = 0
        for smp in (log.samples or []):
            attach = smp.attachments or {}
            mode = (smp.metadata or {}).get("eval_mode")
            for ev in smp.events:
                if getattr(ev, "event", None) != "model" or not getattr(ev, "call", None):
                    continue
                msgs, ok = [], True
                for m in (ev.call.request or {}).get("messages", []):
                    c = m.get("content")
                    if isinstance(c, str) and c.startswith("attachment://"):
                        c = attach.get(c.split("attachment://")[1])
                    if not isinstance(c, str):
                        ok = False
                        break
                    msgs.append({"role": m.get("role", "user"), "content": c})
                if ok and msgs and sum(len(m["content"]) for m in msgs) > 1000:
                    out.append({"mode": mode, "id": str(smp.id), "messages": msgs})
                    taken += 1
                break
            if taken >= per_mode:
                break
    return out


if CACHE.exists():
    PROMPTS = json.loads(CACHE.read_text())
else:
    PROMPTS = extract_prompts()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(PROMPTS))
    print(f"extracted {len(PROMPTS)} prompts from {SOURCE_LOG} into {CACHE}")
MODEL = "deepinfra/zai-org/GLM-5.3"
MAX_TOKENS = 8192          # bounds worst-case spend; truncation rate is reported
CONCURRENCY = 5
BASE = os.environ["LITELLM_BASE_URL"].rstrip("/")
KEY = os.environ["LITELLM_API_KEY"]

CELLS = [("high", False), ("high", True), (None, False), (None, True)]


def body(messages, effort, stream):
    b = {"model": MODEL, "messages": messages, "max_tokens": MAX_TOKENS,
         "temperature": 0.0, "stream": stream}
    if effort is not None:
        b["reasoning_effort"] = effort
        b["allowed_openai_params"] = ["reasoning_effort"]
    if stream:
        b["stream_options"] = {"include_usage": True}
    return b


def pull(usage, finish):
    d = (usage or {}).get("completion_tokens_details") or {}
    p = (usage or {}).get("prompt_tokens_details") or {}
    return {"completion": (usage or {}).get("completion_tokens"),
            "reasoning": d.get("reasoning_tokens"),
            "prompt": (usage or {}).get("prompt_tokens"),
            "cached": p.get("cached_tokens"),
            "cost": (usage or {}).get("estimated_cost"),
            "finish": finish}


async def one(client, sem, rec, effort, stream):
    async with sem:
        t0 = time.time()
        try:
            if not stream:
                r = await client.post(f"{BASE}/v1/chat/completions",
                                      json=body(rec["messages"], effort, False),
                                      headers={"Authorization": f"Bearer {KEY}"}, timeout=600)
                r.raise_for_status()
                j = r.json()
                out = pull(j.get("usage"), (j.get("choices") or [{}])[0].get("finish_reason"))
            else:
                usage = None; finish = None
                async with client.stream("POST", f"{BASE}/v1/chat/completions",
                                         json=body(rec["messages"], effort, True),
                                         headers={"Authorization": f"Bearer {KEY}"},
                                         timeout=600) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                        for ch in chunk.get("choices") or []:
                            if ch.get("finish_reason"):
                                finish = ch["finish_reason"]
                out = pull(usage, finish)
            out.update(mode=rec["mode"], id=rec["id"], effort=str(effort), stream=stream,
                       secs=round(time.time() - t0, 1))
            return out
        except Exception as e:
            return {"mode": rec["mode"], "id": rec["id"], "effort": str(effort),
                    "stream": stream, "error": str(e)[:200], "secs": round(time.time() - t0, 1)}


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    recs = PROMPTS[:1] + [p for p in PROMPTS if p["mode"] == "attack"][:1] if mode == "smoke" else PROMPTS
    print(f"{mode}: {len(recs)} prompts x {len(CELLS)} cells = {len(recs)*len(CELLS)} calls", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    rows = []
    async with httpx.AsyncClient() as client:
        for effort, stream in CELLS:
            got = await asyncio.gather(*(one(client, sem, r, effort, stream) for r in recs))
            rows.extend(got)
            ok = [g for g in got if "error" not in g and g.get("completion") is not None]
            errs = [g for g in got if "error" in g]
            label = f"effort={effort or 'unset':5s} stream={str(stream):5s}"
            if ok:
                comp = [g["completion"] for g in ok]
                reas = [g["reasoning"] or 0 for g in ok]
                trunc = sum(1 for g in ok if g["finish"] == "length")
                cost = sum(g["cost"] or 0 for g in ok)
                print(f"  {label}  n={len(ok):3d}  completion median={statistics.median(comp):7.0f} "
                      f"mean={statistics.mean(comp):7.0f}  reasoning median={statistics.median(reas):6.0f} "
                      f"trunc={trunc}  ${cost:.4f}", flush=True)
            if errs:
                print(f"  {label}  {len(errs)} ERRORS e.g. {errs[0]['error'][:120]}", flush=True)
    OUT.write_text(json.dumps(rows, indent=1))
    tot = sum(r.get("cost") or 0 for r in rows)
    print(f"\nwrote {OUT}  total reported cost ${tot:.4f}")

asyncio.run(main())
