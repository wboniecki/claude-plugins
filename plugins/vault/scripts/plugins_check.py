"""Compare this device's Obsidian community plugins with the vault's plugin list note (layout key plugins_note).

Usage:
    python -I -B plugins_check.py            # prints OK, or one line per difference (MISSING, NEW, STATE)
    python -I -B plugins_check.py --update   # rewrite the note from this device
The vault comes from the plugin option vault_dir (or VAULT_DIR), see gather.py.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script folder from sys.path
from gather import load  # noqa: E402

SECTIONS = ("Enabled", "Disabled", "Broken")


def device_state(vault):
    obs = vault / ".obsidian"
    enabled_file = obs / "community-plugins.json"
    enabled = set(json.loads(enabled_file.read_text(encoding="utf-8"))) if enabled_file.exists() else set()
    installed, broken = set(), set()
    plugins_dir = obs / "plugins"
    if plugins_dir.is_dir():
        for d in plugins_dir.iterdir():
            if d.is_dir():
                (installed if (d / "manifest.json").exists() else broken).add(d.name)
    state = {}
    for pid in installed:
        state[pid] = "Enabled" if pid in enabled else "Disabled"
    for pid in broken:
        state[pid] = "Broken"
    for pid in enabled - installed - broken:
        state[pid] = "Enabled, not installed"
    return state


def note_state(path):
    state, section = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        h = re.match(r"#+\s*(\w+)", line)
        if h:
            section = h.group(1) if h.group(1) in SECTIONS else None
            continue
        item = re.match(r"\s*-\s+(\S+)", line)
        if section and item:
            state[item.group(1)] = section
    return state


def render(state):
    out = ["---", "tags:", "  - claude", "---"]
    for section in SECTIONS:
        ids = sorted(p for p, s in state.items() if s == section)
        if ids:
            out += [f"# {section}"] + [f"- {p}" for p in ids]
    return "\n".join(out) + "\n"


def diffs(vault, note):
    """Return a list of difference lines, or None when the note is missing."""
    if not note.exists():
        return None
    expected, device = note_state(note), device_state(vault)
    out = []
    for pid in sorted(set(expected) | set(device)):
        want, have = expected.get(pid), device.get(pid)
        if want == have:
            continue
        if have is None:
            out.append(f"MISSING  {pid}: expected {want}, not installed")
        elif want is None:
            out.append(f"NEW      {pid}: {have}, not in note")
        else:
            out.append(f"STATE    {pid}: expected {want}, is {have}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="rewrite the note from this device")
    args = ap.parse_args()
    vault, layout, err = load()
    if err or not layout.get("plugins_note"):
        print(err or "plugins_note is not set in the vault layout file")
        return 1
    note = vault / layout["plugins_note"]
    if args.update:
        device = device_state(vault)
        note.write_bytes(render({p: s for p, s in device.items() if s in SECTIONS}).encode("utf-8"))
        print(f"Updated {note.name} ({len(device)} plugins)")
        return 0
    found = diffs(vault, note)
    if found is None:
        print(f"Missing note: {layout['plugins_note']}. Run with --update to create it.")
        return 1
    print("\n".join(found) if found else "OK")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
