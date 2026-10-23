---
type: session
date: {{YYYY-MM-DD of the first save}}
updated: {{YYYY-MM-DD}}
status: {{active | paused | done}}
topic: {{Topic}}
waiting_for: {{short: what must happen before continuing, or empty}}
dir: {{absolute path of the working directory}}
machine: {{hostname}}
repo: {{normalised remote URL, or empty}}
branch: {{git branch, or empty}}
commit: {{short sha of HEAD at save, or empty}}
project: "{{[[vault/path/to/project note|Name]] or empty}}"
tags:
  - session
---

# {{Topic}}

## Resume
{{3–6 sentences to Claude: what this is, where we stopped, what to check first, the next step. Name files by path.}}

## Goal
{{The goal of the whole topic, 1–2 sentences.}}

## State
- {{what's done}}: {{key file or note}}
- {{what's partly done or unverified}}

## Decisions
| Decision | Why |
| --- | --- |
| {{decision, including rejected options}} | {{reason}} |

## Waiting for
- [ ] {{something the user has to do before continuing}}

## Next steps
- [ ] {{task, in order}}

## Commands
```
{{commands to run or test with, no secrets}}
```

## History
- {{YYYY-MM-DD}} ({{machine}}): {{one line: what this sitting did}}
