---
name: sesja
description: Save, list, search, resume, archive or delete Claude work sessions as handoff notes in the user's Obsidian vault, so work can continue in a new session or on another machine. Use when the user types /wb:sesja, or says things like "zapisz sesję", "pokaż zapisane sesje", "ostatnio zajmowaliśmy się X", "wróćmy do X", "save this session", "where did we leave off".
argument-hint: "[zapisz [temat] | lista [fraza] [--archiwum] | wznow <nr|nazwa> | zakoncz <nr|nazwa> | usun <nr|nazwa>]"
---

# /wb:sesja: session handoff notes in Obsidian

A session note is a **temporary handoff**: everything a fresh Claude needs to pick the work up where it stopped, on any machine.
It is not a learning record. That's `/wb:devlog`. A session note lives while the topic is open, then goes to the archive.

The skill runs on Linux (bash) and Windows (PowerShell). Use Claude's **Glob, Grep, Read, Write and Edit tools** for every
vault operation. Use the shell only for `git`, `hostname` and reading the env var.

## Step 0: find the vault
Read `DEVLOG_VAULT`: `echo $DEVLOG_VAULT` in bash, or `$env:DEVLOG_VAULT` in PowerShell. If it's empty or the folder doesn't
exist, **stop** and tell the user to add it to `~/.claude/settings.json` (`%USERPROFILE%\.claude\settings.json` on Windows):
```json
{ "env": { "DEVLOG_VAULT": "<absolute path to the vault folder>" } }
```
then restart Claude Code. Never guess the path.

| What | Where (relative to the vault) |
| --- | --- |
| Open sessions | `99 - Meta/Claude/Sesje/<YYYY-MM-DD> <Temat>.md` |
| Finished sessions | `99 - Meta/Claude/Sesje/Archiwum/` |
| Obsidian view of all sessions | `99 - Meta/Claude/Sesje/Sesje.base` |

Templates are in `templates/` next to this file: `sesja.md` (the note) and `sesje.base` (the view). Read them before writing.
`{{...}}` marks a placeholder; fill every one or delete the line.

If `Sesje.base` is missing, create it from `templates/sesje.base` (on any subcommand). Never overwrite an existing one.

## Pick the subcommand
From the arguments, or from the user's words if the skill was triggered by a phrase:
- `zapisz [temat]` ("zapisz sesję", "save this") → **Save**
- `lista [fraza] [--archiwum]`, no arguments, or "pokaż sesje", "ostatnio zajmowaliśmy się X" → **List** (X is the phrase)
- `wznow <nr|nazwa>` ("wróćmy do X") → **Resume**
- `zakoncz <nr|nazwa>` → **Finish**
- `usun <nr|nazwa>` → **Delete**

A number refers to the last list shown in this conversation. A name is matched fuzzily against file names and `temat`.
If several match, list them and ask.

## Save
1. **Gather the state** from this conversation: the goal, what's done (with the key files), the decisions and why, what the
   user still has to do (keys, exports, approvals), the next steps, the useful commands.
2. **Context:** `hostname`, the current directory. If it's a git repo: `git rev-parse --show-toplevel`, the branch
   (`git branch --show-current`), `git rev-parse --short HEAD`, the remote URL (`git remote get-url origin`) and `git status --short`.
   Mention uncommitted changes in **Stan**: they won't be on another machine unless they're pushed.
3. **Find an existing session** on the same topic: Grep `99 - Meta/Claude/Sesje/*.md` (not the archive) for the `katalog`
   value and the topic keywords. If one clearly matches, **update it**; if it's unclear, ask.
   - Update: rewrite **Wznowienie**, **Stan**, **Czeka na**, **Następne kroki** and **Polecenia** to the current state, add new
     rows to **Decyzje**, append one line to **Historia**, set `updated`, `maszyna`, `status`, `czeka_na` and the git fields.
     Keep everything else.
   - New: `99 - Meta/Claude/Sesje/<today> <Temat>.md` from `templates/sesja.md`. `Temat` is short and specific
     (`Kolekcja gier w Obsidianie`, `Parser TOML w moj-rust`) and has no `\ / : * ? " < > | # ^ [ ]`.
