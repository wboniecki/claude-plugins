---
name: d365-task
description: Dump a finished D365 F&O work item (description, solution, changed objects, key code, tests) into its task note in the user's Obsidian vault, and offer X++ memo cards. Run only when the user types /vault:d365-task, usually right after "task <n> finished" in a D365 repo.
disable-model-invocation: true
argument-hint: "<work item ID> [client]"
allowed-tools: Bash(python -I -B *) PowerShell(python -I -B *)
---

# /vault:d365-task: write a finished D365 task to Obsidian

Built to be cheap, like `/vault:devlog`: the facts below are already collected, you write one brief, ask one question,
and a subagent does all vault work and reads the diff. **Don't read, search or write the vault yourself**, don't run
git or tf, and don't grep AOT objects.

## Facts (collected before this skill loaded)
```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' d365-task --args "$ARGUMENTS"`
```
Template: `${CLAUDE_PLUGIN_ROOT}/skills/d365-task/templates/d365-task.md`,
memo card format: `${CLAUDE_PLUGIN_ROOT}/skills/devlog/formats.md` (section **Memo card**).

If the facts have `error`, show it and stop. If `source.kind` is `none`, ask which repo this is before going on.

## Step 1: target
- **ID:** `id` (from the arguments, else the branch). Empty: ask in the Step 3 question.
- **Client:** the folder of the one match in `task_notes`; else `client_arg` matched against `clients`; else ask.
  The client only in `clients_archived` (or the note only in `task_notes_archived`): stop and ask, archives are read only.
- **Note:** one match in `task_notes` = append a summary; none = a new note (title in the Step 3 question); several = ask.

## Step 2: the brief (from this conversation + facts)
Short bullets, in Polish (AOT names and code as they are):
- **Opis:** what the task was about, 1–3 lines.
- **Rozwiązanie:** per changed object, what changed and why (from the conversation; `changed` lists the files).
- **Key code:** the objects and methods whose snippets belong in **Kod** (names only: the writer cuts them from the diff).
- **Testy:** scenarios tested (done) and still to test.
- **Notatki:** open questions, gotchas, remaining functional work. No build/compile to-dos.
- **Done to-dos:** which of `task_note.open_todos` the conversation shows as done.
- **Frontmatter:** branch, VS solution, changeset/PR when known (filled only where `task_note.empty_keys` lists them).

Data: names in code (AOT objects, client prefixes) are fine. Personal or customer data from records (names, addresses,
e-mails, tax IDs, customers and vendors from data, amounts tied to them) never: use placeholders (`<Klient>`, `<Kwota>`).
No secrets (keys, passwords, connection strings, tenant/subscription IDs).

## Step 3: one question
Ask once, with AskUserQuestion, everything still open, in one call:
- the title of a new note (propose a short Polish one), the ID or client when unknown;
- **Memo cards** (multi-select, at most 3): snippets from this task reusable on their own. Check `memo_cards.titles`
  first: a matching card is offered as "link <title>", not as a new card.
Skip the question when there's nothing to ask.

## Step 4: hand over
Launch the `vault:d365-task-writer` agent with one prompt containing: the facts JSON, the brief, the target (note path or
client + title), the picked memo cards, and the template and formats file paths. Wait for it.

## Step 5: report
Show the agent's list of notes as full paths (`<vault>/<path>`), in one short list.

## Later
Ideas the user will decide on, so don't do these yet:
- fill `timelog` from the repo's time report (`.claude/tasks/timereport.ps1 -Ticket <ID>`)
- `url` to the work item (dropped for now)
- a connector to the D365 dev plugin (its repo config, base branch, AOT metadata index), one stable contract
