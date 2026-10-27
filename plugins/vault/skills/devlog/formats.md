# Devlog note formats

`{{...}}` is a placeholder: fill it, or drop the line when there's nothing to say. Never leave `{{` in a note.
Links: full vault path without `.md`, plus a display name: `[[01 - Projects/00 - Personal/X/_index|X]]`.

### Links to PRs and commits
PRs and commits in the note body are web links to the repo host. Repo URL: `facts.source.remote`; when it's empty
(a session without git), the `repo:` key of the project's `_index.md`.
- GitHub (`https://github.com/<owner>/<repo>`): PR `[#8](<repo>/pull/8)`, commit ``[`a4684d7`](<repo>/commit/a4684d7)``.
- Azure DevOps (`https://dev.azure.com/…/_git/<repo>`): PR `[#8](<repo>/pullrequest/8)`, commit ``[`a4684d7`](<repo>/commit/a4684d7)``.
- Another host or no repo URL: plain text (`PR #8`, `` `a4684d7` ``).
Frontmatter stays plain: `last_commit` is a bare sha (gather reads it).

## Session log: `<project>/Devlog/YYYY-MM-DD <Topic>.md`
Topic: what the first session was about, at most 5 words. The title never changes after the note is created.

```markdown
---
type: devlog
date: {{YYYY-MM-DD}}
project: "[[{{project _index path}}|{{Project}}]]"
last_commit: {{short sha of the newest commit covered}}
commits: {{number of commits covered}}
tags:
  - devlog
---

# {{YYYY-MM-DD Topic}}

**TLDR:** {{2–3 sentences about the whole day: what got done and what it means.}}
**Lesson:** [[{{lesson .html path}}|{{Lesson N: title}}]]

## Session {{HH:MM}} — {{session topic}}
**Goal:** {{one sentence}}

### Done
- {{outcome, not a file list}}; PR/commit only when it's the point, linked (see Links to PRs and commits)

### Decisions
- {{decision}}: {{why, one line}}

### Problems
- {{symptom as it looked}}: {{cause}} → {{fix}}
  ![[{{screenshot path}}|300]]

### Learned
- [[{{Dev note path}}|{{Concept}}]]: {{one-line takeaway}}
- Record: [[{{learning record path}}|{{record title}}]]

### Review
1. {{one question that checks understanding, not memory of commands}}

### Next
- [ ] {{task}}
```
- About 25 lines per session. Done: at most 5 bullets. Decisions: only non-obvious ones. Problems: one line each,
  a screenshot only for visual (UI/layout) problems when the image exists.
- Drop the **Lesson** line when no lesson came up today; drop empty sections.
- **Appending** (only when the user chose to append to a log dated today): add a new `## Session HH:MM — <topic>` at the end, rewrite **TLDR** so it
  covers all sessions of the day, add a **Lesson** link if a new lesson came up, update `last_commit` and `commits`.
  Don't rename the file and don't change the H1.

## Project index: `<project>/_index.md` (create only when missing)
```markdown
---
type: project
status: active
repo: {{repo url}}
url: {{live url}}
stack: [{{keywords}}]
started: {{YYYY-MM-DD}}
tags:
  - project
  - dev
---

# {{Project}}

## Overview
{{2–4 sentences: what it is, who it's for, what "done" looks like.}}

## Links
- Repo: {{repo url}}
- Live: {{live url}}

## Stack
| Layer | Choice |
| --- | --- |
| {{layer}} | {{choice}} |

## Decisions
| Date | Decision | Why |
| --- | --- | --- |

## Devlog
- [[{{log path}}|{{log title}}]]
```
On every run: add a new log to **Devlog** (newest last), significant decisions to **Decisions**, and update
`status`, `url` or **Stack** when they changed. Nothing else.

## Dev notes: `<dev_notes>/<area folder>/<Name>.md`
One subfolder per area: the folder from `facts.dev_notes.area_folders`. A new area gets a new folder named in
Title Case with spaces (`ci-cd` → `Ci Cd`). Links to Dev notes use the path from `facts.dev_notes.notes`.

## Concept note: `<dev_notes>/<area folder>/<Concept>.md`
```markdown
---
type: concept
aliases: [{{other names, abbreviations}}]
area: {{one existing area}}
tags:
  - concept
first_seen: "[[{{log path}}|{{log title}}]]"
---

# {{Concept}}

## What it is
{{2–5 sentences in plain words. A D365 F&O analogy when one really fits.}}

## Why it matters
{{The problem it solves.}}

## How I used it
- [[{{project _index path}}|{{Project}}]]: {{one line}}

## Gotchas
- {{surprise or limitation seen in practice}}

## Links
- {{official docs URL}}
```
Existing concept: add one line under **How I used it**. That is the only allowed change.

## Tip note: `<dev_notes>/<area folder>/<Tip>.md`
```markdown
---
type: tip
aliases: [{{tool or command names}}]
area: {{one existing area}}
tags:
  - tip
first_seen: "[[{{log path}}|{{log title}}]]"
---

# {{Tip title, e.g. Install Node.js with winget}}

{{One sentence: what it achieves and when you need it.}}

```{{shell}}
{{the exact command that worked}}
```
- `{{flag}}`: {{what it does}}

**Verify:** `{{command that shows it worked}}`

## Gotchas
- {{surprise seen in practice}}
```

## Memo card (X++ / D365): `<work_cards>/<Title>.md`
A self-explanatory title plus code. One or two lines of explanation only when the code alone doesn't explain the trick.
```markdown
---
tags:
  - Work
  - D365
category: {{X++ | Database | Environment | Reporting | Other}}
---
```X++
{{the code}}
```
```
