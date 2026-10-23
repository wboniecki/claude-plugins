# claude-plugins

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace.

## `vault`: Obsidian vault workflow

Writes work into an Obsidian vault from any repo. The vault's folder layout comes from a JSON file in the vault,
so any structure works, and a feature without its folder is simply off.

| Command | What it does |
| --- | --- |
| `/vault:devlog` | Logs the current coding session: a project devlog note (TLDR, done, decisions, problems, learned, next) or a section in a D365 work-item note, plus concept, tip and memo card notes you pick. |
| `/vault:d365-task <ID> [client]` | Writes a finished D365 F&O task into its task note and offers X++ memo cards. |
| `/vault:session` | Saves, lists, resumes and archives handoff notes, so work continues in a new session or on another machine. |
| `/vault:capture <text \| url>` | Quick inbox note: a summary of an article or video, `--raw` for just the link, or your own thought. |
| `/vault:note` | Turns an inbox note, a topic or web research into a draft note (or a structure or collection), or extends an existing note. |
| `/vault:accept` | Moves drafts to their target folder and links them from a MOC. |
| `/vault:add-game <title>` | Adds a game card to a game collection: data, cover and art, links. |
| `/vault:plugins-check` | Compares the device's Obsidian community plugins with a list note. |

Hooks:
- after a successful `git push` or `tf checkin`, a one-line reminder to run `/vault:devlog`;
- when a session starts in the vault, a plugin check that speaks only when something differs.

Supports git (GitHub, Azure DevOps) and TFVC, on Linux, macOS and Windows.

## Install

Requirements: Claude Code, `python` 3.9+ on PATH.

```
claude plugin marketplace add wboniecki/claude-plugins
claude plugin install vault@wboniecki
```
When asked, set `vault_dir` to the vault's absolute path on this machine. Restart Claude Code.

Then add the layout file to the vault (default path `99 - Meta/Claude/vault.json`, changeable with the `layout_file` option).
Paths are relative to the vault; leave a key out to turn its feature off:

```json
{
  "inbox": "Inbox",
  "drafts": "Inbox/Claude",
  "mocs": "Maps",
  "archives": "Archive",
  "projects_personal": "Projects/Personal",
  "projects_work": "Projects/Work",
  "d365_clients": "Projects/Work",
  "work_task_template": "Templates/Work Task.md",
  "dev_notes": "Resources/Dev",
  "work_cards": "Resources/Work",
  "sessions": "Claude/Sessions",
  "plugins_note": "Obsidian plugins.md",
  "games": {
    "cards": "Areas/Games",
    "images": "Images/Games",
    "reference_card": "Areas/Games/Example.md",
    "template": "Templates/Game.md",
    "gallery_view": "Scripts/game-gallery",
    "keys_file": "Claude/game-keys.env"
  },
  "folders_exclude": ["Archive", "attachments"],
  "folders_depth": 4
}
```

## Update

```
claude plugin marketplace update wboniecki
claude plugin update vault@wboniecki
```
