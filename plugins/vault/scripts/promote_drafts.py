"""Move accepted drafts from "<drafts>/<target path>" to "<target path>" in the vault (layout key drafts).

Drafts mirror their target path, so accepting one only drops the prefix. MOC links are added by /vault:accept, not here.

Usage:
    python -I -B promote_drafts.py               # list waiting drafts, newest last
    python -I -B promote_drafts.py --all         # move every draft
    python -I -B promote_drafts.py --last        # move the newest draft
    python -I -B promote_drafts.py <draft> ...   # move these (vault path or relative to the drafts folder)
--vault <path>: the vault (skills pass the plugin option); else env, see gather.py.
Never overwrites an existing note: such a draft is skipped and reported. Exit 1 if anything was skipped or not found.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script folder from sys.path
from gather import load, take_vault_args, utf8_stdio  # noqa: E402


def main():
    utf8_stdio()
    take_vault_args(sys.argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drafts", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--last", action="store_true")
    args = ap.parse_args()

    vault, layout, err = load()
    if err or not layout.get("drafts"):
        print(err or "drafts is not set in the vault layout file")
        return 1 if (args.drafts or args.all or args.last) else 0  # listing is injected into a skill: exit 0
    vault = vault.resolve()
    drafts = (vault / layout["drafts"]).resolve()
    if not drafts.is_dir():
        print("0 draft(s) waiting.")
        return 0
    waiting = sorted((p.resolve() for p in drafts.rglob("*") if p.is_file()), key=lambda p: p.stat().st_mtime)

    if not (args.drafts or args.all or args.last):
        for p in waiting:
            print(p.relative_to(drafts).as_posix())
        print(f"{len(waiting)} draft(s) waiting.")
        return 0

    todo = waiting if args.all else waiting[-1:] if args.last else []
    code = 0
    for a in args.drafts:
        src = next((c.resolve() for c in (vault / a, drafts / a)
                    if c.is_file() and drafts in c.resolve().parents), None)
        if src is None:
            print(f"NOT FOUND {a}")
            code = 1
        else:
            todo.append(src)

    for src in todo:
        dst = vault / src.relative_to(drafts)
        if dst.exists():
            print(f"SKIP (exists) {dst.relative_to(vault).as_posix()}")
            code = 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        for d in src.parents:  # remove empty draft folders left behind
            if d == drafts or any(d.iterdir()):
                break
            d.rmdir()
        print(f"MOVED {dst.relative_to(vault).as_posix()}")
    return code


if __name__ == "__main__":
    sys.exit(main())
