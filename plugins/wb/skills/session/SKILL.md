---
name: session
description: Save, list, search, resume, finish (archive) or delete Claude work sessions as handoff notes in the user's Obsidian vault, so work can continue in a new session or on another machine. Use when the user types /wb:session, or says things like "save this session", "show saved sessions", "where did we leave off", "last time we worked on X", "let's get back to X", or the Polish "zapisz sesję", "pokaż zapisane sesje", "ostatnio zajmowaliśmy się X", "wróćmy do X".
argument-hint: "[save [topic] | list [phrase] [--archive] | resume <no|name> | finish <no|name> | delete <no|name>]"
---

# /wb:session: session handoff notes in Obsidian

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
| Open sessions | `99 - Meta/Claude/Sessions/<YYYY-MM-DD> <Topic>.md` |
| Finished sessions | `99 - Meta/Claude/Sessions/Archive/` |
| Obsidian view of all sessions | `99 - Meta/Claude/Sessions/Sessions.base` |

Templates are in `templates/` next to this file: `session.md` (the note) and `sessions.base` (the view). Read them before writing.
`{{...}}` marks a placeholder; fill every one or delete the line.

If `Sessions.base` is missing, create it from `templates/sessions.base` (on any subcommand). Never overwrite an existing one.

## Pick the subcommand
From the arguments, or from the user's words if the skill was triggered by a phrase:
- `save [topic]` ("save this session", "zapisz sesję") → **Save**
- `list [phrase] [--archive]`, no arguments, or "show sessions", "last time we worked on X" → **List** (X is the phrase)
- `resume <no|name>` ("let's get back to X") → **Resume**
- `finish <no|name>` → **Finish**
- `delete <no|name>` → **Delete**

A number refers to the last list shown in this conversation. A name is matched fuzzily against file names and `topic`.
If several match, list them and ask.

## Save
1. **Gather the state** from this conversation: the goal, what's done (with the key files), the decisions and why, what the
   user still has to do (keys, exports, approvals), the next steps, the useful commands.
2. **Context:** `hostname`, the current directory. If it's a git repo: `git rev-parse --show-toplevel`, the branch
   (`git branch --show-current`), `git rev-parse --short HEAD`, the remote URL (`git remote get-url origin`) and `git status --short`.
   Mention uncommitted changes in **State**: they won't be on another machine unless they're pushed.
3. **Find an existing session** on the same topic: Grep `99 - Meta/Claude/Sessions/*.md` (not the archive) for the `dir`
   value and the topic keywords. If one clearly matches, **update it**; if it's unclear, ask.
   - Update: rewrite **Resume**, **State**, **Waiting for**, **Next steps** and **Commands** to the current state, add new
     rows to **Decisions**, append one line to **History**, set `updated`, `machine`, `status`, `waiting_for` and the git fields.
     Keep everything else.
   - New: `99 - Meta/Claude/Sessions/<today> <Topic>.md` from `templates/session.md`. `Topic` is short and specific
     (`Game collection in Obsidian`, `TOML parser in my-rust`) and has no `\ / : * ? " < > | # ^ [ ]`.
4. **Status:** `active` (just stopping for now), `paused` (blocked on something, which goes in `waiting_for`),
   `done` (use **Finish** instead). Infer it from the conversation; ask only if it's unclear.
5. If there's a related project note (`01 - Projects/**/_index.md` with a matching `repo:`, or a note the session worked on),
   link it in `project`.
6. Report: the full path of the note, its status, and what it waits for. One short list.

### Writing the note
- **Resume** is written *to Claude*: 3–6 sentences, enough to act on without reading the rest. Say what the topic is,
  where it stopped, what to check first, and what to do next. Name files by path.
- Write for a reader with **no memory of this conversation**. Spell out the decisions that were made with the user, and the
  ones the user rejected, so they don't get proposed again.
- Language: keys, headings and status values stay in English (from the template). The content is in the language of the
  conversation (often Polish). Plain Markdown, valid YAML, quote values with `[[`, `:` or `#`.
- Links to vault notes: `[[full/vault/path|Name]]` without `.md`. Paths outside the vault: in backticks.
- **No secrets, ever**: no API keys, tokens, passwords, connection strings. Write "the MobyGames key (in keys.env)" instead.
- Keep it under about 120 lines. Bullets over paragraphs.

## List
1. Glob `99 - Meta/Claude/Sessions/*.md` (plus `Archive/*.md` with `--archive`) and read each note's frontmatter.
2. With a phrase: keep the notes whose name, `topic`, `waiting_for` or body match it (Grep, case-insensitive, try PL and EN words).
   If nothing matches, say so and show the full list.
3. Show one table, newest `updated` first:

   | No | Topic | Status | Waiting for | Updated | Machine |
   | --- | --- | --- | --- | --- | --- |

   Below it, list each note's vault path (`99 - Meta/Claude/Sessions/…md`) so the user can open it in Obsidian.
4. **Stop** and wait. The user picks a number (then **Resume**), asks for something else, or gives up.

## Resume
1. Read the whole note.
2. **Directory:** if `dir` exists on this machine, that's where the work happens. If it doesn't (another machine), find the
   same project here (the same `repo` URL in a local clone, or ask for the path).
3. **Git** (if `commit` is set): `git fetch` only if the user agrees, then `git log --oneline <commit>..HEAD` and `git status --short`.
   Report what changed since the save (other machine's commits, local edits).
4. Check the **Waiting for** items you can check yourself (e.g. a file exists, a key is set as an env var or in a config file,
   without printing its value). Tell the user which ones are still open.
5. Summarize in a few lines: where we stopped, what changed since, what's still blocked, and the first next step. **Ask for
   the go-ahead** before doing anything.
6. Once work continues, set `status: active` and append a History line ("resumed on <machine>").

## Finish
1. Ask for a one-line outcome if it isn't obvious.
2. Set `status: done`, `updated`, clear `waiting_for`, append the outcome to **History**.
3. Move the file to `Archive/` (create the folder if needed) with the same name. Use Read + Write to the new path, then
   delete the old file with the shell (`rm` / `Remove-Item`) only after the new one is written.
4. If the session was dev work and no devlog covers it, suggest `/wb:devlog`.

## Delete
Only on explicit request. Show the note's name, status and `updated`, ask whether to delete it for good, and wait for a clear yes.
Deleted notes can't be recovered from the vault (Obsidian Sync's version history may still have them).

## Rules
- **Only touch** notes in `99 - Meta/Claude/Sessions/` (and `Sessions.base`). Never rename, move or delete anything else in the vault.
- One note per topic. Don't create a second note for a topic that has an open one; update it.
- Never invent progress. If something wasn't verified in the session, say so in **State**.
