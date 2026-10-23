"""Collect facts for the vault skills in one call, so a skill gets them before its first turn.

Skills inject it with  !`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" <command>`.
Stdlib only, Python 3.9+. Always exits 0: errors are part of the output, so the skill can report them.

Commands:
    config    resolved vault folder, layout paths, enabled features, missing paths (JSON)
    folders   the vault's folder tree, one folder per line, indented (plain text: cheaper than JSON)

The vault folder comes from the plugin option vault_dir (env CLAUDE_PLUGIN_OPTION_VAULT_DIR), or VAULT_DIR.
The layout file (option layout_file, default "99 - Meta/Claude/vault.json") maps roles to vault-relative paths.
"""
import json
import os
import sys
from pathlib import Path

DEFAULT_LAYOUT_FILE = "99 - Meta/Claude/vault.json"

# feature -> layout keys it needs
FEATURES = {
    "devlog": ["projects_personal", "projects_work", "dev_notes"],
    "d365-task": ["d365_clients", "work_cards"],
    "session": ["sessions"],
    "capture": ["inbox"],
    "note": ["inbox", "drafts", "mocs"],
    "accept": ["drafts", "mocs"],
    "add-game": ["games.cards", "games.images", "games.reference_card"],
    "plugins-check": ["plugins_note"],
}


def env(*names):
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return ""


def load():
    """Return (vault Path or None, layout dict, error or None)."""
    raw = env("CLAUDE_PLUGIN_OPTION_VAULT_DIR", "VAULT_DIR")
    if not raw:
        return None, {}, "vault_dir is not set: set the vault plugin's vault_dir option, or the VAULT_DIR env var"
    vault = Path(raw).expanduser()
    if not vault.is_dir():
        return None, {}, f"vault_dir does not exist: {vault}"
    layout_rel = env("CLAUDE_PLUGIN_OPTION_LAYOUT_FILE", "VAULT_LAYOUT_FILE") or DEFAULT_LAYOUT_FILE
    layout_path = vault / layout_rel
    if not layout_path.is_file():
        return vault, {}, f"layout file not found: {layout_rel}"
    try:
        return vault, json.loads(layout_path.read_text(encoding="utf-8")), None
    except ValueError as e:
        return vault, {}, f"layout file is not valid JSON: {layout_rel}: {e}"


def get(layout, dotted):
    cur = layout
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def cmd_config(vault, layout):
    paths, missing = {}, []

    def walk(d, prefix=""):
        for k, v in d.items():
            key = prefix + k
            if isinstance(v, dict):
                walk(v, key + ".")
            elif isinstance(v, str) and not k.startswith("_"):
                paths[key] = v
                if not (vault / v).exists():
                    missing.append(key)

    walk(layout)
    features = {f: all(get(layout, k) for k in keys) for f, keys in FEATURES.items()}
    return {"vault": vault.as_posix(), "paths": paths, "missing": missing, "features": features}


def cmd_folders(vault, layout):
    exclude = set(layout.get("folders_exclude", []))
    depth = int(layout.get("folders_depth", 4))
    lines = []

    def walk(d, level):
        try:
            subs = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            return
        for p in subs:
            rel = p.relative_to(vault).as_posix()
            if p.name.startswith(".") or p.name in exclude or rel in exclude:
                continue
            lines.append("  " * level + p.name)
            if level + 1 < depth:
                walk(p, level + 1)

    walk(vault, 0)
    return "\n".join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "config"
    vault, layout, err = load()
    if err and (vault is None or cmd != "config"):
        print(json.dumps({"error": err}, ensure_ascii=False))
        return 0
    if cmd == "config":
        out = cmd_config(vault, layout) if not err else {"vault": vault.as_posix(), "error": err}
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif cmd == "folders":
        print(cmd_folders(vault, layout))
    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
