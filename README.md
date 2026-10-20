# claude-plugins

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace.

## Plugins

### `wb`: dev workflow
- **`/wb:devlog`** logs the current coding session to an Obsidian vault: what changed, why, problems and fixes, what I learned,
  and next steps.
  - Personal and dev projects get `01 - Projects/<…>/<Project>/_index.md` plus `Devlog/` notes.
  - D365 work items get a `## Devlog` section appended to `02 - Areas/01 - Work/<Client>/<ID> - <title>.md`.
  - Shared concept notes go in `04 - Permament/Dev/`.
  - Supports git (GitHub, Azure DevOps) and TFVC.
- **Commit reminder hook:** after Claude makes a successful `git commit` (or a `tf checkin` on Windows), it reminds you to run
  `/wb:devlog`. It runs no scripts: the same `echo` command works in bash and in PowerShell.

## Install (each machine)

1. Tell the skill where the vault is. Add this to your user settings, `~/.claude/settings.json`
   (on Windows, `%USERPROFILE%\.claude\settings.json`), and merge it with what's already there:

   ```json
   { "env": { "DEVLOG_VAULT": "/home/boniek/obsidianvault/wbobsidian" } }
   ```

   On Windows, use the vault's Windows path, written with forward slashes or escaped backslashes:
   `"C:/Users/<you>/Documents/wbobsidian"` or `"C:\\Users\\<you>\\Documents\\wbobsidian"`.

2. In Claude Code:

   ```
   /plugin marketplace add wboniecki/claude-plugins
   /plugin install wb@wboniecki
   ```

3. Restart Claude Code. `/wb:devlog` should now appear in the command list.

## Update

1. Edit in this repo (never in `~/.claude/plugins/`), and bump `version` in `plugins/wb/.claude-plugin/plugin.json`.
2. Run `claude plugin validate .`, then commit and push.
3. On each machine:

   ```
   claude plugin marketplace update wboniecki
   claude plugin update wb@wboniecki
   ```

   Then restart Claude Code.

## Notes for Windows
- Claude Code on Windows uses the PowerShell tool. The hook has matcher groups for both `Bash` and `PowerShell`.
- Git and `tf.exe` must be on PATH. `tf.exe` comes with Visual Studio. Use a Developer PowerShell, or add
  `…\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer` to PATH.
- The vault must be the same Obsidian Sync vault as at home, so notes from both machines meet.
