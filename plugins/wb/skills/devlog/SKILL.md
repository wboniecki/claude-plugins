---
name: devlog
description: Log the current coding session (setup steps, changes, decisions, problems solved, lessons) into the user's Obsidian vault, either as a project devlog note or as a Devlog section in a D365 work-item note, plus concept notes. Run only when the user types /wb:devlog.
disable-model-invocation: true
argument-hint: "[session title] [--new-project] [--work <ID or client>]"
---

# /wb:devlog: write a session log to Obsidian

The user is learning modern development and is also a Dynamics 365 F&O developer. These notes are their
learning record, so the point is understanding, not a changelog. Write for someone who will reread this in six months.

The skill runs on Linux (bash) and Windows (PowerShell). Use Claude's **Glob, Grep, Read, Write and Edit tools** for every
vault operation. Use the shell only for `git` or `tf` and for reading the env var, so nothing depends on `grep`, `ls` or
path syntax.

## Step 0: find the vault
Read the env var `DEVLOG_VAULT`: `echo $DEVLOG_VAULT` in bash, or `$env:DEVLOG_VAULT` in PowerShell.
If it's empty or the folder doesn't exist, **stop** and tell the user to add it to `~/.claude/settings.json`
(on Windows that's `%USERPROFILE%\.claude\settings.json`):
```json
{ "env": { "DEVLOG_VAULT": "<absolute path to the vault folder>" } }
```
Then they need to restart Claude Code. Never guess the path.

Vault layout (the same vault on every machine, synced with Obsidian Sync):

| What | Where (relative to the vault) |
| --- | --- |
| Personal / dev projects | `01 - Projects/00 - Personal/<Project>/` (`_index.md`, `Devlog/`) |
| Work dev projects (tools, not client items) | `01 - Projects/01 - Work/<Project>/` |
| D365 work items | `02 - Areas/01 - Work/<NN - Client>/<ID> - <title>.md` |
| Client info | `02 - Areas/01 - Work/<NN - Client>/00 - <Client> - …md` |
| Concept notes (shared) | `03 - Resources/00 - Personal/Dev/<Concept>.md` |
| Tip notes (shared) | `03 - Resources/00 - Personal/Dev/<Tip>.md` |
| D365 / X++ memo cards (work) | `03 - Resources/01 - Work/<Title>.md` |
| User's work task template | `99 - Meta/00 - Templates/01 - Work/(T) Work Task.md` |

This skill's own templates are in `templates/`, next to this file: `project-index.md`, `session-log.md`, `concept.md`,
`tip.md`, `work-card.md` and `work-devlog-section.md`. Read them before writing. `{{...}}` marks a placeholder, and every placeholder must be filled.

## Step 1: work out the source and the mode
**Source control:**
- **Git:** `git rev-parse --show-toplevel` works. Get `git remote get-url origin` and normalise it:
  - GitHub: `https://github.com/<owner>/<repo>`. Drop `.git`, and convert `git@github.com:` to `https://github.com/`.
  - Azure DevOps: `https://dev.azure.com/<org>/<project>/_git/<repo>`. Convert `<org>@vs-ssh.visualstudio.com:v3/<org>/<project>/<repo>`
    and `https://<org>.visualstudio.com/<project>/_git/<repo>` to that form, and drop any `user@` prefix.
- **TFVC:** there's no git repo, but a `$tf` folder exists or `tf workfold` works. Changesets come from
  `tf history . /recursive /stopafter:10 /format:brief /noprompt`. If `tf` isn't on PATH, ask the user for the changeset numbers.
- **Neither:** ask what this is.

**Mode:**
- **Work item:** use this when the user passed `--work`, or a work-item ID appears in the branch name (e.g. `feature/17656-…`) or in commit
  or changeset comments, or the remote is Azure DevOps or the source is TFVC. If you're unsure, ask: "Work item (which ID and client?)
  or project log?"
- **Project:** everything else (GitHub repos, personal tools).

## Step 2: gather what happened
- **Project mode:** read `last_commit` from the newest note in `<Project>/Devlog/`, then `git log --stat <last_commit>..HEAD`.
  If there's no previous log, use the whole history.
- **Work mode:** commits on the current branch that aren't in the main branch (`git log --stat main..HEAD`, or `master`), or
  the TFVC changesets above. Skip anything already listed in the note's previous Devlog sections.
- Combine that with this conversation: decisions and why they were made, errors with their exact text and real cause,
  and anything the user asked to understand.

## Step 3a: project mode
1. Find the project: Grep `repo: <normalised url>` in files named `_index.md` under `01 - Projects/`. If nothing matches, or
   `--new-project` was given, ask whether it's personal or work and what it's called (default: the repo name in Title Case).
   Reuse the folder if it already exists, then create `_index.md` from `project-index.md`.
2. Write the log to `<Project>/Devlog/YYYY-MM-DD <Title>.md` from `session-log.md`. If a log dated today already exists, add
   `## Session HH:MM` with the same subsections at the end instead. Update `last_commit` and `commits`.
   When you append, also update that log's **title** so it covers the new session: if it names a version range
   (`wb 0.2-0.3 - …`), extend it (`wb 0.2-0.4 - …`), and add the new topic to the subtitle (`…, session`). Change the H1 and the
   file name together, then fix every link to the old name: Grep the vault for the old file name (the project `_index.md`
   **Devlog** list, `first_seen:` in concept and tip notes) and replace it.
3. Update `_index.md`: add the log to **Devlog** (newest last) and new rows to **Decisions**, and update `status`, `url` or **Stack**.

## Step 3b: work mode
1. Find the client folder under `02 - Areas/01 - Work/` (the folder names are `NN - Client`). If the client isn't clear, list the folders
   and ask.
2. Glob `<client folder>/<ID> - *.md`.
   - **If found:** append a section from `work-devlog-section.md` at the **end** of the note. Don't touch the existing text.
     Existing notes are often in Polish. Leave them as they are and write the new section in English.
     In the frontmatter, fill `branch_name`, `solution_name` and the changeset key (`changeset/PR`, or `changeset` in older notes,
     whichever the note has) **only if they're empty**. Never overwrite a value.
   - **If not found:** create `<ID> - <title>.md` from the user's `(T) Work Task.md`. Resolve its Templater syntax by hand:
     `<% tp.date.now("YYYY-MM-DD")%>` becomes today's date, and `<% tp.file.title %>` becomes the note title. Fill the frontmatter
     you know, put a one-line description under the heading, then append the Devlog section.
3. Work items have no `_index.md`. The task note is the index.

## Step 4: concept and tip notes (both modes)
Pick at most 3 notes in total:
- **Concepts** that are genuinely new to the user (e.g. "Chain of Command", "Astro content collections"), from `concept.md`.
- **Tips**: a reusable command or procedure from the session that the user will want to run again
  (e.g. "Install Node.js with winget"), from `tip.md`.
- **X++ / D365 code from work** is not a tip: it becomes a memo card in `03 - Resources/01 - Work/` from `work-card.md`
  (see below).

Both live flat in `03 - Resources/00 - Personal/Dev/`. Don't create subfolders there: the vault's Dev catalog (an Obsidian Bases view)
lists the notes by `type` and groups them by `area`, so it needs no MOC edits.
- Search first: Glob `03 - Resources/00 - Personal/Dev/*.md`, then Grep `aliases:` for the name and its abbreviations. If a note exists,
  link it. For a concept, add one line under **How I used it**. That's the only change allowed to an existing note.
- If none exists, create one from the template. Create `03 - Resources/00 - Personal/Dev/` if it's missing.
- `area`: Grep `^area:` in `03 - Resources/00 - Personal/Dev/` and reuse an existing value. Add a new one (lowercase, one word or
  kebab-case) only when none fits. Exactly one area per note.
- **From work:** keep concept notes generic. **No client names** (link to the work-item note for context, and write
  "a client project" in the text). **Code is fine**, but make it generic where it's easy.
  **Ask before including any data**: record values, customer or vendor names, amounts, environment names or URLs.

**Memo cards (X++ / D365).** A card is a self-explanatory title plus code, even a single line. No "when to use" sections;
add one or two lines of explanation only when the code alone doesn't make the trick clear.
- Search first: Grep `03 - Resources/01 - Work/` for the main class or method names. If a card already covers it, link it instead.
- File name: short, the title says what the code does (Polish or English, like the existing cards).
- Use generic placeholder names (`Xyz…`) instead of client prefixes where it's easy. Same data rule as above.
- Offer the cards (max 3) and write them only after the user confirms.

Write each note **before** linking to it anywhere else. Clicking an unresolved link makes Obsidian create an empty note.
If a target file already exists and is empty (0 bytes), it's such a placeholder and can be overwritten. If it has content
and it isn't a work-item note from step 3b, ask first.

## Step 5: report
List every created or changed note as a full absolute path. Then add one sentence on what's worth rereading, and remind the user
that Obsidian Sync will pick the notes up.

## Rules
- **English**, unless the user asks for Polish.
- **Links use full vault paths** with `/` (on Windows too), without `.md`, plus a display name:
  `[[01 - Projects/00 - Personal/D365 Blog/_index|D365 Blog]]`. The vault has many `_index.md` files.
- **Plain Markdown only.** No Templater `<% %>` syntax in the output, and no community-plugin syntax. Frontmatter must be valid YAML.
  Quote values that contain `[[`, `:` or `#`.
- **Only touch these notes:** notes this skill created, additions to a project `_index.md`, appended Devlog sections and empty-field
  fills in work-item notes, and one-line additions to concept notes. Never rename, move or delete anything in the vault, except
  renaming a session log this skill wrote when appending to it (step 3a), together with the links to it. The vault holds
  the user's personal notes and their work task tracking.
- **No secrets, ever.** Leave out tokens, keys, passwords, connection strings, one-time codes, subscription or tenant IDs, and
  environment URLs with credentials. Write "the subscription" or "the tenant" instead.
- **Work data:** ask before writing business data anywhere (see step 4). Client names are fine *inside* that client's own
  area folder, because the user already keeps them there.
- **Plain words.** Explain jargon the first time it appears. A D365 F&O comparison helps when it really fits.
- Keep it scannable. Use bullets over paragraphs. Keep a project session log under about 150 lines and a work Devlog section under about 40.
- `Next steps` are written as `- [ ]` tasks, which is where the future planner skill will collect them.
