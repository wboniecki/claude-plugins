"""Hook handlers for the vault plugin. Reads the hook event JSON on stdin and prints nothing unless it has something to say.

    hooks.py push           PostToolUse (Bash/PowerShell): after a successful `git push` or `tf checkin`,
                            remind to run /vault:d365-task (TFVC, or a D365 repo) or /vault:devlog.
                            Force pushes (rewritten history) are ignored.
    hooks.py session-start  SessionStart: in the vault, compare Obsidian community plugins with the plugin list note
                            and report only differences.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script folder from sys.path

GIT_PUSH = re.compile(r"(?:^|[;&|(]\s*|\s)git(?:\s+-C\s+\S+)?\s+push\b")
FORCE = re.compile(r"\s(?:-f|--force(?:-with-lease)?(?:=\S*)?|\+\S+)(?=\s|$)")
TF_CHECKIN = re.compile(r"\btf(?:\.exe)?\s+checkin\b", re.I)


def text_of(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(text_of(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(text_of(v) for v in value)
    return ""


def emit(event, context):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))


def is_d365(cwd):
    from gather import d365_facts, run

    top = run("git", "rev-parse", "--show-toplevel", cwd=cwd)
    return bool(top) and d365_facts(top)["d365"]


def on_push(data):
    cmd = text_of((data.get("tool_input") or {}).get("command", ""))
    out = text_of(data.get("tool_response"))
    if GIT_PUSH.search(cmd):
        if FORCE.search(cmd) or re.search(r"\b(?:rejected|fatal|error):|Everything up-to-date", out):
            return
        if not re.search(r"->|\[new (?:branch|tag)\]", out):
            return
        skill = "/vault:d365-task" if is_d365(data.get("cwd") or os.getcwd()) else "/vault:devlog"
        emit("PostToolUse", "A git push just succeeded. End your reply with one line: "
                            f"Pushed. Run {skill} to log it to Obsidian. Do not run {skill} yourself.")
    elif TF_CHECKIN.search(cmd) and re.search(r"Changeset #?\d+", out, re.I):
        emit("PostToolUse", "A TFVC check-in just created a changeset. End your reply with one line: "
                            "Checked in. Run /vault:d365-task to log it to Obsidian. Do not run /vault:d365-task yourself.")


def on_session_start(data):
    from gather import load
    from plugins_check import diffs

    vault, layout, err = load()
    if err or not layout.get("plugins_note"):
        return
    try:
        cwd = Path(data.get("cwd") or os.getcwd()).resolve()
        if cwd != vault.resolve():
            return
    except OSError:
        return
    found = diffs(vault, vault / layout["plugins_note"])
    if found:
        emit("SessionStart", "Obsidian community plugins on this device differ from "
                             f"'{layout['plugins_note']}':\n" + "\n".join(found) +
                             "\nTell the user briefly at the start of your first reply. If the change was on purpose, "
                             "offer /vault:plugins-check --update.")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    try:
        if sys.argv[1:] == ["push"]:
            on_push(data)
        elif sys.argv[1:] == ["session-start"]:
            on_session_start(data)
    except Exception:  # a hook must never break the session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
