---
name: plugins-check
description: Compare this device's Obsidian community plugins with the vault's plugin list note, or rewrite the note with --update. Run only when the user types /vault:plugins-check.
disable-model-invocation: true
argument-hint: "[--update]"
allowed-tools: Bash(python -I -B *) PowerShell(python -I -B *)
---

Result of `plugins_check.py $ARGUMENTS`:
```
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/plugins_check.py" --report --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' $ARGUMENTS`
```
Report it to the user in one or two lines: `OK`, the note was updated, or each difference (MISSING = expected but not
installed here, NEW = installed here but not in the note, STATE = enabled/disabled/broken differs).
After differences, offer `/vault:plugins-check --update` if the user changed plugins on purpose. Do nothing else.
