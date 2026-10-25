---
name: devlog
description: Log the current coding session (changes, decisions, problems solved, lessons) into the user's Obsidian vault as a project devlog note, plus concept, tip and memo card notes. D365 work items go to /vault:d365-task instead. Run only when the user types /vault:devlog.
disable-model-invocation: true
argument-hint: "[session topic] [--new-project] [--project]"
allowed-tools: Bash(python -I -B *) PowerShell(python -I -B *)
---

# /vault:devlog: write a session log to Obsidian

The user is learning modern development and is also a Dynamics 365 F&O developer. The notes are their learning record:
understanding, not a changelog, for someone rereading it in six months.

This skill is built to be cheap: the facts below are already collected, you write one brief, ask one question, and a
subagent does all vault work. **Don't read, search or write the vault yourself**, and don't run git.

## Facts (collected before this skill loaded)
```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault "${user_config.vault_dir}" --layout "${user_config.layout_file}" devlog`
```
Formats file for the subagent: `${CLAUDE_PLUGIN_ROOT}/skills/devlog/formats.md`

If the facts have `error`, show it and stop (the vault folder is the plugin's `vault_dir` option).
If `source.kind` is `none`, ask what this is before going on.

## Step 1: target
- **D365 repo** (`d365` is true) and no `--project`: reply in one line "This is a D365 task: run `/vault:d365-task <ID>`
  instead." and stop. `--project` logs it as a project anyway (e.g. a private X++ experiment).
- Target: `project.index`. If there's no `project` (or `--new-project`): ask personal or work and the name
  (default `project_suggested_name`) in the Step 3 question.

## Step 2: the brief (from this conversation + facts.commits)
Write it for the subagent, in English, as short bullets:
- **Topic**: at most 5 words (the user's argument if given). It names a new log; when `project.today_log` exists it is the session heading.
- **Goal**, **Done** (outcomes, max 5), **Decisions** (non-obvious, with why), **Problems** (symptom: cause → fix, exact error
  text when it matters, screenshot paths if any were taken), **Learned**, one **Review** question, **Next** tasks.
- **Lesson / records**: the `learning_new` files that belong to today, if any.
- `last_commit` = newest sha covered, `commits` = how many.
Leave out secrets. Names in code (AOT objects, prefixes) are fine; personal or customer data from records (names,
addresses, e-mails, tax IDs, customers and vendors from data) never: use placeholders (`<Customer>`, `<Amount>`).

## Step 3: one question
Ask once, with AskUserQuestion, everything still open, in one call:
- **Notes to write** (multi-select, at most 3 offered): concepts genuinely new to the user, reusable commands (tips), and for
  X++ / D365 work memo cards. Check `dev_notes` first: an existing note is offered as "add a line to <name>", not as a new note.
- the project name/type when it's new.
Skip the question when there's nothing to ask.

## Step 4: hand over
Launch the `vault:devlog-writer` agent with one prompt containing: the facts JSON, the brief, the target, the picks,
and the formats file path. Wait for it.

## Step 5: report
Show the agent's list of notes as full paths (`<vault>/<path>`), plus one sentence on what's worth rereading.
