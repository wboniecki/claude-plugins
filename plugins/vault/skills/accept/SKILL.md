---
name: accept
description: Accept draft notes in the user's Obsidian vault - move them from the drafts folder to their mirrored target path and link them from the fitting MOC. Run only when the user types /vault:accept (or "akceptuj <note>", "akceptuj wszystko", "akceptuj ostatnią").
disable-model-invocation: true
argument-hint: "<draft name> | wszystko | ostatnia"
---

# /vault:accept: drafts → their target, plus MOC links

Input: `$ARGUMENTS`.

```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" config`
```
Waiting drafts (oldest first, newest last):
```
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/promote_drafts.py"`
```
If config has `error`, or `features.accept` is false, show why and stop. Nothing waiting: say so and stop.

## 1. Move
Pick the drafts from the input: a name (fuzzy, against the list above; ask if several match), `wszystko` / `all` → `--all`,
`ostatnia` / `last` / "ostatnia notatka" → `--last`. Then run, once:
`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/promote_drafts.py" <--all | --last | "<draft path>" ...>`
It prints `MOVED <path>`, `SKIP (exists) <path>` (a note is already there: tell the user, don't overwrite) or `NOT FOUND`.

## 2. Link from a MOC
For each `MOVED` note (child notes of a structure: only the parent):
- Find the fitting topic MOC: Glob `<paths.mocs>/**/*.md`, pick by topic, Read it and choose the heading.
- Add `- [[<note title>]]` under that heading. Change nothing else in the MOC.
- No MOC fits: propose a new one (and its link from the top-level MOC) and wait.
Notes with a `type:` of `concept`, `tip` or `devlog` are listed by Obsidian Bases views: no MOC link.

## 3. Report
One line per note: `<target path> ← MOC <name> / <heading>`.
