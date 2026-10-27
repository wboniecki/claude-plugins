---
name: add-game
description: Add a game to the user's game collection in their Obsidian vault as a card note (cover, logo, screenshots, Polish description, links), with data from Wikipedia/IGDB and art from Polish shops, SteamGridDB, LaunchBox and IGDB. Use when the user types /vault:add-game or says dodaj grę, add game, "kupiłem grę", or wants a game on the wishlist (lista życzeń).
argument-hint: <tytuł> [platforma] [szczegóły kopii: cena, kompletność, region, gdzie kupione, status]
allowed-tools: Bash(python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" *) Bash(python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_meta.py" *) Bash(python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_art.py" *) PowerShell(python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" *) PowerShell(python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_meta.py" *) PowerShell(python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_art.py" *)
---

# Dodaj grę do kolekcji

Input: `$ARGUMENTS`: the title, optionally the platform and details of the user's copy (e.g. "Metroid Dread Switch, 120 zł Vinted, CIB PAL").

```json
!`python -I -B "${CLAUDE_PLUGIN_ROOT}/scripts/gather.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' config`
```
If it has `error`, or `features.add-game` is false, show why and stop. Below, `<cards>`, `<images>`, `<reference_card>`,
`<template>` and `<gallery_view>` are the `games.*` paths, all relative to `vault`.

Default platform: Nintendo Switch (ask only if the title exists on several platforms and nothing points to one). Default `status_gry`: `Posiadam`.
The reference card is `<reference_card>`. Copy its shape exactly.

## Platform → code (tag + folder name)
| Platforma | Kod |
| --- | --- |
| Nintendo Switch | NSW |
| Nintendo Switch 2 | NS2 |
| PlayStation 5 / 4 / 3 / 2 / PlayStation | PS5 / PS4 / PS3 / PS2 / PS1 |
| PlayStation Vita / PSP | PSV / PSP |
| Xbox Series X / Xbox One / Xbox 360 | XSX / XONE / X360 |
| Wii U / Wii / GameCube | WIIU / WII / NGC |
| Nintendo 3DS / DS / Game Boy Advance | 3DS / NDS / GBA |
| PC | PC |
Keep it in sync with `<template>`.

## Steps
1. **Duplicate check**: Grep `<cards>/**` for the title. If a card exists, update it (e.g. `status_gry` or copy details) instead of creating a new one.
2. **Data**: `python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_meta.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' --title "<English title>" --platform "<Platforma>"`.
   - Wikipedia first, IGDB as a fallback (e.g. remasters without their own article: "brak dokładnego artykułu"). If both fail, find the data with WebSearch and say so in the report.
   - Write a 2–4 sentence **Polish** description based on the English one. Translate genres into Polish where there's a natural word (Akcja, Przygodowa, Platformowa, RPG, Wyścigi, Strategia, Roguelike, Metroidvania, FPS...).
3. **Art**: `python -I -B "${CLAUDE_PLUGIN_ROOT}/skills/add-game/scripts/fetch_art.py" --vault '${user_config.vault_dir}' --layout '${user_config.layout_file}' --title "<English title>" --platform "<Platforma>" --name "<card title>" --out "<vault>/<images>/<KOD>"`. It downloads the cover, the banner (background, always saved as `.jpg`), the logo, 2 screenshots and up to 3 product photos (`produkt1..3`: box back, 3D box, cartridge/disc) and shrinks them. The source order depends on the image type:
   - **Cover:** the Polish release from a Polish shop first (MediaMarkt, Empik, x-kom; Media Expert blocks bots), then the real box from LaunchBox (SteamGridDB covers are fan art). Empik covers are `.webp`; Obsidian shows them as is.
   - **LaunchBox images** prefer Polish/English releases (`REGION_PREF`: Poland, UK, North America...), so a German, French or Spanish box is used only when nothing else exists. Check `produkt1` (box back): if it is only in a foreign language, delete it and leave its embed out.
   - **Banner:** a SteamGridDB hero.
   - **Special edition:** if `# Notatki` says `Wydanie: <name>` (e.g. Dagdan Collection, Key Card), add `--edition "<name>"`. The shop then looks for that edition, and Empik's gallery photos of it become the `produkt` images.
   - When the cover comes from a shop, the JSON has `shop` and `shop_url`; add `- Okładka: [<shop>](<shop_url>)` to `## Źródła`.

   When re-fetching art for an existing card, first delete its old images, because a new file may have a different extension. Use the real extensions from its JSON output in the card (`.jpg`/`.png`/`.webp`). If something is missing, leave that embed out instead of linking a missing file.
4. **Links** (properties hold bare URLs):
   - `url`: the MobyGames page (`moby_url` from fetch_meta, found through the MobyGames ID on Wikidata, no API key needed). If it's missing, use WebSearch `site:mobygames.com`; if there's still nothing, use `wikipedia_url` or `igdb_url`. Also list it in `## Źródła`.
   - `howlongtobeat`, `opencritic`, `metacritic`: for Switch games, take them from `https://www.dekudeals.com/items/<slug>` (curl, grep `howlongtobeat.com/game.php?id=`, `opencritic.com/game/`, `metacritic.com/game/`). Write HLTB as `https://howlongtobeat.com/game/<id>`. Otherwise use WebSearch. Leave a property empty rather than guessing.
   - `pricecharting`: a search link `https://www.pricecharting.com/search-products?q=<title>+<platform>&type=prices` (the site blocks bots, so no prices).
5. **Write** `<vault>/<cards>/<KOD>/<Tytuł>.md` in the reference card's shape:
   - frontmatter keys in this order: `date` (today), `tags` (`Gra`, `<KOD>`), `cssclasses: [gra]`, `platforma`, `status_gry`, `kompletnosc`, `region`, `data_zakupu`, `cena_zakupu`, `miejsce_zakupu`, `wartosc_usd`, `wartosc_data`, `developer`, `wydawca`, `gatunek`, `rok_wydania`, `okladka`, `pricecharting`, `url`, `howlongtobeat`, `opencritic`, `metacritic`;
   - copy details only from the arguments. Never invent price, region or completeness; leave them empty. Allowed values: `status_gry` Posiadam | Lista życzeń | Sprzedane | Pożyczone; `kompletnosc` Komplet (CIB) | Bez instrukcji | Sam nośnik | Nowa (folia); `region` PAL | NTSC-U | NTSC-J;
   - body: banner embed `|baner` and logo embed `|logo` on two consecutive lines (no blank line between, so the CSS can put the logo over the banner), then the `> [!gra] Informacje` callout with the cover `|okladka` followed directly (consecutive `>` lines, no blank one) by the product photos `|produkt` that were downloaded (they form a swipeable gallery), then `>` and the description, then `>` and a `dataviewjs` block with `await dv.view("<gallery_view>")` as the last part of the callout (it adds the ‹ › arrows), `# Galeria` with screenshots `|screen`, `# Notatki` (the user's remarks from the arguments, in their wording), `## Źródła` (Wikipedia/IGDB and the art source as markdown links).
6. **Report** in one short list: the card path, which sources supplied data and art, and what's missing or unverified.

## API keys
Stored in the vault file `games.keys_file` (synced with "Sync all other types"; environment variables override it). Never read or print this file. Without a key, that source is skipped.
```
STEAMGRIDDB_KEY=        # steamgriddb.com → Preferences → API
IGDB_CLIENT_ID=         # dev.twitch.tv → aplikacja (IGDB używa kont Twitch)
IGDB_CLIENT_SECRET=
```
Twitch app for IGDB: OAuth redirect URL `http://localhost` (never used, the scripts use `client_credentials`), client type "Poufne" (confidential, so it gets a secret).
LaunchBox, Wikipedia and the Polish shops need no keys.
