---
type: sesja
date: {{YYYY-MM-DD of the first save}}
updated: {{YYYY-MM-DD}}
status: {{aktywna | wstrzymana | zakończona}}
temat: {{Temat}}
czeka_na: {{short: what must happen before continuing, or empty}}
katalog: {{absolute path of the working directory}}
maszyna: {{hostname}}
repo: {{normalised remote URL, or empty}}
branch: {{git branch, or empty}}
commit: {{short sha of HEAD at save, or empty}}
projekt: "{{[[vault/path/to/project note|Name]] or empty}}"
tags:
  - sesja
---

# {{Temat}}

## Wznowienie
{{3–6 sentences to Claude: what this is, where we stopped, what to check first, the next step. Name files by path.}}

## Cel
{{The goal of the whole topic, 1–2 sentences.}}

## Stan
- {{what's done}}: {{key file or note}}
- {{what's partly done or unverified}}

## Decyzje
| Decyzja | Dlaczego |
| --- | --- |
| {{decision, including rejected options}} | {{reason}} |

## Czeka na
- [ ] {{something the user has to do before continuing}}

## Następne kroki
- [ ] {{task, in order}}

## Polecenia
```
{{commands to run or test with, no secrets}}
```

## Historia
- {{YYYY-MM-DD}} ({{maszyna}}): {{one line: what this sitting did}}
