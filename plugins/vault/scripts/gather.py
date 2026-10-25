"""Collect facts for the vault skills in one call, so a skill gets them before its first turn.

Skills inject it with  !`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" <command> --vault "${user_config.vault_dir}"`.
Stdlib only, Python 3.9+. Always exits 0 (a non-zero exit aborts the skill): errors are part of the output.

Commands:
    config    resolved vault folder, layout paths, enabled features, missing paths (JSON)
    folders   the vault's folder tree, one folder per line, indented (plain text: cheaper than JSON)
    devlog    source control, D365 flag, project note, previous log, commits since it, new Learning files,
              existing Dev notes and areas (JSON); run it in the repo being logged

The vault folder comes from --vault, else the env CLAUDE_PLUGIN_OPTION_VAULT_DIR (hooks only), else VAULT_DIR.
The layout file (--layout / option layout_file, default "99 - Meta/Claude/vault.json") maps roles to vault-relative paths.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
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


ARGS = {}  # --vault / --layout given on the command line; they win over the env vars


def take_vault_args(argv):
    """Remove `--vault X` and `--layout X` from argv (in place) and remember them for load().

    Skills pass them as `--vault "${user_config.vault_dir}"`: Claude Code substitutes the option into skill text,
    but exports CLAUDE_PLUGIN_OPTION_* only to hooks, not to commands run through Bash or PowerShell.
    """
    for flag, key in (("--vault", "vault"), ("--layout", "layout")):
        while flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                ARGS[key] = argv[i + 1].strip()
                del argv[i:i + 2]
            else:
                del argv[i]


def load():
    """Return (vault Path or None, layout dict, error or None)."""
    raw = ARGS.get("vault") or env("CLAUDE_PLUGIN_OPTION_VAULT_DIR", "VAULT_DIR")
    if not raw or raw.startswith("${"):
        return None, {}, "vault_dir is not set: set the vault plugin's vault_dir option (/plugin configure vault@wboniecki)"
    vault = Path(raw).expanduser()
    if not vault.is_dir():
        return None, {}, f"vault_dir does not exist: {vault}"
    layout_rel = ARGS.get("layout") or env("CLAUDE_PLUGIN_OPTION_LAYOUT_FILE", "VAULT_LAYOUT_FILE") or DEFAULT_LAYOUT_FILE
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


def run(*args, cwd=None):
    """Run a command, return stripped stdout or "" on any failure."""
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_remote(url):
    url = url.strip()
    if not url:
        return ""
    url = re.sub(r"\.git$", "", url)
    m = re.match(r"git@github\.com:(.+)", url)
    if m:
        return "https://github.com/" + m.group(1)
    m = re.match(r"(?:[^@/]+@)?vs-ssh\.visualstudio\.com:v3/([^/]+)/([^/]+)/(.+)", url)
    if m:
        return f"https://dev.azure.com/{m.group(1)}/{m.group(2)}/_git/{m.group(3)}"
    m = re.match(r"https://(?:[^@/]+@)?([^./]+)\.visualstudio\.com/([^/]+)/_git/(.+)", url)
    if m:
        return f"https://dev.azure.com/{m.group(1)}/{m.group(2)}/_git/{m.group(3)}"
    return re.sub(r"https://[^@/]+@", "https://", url)


def frontmatter(path, keys):
    """Read simple `key: value` lines from a note's frontmatter (no YAML parser in stdlib)."""
    out = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"(\w[\w/-]*):\s*(.*)", line)
        if m and m.group(1) in keys:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def d365_facts(root):
    """Is this a D365 F&O repo? Only sure signals: a model descriptor (<Package>/Descriptor/<Model>.xml, up to two
    folders deep) or TFVC. The one place to plug in a connector to the D365 dev plugin later."""
    root = Path(root)
    if (root / "$tf").exists():
        return {"d365": True, "signal": "tfvc"}
    for pattern in ("*/Descriptor/*.xml", "*/*/Descriptor/*.xml", "*/*/*/Descriptor/*.xml"):
        hit = next(root.glob(pattern), None)
        if hit:
            return {"d365": True, "signal": "descriptor", "descriptor": hit.relative_to(root).as_posix()}
    return {"d365": False}


