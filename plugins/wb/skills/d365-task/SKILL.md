---
name: d365-task
description: Dump a finished D365 F&O work item (description, solution, changed objects, key code, tests) into its task note in the user's Obsidian vault, and offer X++ memo cards. Run only when the user types /wb:d365-task, usually right after "task <n> finished" in a D365 repo.
disable-model-invocation: true
argument-hint: "<work item ID> [client]"
---

# /wb:d365-task: write a finished D365 task to Obsidian

**v0, a soft entry point.** The user will tune it while using it. Keep it simple and follow it literally; see **Later** at the end.

Use Claude's **Glob, Grep, Read, Write and Edit tools** for the vault. Use the shell only for `git`/`tf` and the env var.

## Step 0: vault
Read `DEVLOG_VAULT` (`echo $DEVLOG_VAULT` in bash, `$env:DEVLOG_VAULT` in PowerShell). If it's empty or missing, stop and point
the user to the `env` block in `~/.claude/settings.json` (same as `/wb:devlog`). Never guess the path.

## Step 1: gather
- **ID and client:** from the arguments, else from the branch name (`Sii_<ID>_<Description>` or `feature/<ID>-…`), else ask.
  The client folder is one of `02 - Areas/01 - Work/<NN - Client>/`. If unclear, list the folders and ask.
- **Repo task state:** read `.claude/tasks/<ID>.md` in the repo if it exists (goal, changed objects, decisions, open questions).
- **Changes:** git: `git log --stat <base>..HEAD` and `git diff <base>..HEAD` (base `test`, else `main`/`master`, else ask).
  TFVC: `tf history . /recursive /stopafter:10 /format:brief /noprompt`, or ask for the changeset numbers.
- **This conversation:** the problem, the cause, decisions and why, tests that were run.

## Step 2: write the task note
Target: `02 - Areas/01 - Work/<NN - Client>/<ID> - <title>.md` (Glob `<ID> - *.md` first).
- **Not found:** create it from `templates/d365-task.md` (next to this file). Title: a short Polish description of the task.
- **Found:** append `## Podsumowanie <YYYY-MM-DD>` at the **end** with the same sections as the template body (`### Opis`,
  `### Opis rozwiązania`, …). Add only sections that have content; skip empty ones (no "bez zmian" placeholders).
  Don't change existing text, except checkbox status (see below). In the frontmatter, fill `branch_name`, `solution_name`
  and the changeset key (`changeset/PR` or `changeset`, whichever exists) only if empty.
- **Checkbox status:** tick `- [ ]` items in earlier summaries that are now done (tests the user reports as done,
  to-dos the code now covers). Check to-dos about code yourself in the objects of the task's VS project (repo paths only),
  instead of asking the user.

Content rules:
- **Polish**, like the user's task notes. AOT names and code stay as they are.
- `Opis rozwiązania`: one bullet per changed object (`Object`: what changed and why). Plain words.
- `Kod`: only the key snippets (the CoC method or the core logic), not whole classes. Use ```` ```X++ fold ```` blocks.
- `Testy`: a `- [ ]` checklist of the scenarios tested or still to test.
- `Notatki` to-dos: short summaries of the remaining functional work. No build/compile items (they happen many times
  during a task); mention build/compile only in the pre-PR check.
- **No secrets** (keys, passwords, connection strings, tenant/subscription IDs). **Ask before business data**
  (record values, customer/vendor names, amounts, environment URLs).
- Never move, rename or delete anything in the vault.

## Step 3: memo cards
Look at the code from this task. If a snippet is reusable on its own, offer up to 3 memo cards for `03 - Resources/01 - Work/`.
Use the format in `../devlog/templates/work-card.md` and the **Memo cards** rules in `../devlog/SKILL.md` (title + code,
an explanation only when needed, Grep for duplicates first). Write them only after the user confirms.

## Step 4: report
List the created or changed notes as full paths, in one short list.

## Later
Ideas the user will decide on, so don't do these yet:
- fill `timelog` from the repo's time report (`.claude/tasks/timereport.ps1 -Ticket <ID>`)
- `url` to the work item (dropped for now)
- merge with `/wb:devlog` work mode, which also appends to task notes