4. **Status:** `aktywna` (just stopping for now), `wstrzymana` (blocked on something, which goes in `czeka_na`),
   `zakończona` (use **Finish** instead). Infer it from the conversation; ask only if it's unclear.
5. If there's a related project note (`01 - Projects/**/_index.md` with a matching `repo:`, or a note the session worked on),
   link it in `projekt`.
6. Report: the full path of the note, its status, and what it waits for. One short list.

### Writing the note
- **Wznowienie** is written *to Claude*: 3–6 sentences, enough to act on without reading the rest. Say what the topic is,
  where it stopped, what to check first, and what to do next. Name files by path.
- Write for a reader with **no memory of this conversation**. Spell out the decisions that were made with the user, and the
  ones the user rejected, so they don't get proposed again.
- Language: the language of the conversation (usually Polish). Plain Markdown, valid YAML, quote values with `[[`, `:` or `#`.
- Links to vault notes: `[[full/vault/path|Name]]` without `.md`. Paths outside the vault: in backticks.
- **No secrets, ever**: no API keys, tokens, passwords, connection strings. Write "the MobyGames key (in keys.env)" instead.
- Keep it under about 120 lines. Bullets over paragraphs.

## List
1. Glob `99 - Meta/Claude/Sesje/*.md` (plus `Archiwum/*.md` with `--archiwum`) and read each note's frontmatter.
2. With a phrase: keep the notes whose name, `temat`, `czeka_na` or body match it (Grep, case-insensitive, try PL and EN words).
   If nothing matches, say so and show the full list.
3. Show one table, newest `updated` first:

   | Nr | Temat | Status | Czeka na | Ostatnio | Maszyna |
   | --- | --- | --- | --- | --- | --- |

   Below it, list each note's vault path (`99 - Meta/Claude/Sesje/…md`) so the user can open it in Obsidian.
4. **Stop** and wait. The user picks a number (then **Resume**), asks for something else, or gives up.

## Resume
1. Read the whole note.
2. **Directory:** if `katalog` exists on this machine, that's where the work happens. If it doesn't (another machine), find the
   same project here (the same `repo` URL in a local clone, or ask for the path).
3. **Git** (if `commit` is set): `git fetch` only if the user agrees, then `git log --oneline <commit>..HEAD` and `git status --short`.
   Report what changed since the save (other machine's commits, local edits).
4. Check the **Czeka na** items you can check yourself (e.g. a file exists, a key is set as an env var or in a config file,
   without printing its value). Tell the user which ones are still open.
5. Summarize in a few lines: where we stopped, what changed since, what's still blocked, and the first next step. **Ask for
   the go-ahead** before doing anything.
6. Once work continues, set `status: aktywna` and append a Historia line ("wznowiona na <maszyna>").

## Finish
1. Ask for a one-line outcome if it isn't obvious.
2. Set `status: zakończona`, `updated`, clear `czeka_na`, append the outcome to **Historia**.
3. Move the file to `Archiwum/` (create the folder if needed) with the same name. Use Read + Write to the new path, then
   delete the old file with the shell (`rm` / `Remove-Item`) only after the new one is written.
4. If the session was dev work and no devlog covers it, suggest `/wb:devlog`.

## Delete
Only on explicit request. Show the note's name, status and `updated`, ask "Usunąć na stałe?" and wait for a clear yes.
Deleted notes can't be recovered from the vault (Obsidian Sync's version history may still have them).

## Rules
- **Only touch** notes in `99 - Meta/Claude/Sesje/` (and `Sesje.base`). Never rename, move or delete anything else in the vault.
- One note per topic. Don't create a second note for a topic that has an open one; update it.
- Never invent progress. If something wasn't verified in the session, say so in **Stan**.
