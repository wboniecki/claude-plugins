"""Pobiera dane gry: opis, gatunki, developer, wydawca, rok, link do strony.

Źródła w kolejności: Wikipedia (bez klucza) -> IGDB (klucze Twitch).
Każde pole bierze się z pierwszego źródła, które je ma.

Klucze: plik z games.keys_file w układzie vaulta (vault.json), patrz fetch_art.load_keys:
    IGDB_CLIENT_ID=...       IGDB_CLIENT_SECRET=...

Użycie (stdlib only, Python 3.9+):
    py fetch_meta.py --title "Metroid Dread" --platform "Nintendo Switch"
Wypisuje JSON: {"title", "description", "genres", "developer", "publisher", "year",
                "wikipedia_url", "igdb_url", "moby_url" (z Wikidata), "sources": {pole: źródło}, "log": {...}}.
Opis jest po angielsku; po polsku streszcza go Claude przy tworzeniu karty.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.dont_write_bytecode = True  # bez __pycache__ w vaulcie (synchronizowałby się przez Obsidian Sync)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # działa też z `py -I`
from fetch_art import http_json, igdb_games, load_keys, norm  # noqa: E402

FIELDS = ["description", "genres", "developer", "publisher", "year"]


# --- Wikipedia (EN): streszczenie + infobox ---
def wiki_clean(s):
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)
    # {{ubl|A|B}}, {{plainlist|...}}, {{vgrelease|...}} -> argumenty
    s = re.sub(r"\{\{\s*(?:ubl|unbulleted list|plainlist|flatlist|hlist)\s*\|", "\n", s, flags=re.I)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = s.replace("}}", "").replace("|", "\n")
    parts = [p.strip(" *'\t") for p in re.split(r"\n|<br\s*/?>|,", s)]
    return [p for p in parts if p]


WIKI_HEADERS = {"User-Agent": "obsidian-gry/1.0 (personal game collection script) python-urllib"}


def wikipedia(title, platform, keys):
    api = "https://en.wikipedia.org/w/api.php?"
    hits = http_json(api + urllib.parse.urlencode({"action": "query", "list": "search", "format": "json",
                                                   "srsearch": f"{title} video game"}),
                     headers=WIKI_HEADERS)["query"]["search"]
    if not hits:
        return {}, "nie znaleziono artykułu"
    page = next((h["title"] for h in hits if norm(h["title"]).startswith(norm(title))), None)
    if not page:
        # np. remaster bez własnego artykułu trafiłby na oryginał, a ten ma inny rok i opis
        return {}, f"brak dokładnego artykułu (najbliższy: {hits[0]['title']})"
    summary = http_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(page.replace(" ", "_")),
                        headers=WIKI_HEADERS)
    wikitext = http_json(api + urllib.parse.urlencode({"action": "parse", "page": page, "prop": "wikitext",
                                                       "section": 0, "format": "json"}),
                         headers=WIKI_HEADERS)["parse"]["wikitext"]["*"]

    def raw(name):
        m = re.search(rf"^\s*\|\s*{name}\s*=(.*?)(?=^\s*\|\s*\w+\s*=|^\}}\}})", wikitext, re.S | re.M | re.I)
        return m.group(1) if m else ""

    def field(name):
        return wiki_clean(raw(name))

    # rok bierzemy z surowego tekstu, bo daty siedzą w szablonach {{Video game release|...}}
    years = re.findall(r"\b(19[7-9]\d|20\d\d)\b", re.sub(r"<ref.*?(?:/>|</ref>)", "", raw("released"), flags=re.S))
    return {"title": summary.get("title"), "wikipedia_url": summary.get("content_urls", {}).get("desktop", {}).get("page"),
            "description": summary.get("extract", ""), "genres": field("genre"),
            "developer": ", ".join(field("developer")), "publisher": ", ".join(field("publisher")),
            "year": min(years) if years else ""}, None


# --- IGDB: gdy Wikipedia nie ma artykułu (remastery, mniejsze gry) ---
def igdb_meta(title, platform, keys):
    games = igdb_games(title, platform, keys,
                       "summary,first_release_date,url,genres.name,"
                       "involved_companies.developer,involved_companies.publisher,involved_companies.company.name")
    if games is None:
        return None, "brak IGDB_CLIENT_ID/SECRET"
    if not games:
        return {}, "nie znaleziono gry"
    g = next((g for g in games if norm(g["name"]) == norm(title)), games[0])
    companies = g.get("involved_companies", [])

    def by_role(role):
        names = []
        for c in companies:
            name = (c.get("company") or {}).get("name")
            if c.get(role) and name and name not in names:
                names.append(name)
        return ", ".join(names)

    released = g.get("first_release_date")
    return {"title": g["name"], "igdb_url": g.get("url"), "description": g.get("summary", ""),
            "genres": [x["name"] for x in g.get("genres", [])],
            "developer": by_role("developer"), "publisher": by_role("publisher"),
            "year": time.strftime("%Y", time.gmtime(released)) if released else ""}, None


SOURCES = [("Wikipedia", wikipedia), ("IGDB", igdb_meta)]


# --- Link do MobyGames przez Wikidata (P11688 = numeryczne ID gry w MobyGames) ---
def moby_url(page):
    """page: tytuł artykułu w angielskiej Wikipedii (przekierowania też działają)."""
    data = http_json("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "wbgetentities", "sites": "enwiki", "titles": page, "redirects": "yes",
         "props": "claims", "format": "json"}), headers=WIKI_HEADERS)
    for entity in data.get("entities", {}).values():
        ids = [c["mainsnak"].get("datavalue", {}).get("value") for c in entity.get("claims", {}).get("P11688", [])]
        if ids and ids[0]:
            return f"https://www.mobygames.com/game/{ids[0]}/"  # pierwsze ID to zwykle podstawowe wydanie
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="tytuł do wyszukania (najlepiej angielski)")
    ap.add_argument("--platform", required=True, help='np. "Nintendo Switch"')
    args = ap.parse_args()

    keys = load_keys()
    result, sources, log = {}, {}, {}
    for src_name, fn in SOURCES:
        try:
            data, err = fn(args.title, args.platform, keys)
        except Exception as e:  # jedno źródło nie może zatrzymać reszty
            data, err = {}, f"błąd: {e}"
        if err:
            log[src_name] = err
        for k, v in (data or {}).items():
            if v and not result.get(k):
                result[k] = v
                if k in FIELDS:
                    sources[k] = src_name
        if all(result.get(f) for f in FIELDS):
            break
    try:
        page = urllib.parse.unquote(result["wikipedia_url"].rsplit("/", 1)[1]) if result.get("wikipedia_url") else args.title
        result["moby_url"] = moby_url(page)
        if not result["moby_url"]:
            log["MobyGames"] = "brak ID MobyGames w Wikidata"
    except Exception as e:
        log["MobyGames"] = f"błąd: {e}"
    result["sources"] = sources
    result["missing"] = [f for f in FIELDS if not result.get(f)]
    result["log"] = log
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
