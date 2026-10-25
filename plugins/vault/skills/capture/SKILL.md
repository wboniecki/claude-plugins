---
name: capture
description: Quickly capture a thought, link, article or video as an inbox note in the user's Obsidian vault, from any repo. Summarizes links by default (TL;DR + key points); saves just the link with --raw. Use when the user types /vault:capture or says capture, zapisz, notatka szybka, "save this", streść (to), podsumuj, summarize, sum up, tl;dr (summary), or zapisz link, zakładka, bookmark, save link, read later (raw), or pastes a URL or text to keep for later.
argument-hint: "<text | url> [comment] [--raw]"
allowed-tools: Bash(python -I -B *) PowerShell(python -I -B *)
---

# /vault:capture: a quick inbox note

Input: `$ARGUMENTS`.

```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' config`
```
If it has `error`, or `features.capture` is false, show why and stop. The note goes to `<vault>/<paths.inbox>/`.

## 1. Mode
- **raw**: `--raw`, or the user said zapisz link, zakładka, bookmark, save link, read later. Don't fetch anything: title from
  the user's words or the URL, the URL, and their comment.
- **summary** (default for a URL; also streść, podsumuj, summarize, sum up, tl;dr):
  - article, docs, blog → WebFetch it: the title, author, a 1–2 sentence TL;DR and 3–7 key points.
  - video (youtube.com, youtu.be, vimeo…) → WebFetch the page: title, channel, the description's main points. Say in the note
    that it's based on the description, not the video. A transcript the user pasted is summarized instead.
- **thought** (plain text, no URL): the user's own words. Keep their wording, fix only obvious typos. No fetching.

## 2. Title and language
- Video: `YT - <video title>`. Otherwise a short descriptive title.
- Strip `\ / : * ? " < > | # ^ [ ]`. If the file exists, ask: append, or a new name.
- Language of the source or of the user's text.

## 3. Write `<vault>/<inbox>/<title>.md`
```markdown
---
date: YYYY-MM-DD
url: <url>              # sources only
tags:
  - <1–2 tags, e.g. YT, Personal, Work>
---
**TL;DR:** <1–2 sentences>        # summary mode; raw/thought: one line of context instead

# Najważniejsze punkty / Key points
- ...                              # summary mode only

# Moje przemyślenia / Own thoughts
<the user's comment, if any>
```
Keep it short: it's an inbox note, `/vault:note` turns it into a permanent one later. Don't search the vault for links.

## 4. Report
One line: `<mode> → <vault-relative path>` (e.g. `summary (article) → 04 - Fleeting/X.md`). Don't repeat the content.
