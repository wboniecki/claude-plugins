"""Token usage per skill run, from Claude Code transcripts.

Reads ~/.claude/projects/<project>/<session>.jsonl and its subagents/*.jsonl. A run is a stretch of the main thread
whose replies carry the same `attributionSkill`; subagent replies with that skill and a timestamp inside the stretch
belong to it. Each reply is counted once (a reply is written several times, once per content block).

Usage (stdlib only, Python 3.9+):
    python -I -B tools/skill_cost.py --skill d365-task
    python -I -B tools/skill_cost.py --skill devlog --since 2026-10-23 --project wbobsidian
Columns: calls, input, cache write, cache read, output tokens per thread and model; ctx = context size at the run's
first call. Cache read dominates: every call in the main thread re-reads the whole conversation.
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def replies(path):
    """Yield (timestamp, skill, model, usage) once per reply, in file order."""
    seen = set()
    try:
        lines = path.open(encoding="utf-8")
    except OSError:
        return
    with lines:
        for line in lines:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") or {}
            usage = msg.get("usage")
            if d.get("type") != "assistant" or not usage:
                continue
            key = msg.get("id") or d.get("requestId") or d.get("uuid")
            if key in seen:
                continue
            seen.add(key)
            yield d.get("timestamp", ""), d.get("attributionSkill"), msg.get("model", "?"), usage


def runs(session_file, skill_filter):
    """Group the main thread into runs of one skill; attach matching subagent replies."""
    out, cur = [], None
    for ts, skill, model, usage in replies(session_file):
        if cur and skill == cur["skill"]:
            cur["end"] = ts
        else:
            cur = None
            if skill and skill_filter in skill:
                cur = {"skill": skill, "start": ts, "end": ts, "ctx": sum(usage.get(f, 0) for f in FIELDS[:3]),
                       "usage": defaultdict(lambda: defaultdict(int))}
                out.append(cur)
        if cur:
            add(cur["usage"][("main", model)], usage)
    sub_dir = session_file.with_suffix("") / "subagents"
    for sub in sorted(sub_dir.glob("*.jsonl")) if sub_dir.is_dir() else []:
        for ts, skill, model, usage in replies(sub):
            for r in out:
                if skill == r["skill"] and r["start"] <= ts and (ts <= r["end"] or r is out[-1] or ts < next_start(out, r)):
                    add(r["usage"][("subagent", model)], usage)
                    break
    return out


def next_start(out, r):
    i = out.index(r)
    return out[i + 1]["start"] if i + 1 < len(out) else "9999"


def add(acc, usage):
    acc["calls"] += 1
    for f in FIELDS:
        acc[f] += usage.get(f, 0) or 0


def fmt(n):
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.1f}k" if n >= 1e3 else str(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", default="", help="substring of the skill name, e.g. d365-task")
    ap.add_argument("--since", default="", help="YYYY-MM-DD")
    ap.add_argument("--project", default="", help="substring of the project folder name")
    ap.add_argument("--root", type=Path, default=Path.home() / ".claude" / "projects")
    args = ap.parse_args()

    found = 0
    for proj in sorted(p for p in args.root.iterdir() if p.is_dir() and args.project in p.name):
        for session in sorted(proj.glob("*.jsonl")):
            for r in runs(session, args.skill):
                if r["start"][:10] < args.since:
                    continue
                found += 1
                start = r["start"].replace("T", " ")[:16]
                print(f"\n{start}  {r['skill']}  ctx {fmt(r['ctx'])}  ({proj.name}/{session.stem[:8]})")
                print(f"  {'thread':9} {'model':22} {'calls':>5} {'input':>8} {'c.write':>8} {'c.read':>8} {'output':>8}")
                for (thread, model), u in sorted(r["usage"].items()):
                    print(f"  {thread:9} {model:22} {u['calls']:>5} {fmt(u['input_tokens']):>8} "
                          f"{fmt(u['cache_creation_input_tokens']):>8} {fmt(u['cache_read_input_tokens']):>8} "
                          f"{fmt(u['output_tokens']):>8}")
    if not found:
        print("No runs found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