def find_project(vault, layout, repo_url):
    for key in ("projects_personal", "projects_work"):
        root = layout.get(key)
        if not root or not repo_url:
            continue
        for idx in (vault / root).glob("*/_index.md"):
            if frontmatter(idx, {"repo"}).get("repo", "").rstrip("/") == repo_url:
                return idx.parent, key
    return None, None


def cmd_devlog(vault, layout):
    now = datetime.now()
    out = {"today": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"), "vault": vault.as_posix(), "cwd": os.getcwd()}

    top = run("git", "rev-parse", "--show-toplevel")
    if top:
        remote = normalize_remote(run("git", "remote", "get-url", "origin"))
        branch = run("git", "branch", "--show-current")
        out["source"] = {"kind": "git", "root": top, "remote": remote, "branch": branch,
                         "head": run("git", "rev-parse", "--short", "HEAD")}
        out.update(d365_facts(top))
    elif Path("$tf").exists() or run("tf", "workfold"):
        out["source"] = {"kind": "tfvc"}
        out.update({"d365": True, "signal": "tfvc"})
        remote = ""
    else:
        out["source"] = {"kind": "none"}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return

    # project mode: project note, previous log, commits since it
    project, key = find_project(vault, layout, remote)
    last_commit, newest_mtime = "", 0.0
    if project:
        devlog = project / "Devlog"
        logs = sorted(devlog.glob("*.md")) if devlog.is_dir() else []
        out["project"] = {"index": (project / "_index.md").relative_to(vault).as_posix(), "layout_key": key,
                          "logs": len(logs)}
        if logs:
            newest = logs[-1]
            newest_mtime = newest.stat().st_mtime
            last_commit = frontmatter(newest, {"last_commit"}).get("last_commit", "")
            out["project"]["newest_log"] = newest.relative_to(vault).as_posix()
            today = [p for p in logs if p.name.startswith(out["today"])]
            if today:
                out["project"]["today_log"] = today[-1].relative_to(vault).as_posix()
        # Learning workspace files newer than the previous log
        learning = project / "Learning"
        if learning.is_dir():
            new = [p.relative_to(vault).as_posix() for p in sorted(learning.rglob("*"))
                   if p.suffix in (".html", ".md") and p.parent.name in ("lessons", "learning-records")
                   and p.stat().st_mtime > newest_mtime]
            if new:
                out["learning_new"] = new
    elif top:
        out["project_suggested_name"] = Path(top).name.replace("-", " ").replace("_", " ").title()

    if top:
        if last_commit and run("git", "rev-parse", "--verify", "-q", last_commit + "^{commit}"):
            rng = [f"{last_commit}..HEAD"]
        else:
            rng = ["-20"]
        log = run("git", "log", "--no-merges", "--format=%h %ad %s", "--date=short", *rng)
        out["commits"] = log.splitlines()[:50]
        out["commit_range"] = rng[0]
        if rng[0].endswith("..HEAD"):
            out["diffstat"] = run("git", "diff", "--shortstat", rng[0].replace("..HEAD", ""), "HEAD")

    # existing Dev notes: reuse areas, link instead of duplicating
    dev = layout.get("dev_notes")
    if dev and (vault / dev).is_dir():
        notes, areas = [], set()
        for p in sorted((vault / dev).glob("*.md")):
            fm = frontmatter(p, {"type", "area", "aliases"})
            if fm.get("area"):
                areas.add(fm["area"])
            notes.append(f'{p.stem} | {fm.get("type", "")} | {fm.get("area", "")} | {fm.get("aliases", "")}')
        out["dev_notes"] = {"folder": dev, "areas": sorted(areas), "notes (name | type | area | aliases)": notes}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    take_vault_args(sys.argv)
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
    elif cmd == "devlog":
        cmd_devlog(vault, layout)
    else:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
