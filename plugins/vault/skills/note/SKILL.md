---
name: note
description: Turn an inbox note into a permanent one, research a topic on the web into a note or a structure of notes (parent + child notes, or a table/collection), or extend an existing note with researched data, in the user's Obsidian vault. New notes are drafts in mirrored folders; the user moves them. Use when the user types /vault:note or says process, przetwórz, inbox, "clean up fleeting notes", "zrób notatkę o…", "create a note about…", build a collection or list, or fill in / enrich a note.
argument-hint: "[inbox note | topic | existing note] [what to fetch] [→ target folder]"
allowed-tools: Bash(python -I -B *) PowerShell(python -I -B *)
---

# /vault:note: inbox, web or topic → draft note

Input: `$ARGUMENTS`.

```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' config`
```
Vault folders (pick targets from this, don't scan the vault):
```
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' folders`
```
If config has `error`, or `features.note` is false, show why and stop. Paths below are relative to `vault`.

## 1. What to do
| Input | Action |
| --- | --- |
| empty or `list` | List `<inbox>/*.md` (not `<drafts>/`), oldest first, plus how many drafts wait in `<drafts>/` for `/vault:accept`. Ask which to process and stop. |
| an inbox note name (fuzzy) | **Process** it (§3). Add web data only if the user asks for it ("dociągnij…", "fetch…"). |
| a topic or request | **Research** it into a new note or structure (§3). |
| an existing note outside the inbox ("uzupełnij…", "fill in…") | **Extend** it in place: fill empty fields or append; keep every row and the user's text (struck-through rows too). |

## 2. Target folder
- The user may give one, often abbreviated: `resources/personal>cookbook` = `03 - Resources/00 - Personal/Cookbook`. Match the
  parts against the folder tree above (ignore `NN - ` prefixes and case). One clear match: use it. Several, or the last part
  doesn't exist: show the best guess and ask.
- No target given: pick from the tree by the PARA test (has an end → Projects; maintained → Areas; knowledge or a source →
  Resources) and reuse existing subfolders.

## 3. Process or research
- **Shape**, the simplest that fits: one note; a structure (parent `<Topic>.md` with a table of contents + subfolder
  `<Topic>/` with child notes that link back with `Część: [[Parent]]`); or a collection (one note with a markdown table).
- **Research**: WebSearch, then WebFetch 2–5 good sources (official, Wikipedia, publishers). Facts over opinions. Never invent
  data: leave a cell empty or `?` and say so in the report.
- **Inbox notes**: if it holds several unrelated ideas, propose a split. Show a short plan (title, target, tags, links, MOC)
  and wait for OK before writing.
- **Links**: Grep the vault for 2–3 clearly related notes (key terms, PL and EN). Only clearly relevant ones.

## 4. Write the draft
Every new note is a draft at `<drafts>/<target folder>/<title>.md` (the target path mirrored). Create the mirror folders.
- An inbox note **becomes** the draft: move it there with one shell `mv` (`Move-Item` on Windows), then rewrite it.
- **Never** move anything to the target folder yourself. The user drags it in Obsidian or runs `/vault:accept`.
- File name = title (spaces and Polish characters are fine, no slugs).
- Language: Polish for personal and general notes, English for dev/tech, or match the notes in the target folder.
- Frontmatter: `date` (original date for inbox notes if known, else today), `tags` (reuse existing ones), `url` (a single
  main source). Keep existing keys.
- Body: short intro → `#` sections → `Powiązane` / `Related` with `[[wikilinks]]` → `Źródła` / `Sources` with the URLs.
  Keep the user's wording, facts, `url`s and embeds (`![[...]]`); improve structure, fix only typos.

## 5. Report
One short list: the draft path(s) (or the extended note), items filled in, anything unverified, and the MOC and heading
that should link it (added on `/vault:accept`, not now: a link to a draft breaks when it moves).
