"""Pobiera grafiki gry (okładka, baner/tło, logo, screeny) do vaulta.

Źródła: polskie sklepy (Empik, MediaMarkt, x-kom), SteamGridDB, LaunchBox, IGDB. Kolejność zależy od typu
grafiki (KIND_ORDER): okładka to prawdziwe pudełko, najpierw polskie wydanie ze sklepu, potem LaunchBox
(w SteamGridDB okładki to fan arty), baner to "hero" z SteamGridDB (szeroki, bez napisów, pod logo).
Z --edition (np. "Dagdan Collection") sklep szuka tej edycji, a zdjęcia z jej galerii idą jako zdjęcia produktu.
Dla każdego typu grafiki brane jest pierwsze źródło, które coś zwróci.
Źródła bez kluczy są pomijane (LaunchBox nie wymaga klucza).
Za duże obrazy są zmniejszane (Pillow, a bez niego PowerShell na Windows albo ImageMagick).

Klucze: plik z games.keys_file w układzie vaulta (vault.json; w vaulcie, synchronizuje się przez Obsidian Sync):
    STEAMGRIDDB_KEY=...
    IGDB_CLIENT_ID=...       IGDB_CLIENT_SECRET=...

Użycie (stdlib only, Python 3.9+):
    py fetch_art.py --title "Metroid Dread" --platform "Nintendo Switch" \
        --out "99 - Meta/99 - Images/Personal/Gry/NSW" [--name "Metroid Dread"] [--screens 2] [--products 3] \
        [--edition "Dagdan Collection"]
Wypisuje JSON: {"okladka": {"files": [...], "source": ...}, ..., "missing": [...], "log": {...}}.
"""
import argparse
import functools
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (obsidian-gry fetch_art)"
KINDS = ["okladka", "baner", "logo", "screen", "produkt"]
MAX_EDGE = {"okladka": 1200, "baner": 1920, "logo": 800, "screen": 1600, "produkt": 900}  # px, dłuższy bok
# Zdjęcia produktu (do galerii obok okładki): po jednym z każdego typu, w tej kolejności.
LB_PRODUCT = ["Box - Back", "Box - 3D", "Cart - Front", "Disc", "Cart - 3D",
              "Fanart - Box - Back", "Fanart - Cart - Front", "Fanart - Disc", "Box - Spine"]

# Identyfikatory platform w IGDB.
IGDB_PLATFORMS = {"Nintendo Switch": 130, "Nintendo Switch 2": 508, "PlayStation 3": 9, "PlayStation 4": 48,
                  "PlayStation 5": 167, "PlayStation 2": 8, "PlayStation": 7,
                  "Nintendo 3DS": 37, "Nintendo DS": 20, "Wii": 5, "Wii U": 41,
                  "GameCube": 21, "Game Boy Advance": 24, "Nintendo 64": 4,
                  "SNES": 19, "NES": 18, "PlayStation Vita": 46, "PSP": 38,
                  "Xbox 360": 12, "Xbox": 11, "PC": 6}
MAX_MB = 1.5  # większe pliki tylko gdy nie ma nic mniejszego
# Najpierw wydania po polsku lub angielsku; reszta regionów (Niemcy, Francja, Hiszpania...) tylko gdy nie ma nic innego.
REGION_PREF = ["Poland", "United Kingdom", "North America", "World", "Europe", "Australia", "Canada"]


def load_keys():
    keys = dict(os.environ)
    # scripts -> add-game -> skills -> plugin root; gather.load() zna vault i jego układ, więc działa z każdego cwd
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from gather import get, load

    vault, layout, _ = load()
    rel = get(layout, "games.keys_file") if vault else None
    path = vault / rel if rel else None
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys.setdefault(k.strip(), v.strip())
    return keys


def http(url, data=None, headers=None, retry=True):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 429 and retry:  # chwilowy limit zapytań: jedna ponowna próba po Retry-After
            wait = e.headers.get("Retry-After", "5")
            time.sleep(min(int(wait), 60) + 1 if wait.isdigit() else 5)
            return http(url, data, headers, retry=False)
        raise


def http_json(url, **kw):
    return json.loads(http(url, **kw).decode("utf-8"))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --- SteamGridDB: okładka (grid 600x900), baner (hero), logo. Brak screenów. ---
def steamgriddb(title, platform, keys, screens, products):
    key = keys.get("STEAMGRIDDB_KEY")
    if not key:
        return None, "brak STEAMGRIDDB_KEY"
    h = {"Authorization": f"Bearer {key}"}
    base = "https://www.steamgriddb.com/api/v2"
    found = http_json(f"{base}/search/autocomplete/{urllib.parse.quote(title)}", headers=h).get("data") or []
    match = next((g for g in found if norm(g["name"]) == norm(title)), None)
    if not match:
        return {}, "nie znaleziono gry"
    gid = match["id"]

    def first(path, query=""):
        items = http_json(f"{base}/{path}/game/{gid}{query}", headers=h).get("data") or []
        return [items[0]["url"]] if items else []

    return {
        "okladka": first("grids", "?dimensions=600x900"),
        "baner": first("heroes"),
        "logo": first("logos"),
    }, None


# --- LaunchBox Games DB (strona WWW, bez klucza). ---
def launchbox(title, platform, keys, screens, products):
    page = http("https://gamesdb.launchbox-app.com/games/results/" + urllib.parse.quote(title)).decode("utf-8", "replace")
    cards = re.findall(r'href="/games/details/(\d+)-[^"]*".*?<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', page, re.S)
    cards = [(gid, html.unescape(t).strip(), html.unescape(p).strip()) for gid, t, p in cards]
    match = (next((c for c in cards if norm(c[1]) == norm(title) and c[2] == platform), None)
             or next((c for c in cards if c[2] == platform), None))
    if not match:
        return {}, "nie znaleziono gry na tej platformie"
    page = http(f"https://gamesdb.launchbox-app.com/games/images/{match[0]}").decode("utf-8", "replace")
    images = []  # (typ, region, url pełnego rozmiaru, szerokość, rozmiar w MB)
    for m in re.finditer(r'href="(https://images\.launchbox-app\.com/[^"]+)"[^>]*?'
                         r'data-title="[^"]*? - (.+?) Image(?: \((.+?)\))?"\s*'
                         r'data-footer="(\d+) x \d+ \w+, ([\d.]+) (KB|MB)', page, re.S):
        mb = float(m.group(5)) / (1024 if m.group(6) == "KB" else 1)
        images.append((html.unescape(m.group(2)), m.group(3) or "", m.group(1), int(m.group(4)), mb))

    def pick(types, min_width, n=1):
        # Najmniejszy plik, który ma jeszcze sensowną rozdzielczość, żeby nie zapychać vaulta.
        items = [i for i in images if i[0] in types]
        big_enough = [i for i in items if i[3] >= min_width] or items
        big_enough.sort(key=lambda i: (REGION_PREF.index(i[1]) if i[1] in REGION_PREF else 99,
                                       types.index(i[0]), i[4] > MAX_MB, i[4]))
        return [i[2] for i in big_enough[:n]]

    return {"okladka": pick(["Box - Front", "Box - Front - Reconstructed"], 500),
            "baner": pick(["Fanart - Background", "Banner"], 1280),
            "logo": pick(["Clear Logo"], 400),
            "screen": pick(["Screenshot - Gameplay"], 960, screens),
            "produkt": [u for t in LB_PRODUCT for u in pick([t], 500)][:products],
            "_launchbox_id": match[0]}, None


# --- Polskie sklepy (Empik, MediaMarkt, x-kom, bez klucza): okładka polskiego wydania. ---
# Media Expert odrzuca skrypty (403 + captcha), więc go nie ma.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
# Platforma -> (słowa, z których jedno musi być w nazwie produktu, słowa wykluczające).
SHOP_PLATFORMS = {"Nintendo Switch 2": (["switch 2", "ns2"], []),
                  "Nintendo Switch": (["switch", "ns", "nsw"], ["switch 2", "ns2"]),
                  "PlayStation 5": (["ps5", "playstation 5"], []), "PlayStation 4": (["ps4", "playstation 4"], []),
                  "PlayStation 3": (["ps3", "playstation 3"], []), "Xbox Series X": (["xbox series", "xsx"], []),
                  "Xbox One": (["xbox one", "xone"], []), "PC": (["pc"], [])}
SHOP_SKIP = ["kod", "klucz", "etui", "pad", "amiibo", "figurka", "dlc", "ladowarka", "konsola"]
SHOP_SPECIAL = ["kolekcjonerska", "collector", "collection", "special", "specjalna", "limited", "steelbook", "bundle", "zestaw", "deluxe"]


def shop_page(url):
    """Zwraca (końcowy URL po przekierowaniach, HTML). Sklepy wymagają nagłówków przeglądarki."""
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept-Language": "pl-PL,pl;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.geturl(), r.read().decode("utf-8", "replace")


def shop_rank(name, title, platform, edition):
    """Ranking kandydata (mniej = lepiej) albo None, gdy to nie ta gra / platforma / edycja."""
    words = " " + re.sub(r"[^a-z0-9]+", " ", name.lower()) + " "
    if norm(title) not in norm(name) or any(f" {w} " in words for w in SHOP_SKIP):
        return None
    need, avoid = SHOP_PLATFORMS.get(platform, ([], []))
    if need and not any(f" {w} " in words for w in need) or any(f" {w} " in words for w in avoid):
        return None
    if edition:
        return 0 if norm(edition) in norm(name) else None
    # bez --edition: zwykłe wydanie przed specjalnymi, polskie przed importem z USA
    return any(w in words for w in SHOP_SPECIAL) * 2 + (" us " in words[:5])


def empik(title, platform, edition, products):
    q = " ".join(filter(None, [title, edition, platform.replace("Nintendo ", "")]))
    url, page = shop_page("https://www.empik.com/szukaj/produkt?q=" + urllib.parse.quote_plus(q))
    redirected = ",multimedia-p" in url  # jeden wynik: Empik od razu otwiera stronę produktu
    links = [url] if redirected else [
        "https://www.empik.com" + h for h in dict.fromkeys(re.findall(r'href="(/[^"/]+,p\d+,multimedia-p)"', page))]
    slug = lambda u: u.rsplit("/", 1)[-1].split(",")[0]
    ranked = sorted((r, i, u) for i, u in enumerate(links)
                    if (r := shop_rank(slug(u), title, platform, edition)) is not None)
    pages = {links[0]: page} if redirected else {}
    if not ranked:
        # Nowości mają tymczasowy adres ("switch-2-nowosc-10"), prawdziwa nazwa jest tylko w <h1> strony produktu.
        for i, u in enumerate(links[:5]):
            pages[u] = pages.get(u) or shop_page(u)[1]
            h1 = html.unescape("".join(re.findall(r"<h1[^>]*>([^<]+)", pages[u])[:1]))
            if (r := shop_rank(slug(u) + " " + h1, title, platform, edition)) is not None:
                ranked.append((r, i, u))
        ranked.sort()
    if not ranked:
        return None
    url = ranked[0][2]
    page = pages.get(url) or shop_page(url)[1]
    url = url.split("?")[0]
    # Galeria produktu: obrazy z jego numerem w ścieżce (inne obrazy na stronie to polecane produkty).
    imgs = list(dict.fromkeys(re.sub(r"/cir/[a-z]/", "/cir/b/", u) for u in
                              re.findall(r'https://ecsmedia\.pl/cir/[a-z]/[^"?\s]+\.webp', page)))
    if not imgs:
        return None
    pid = re.search(r"(\d{12,})/[0-9a-f]+\.webp$", imgs[0])
    imgs = [u for u in imgs if f"{pid.group(1)}/" in u] if pid else imgs[:1]
    return {"okladka": imgs[:1], "produkt": imgs[1:1 + products] if edition else [], "_shop": "Empik", "_shop_url": url}


def mediamarkt(title, platform, edition, products):
    q = " ".join(filter(None, [title, edition, platform.replace("Nintendo ", "")]))
    _, page = shop_page("https://mediamarkt.pl/pl/search.html?query=" + urllib.parse.quote(q))
    items = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if data.get("@type") == "ItemList":
            items += [e["item"] for e in data.get("itemListElement", []) if e.get("item", {}).get("image")]
    ranked = sorted((r, i, it) for i, it in enumerate(items)
                    if (r := shop_rank(it["name"], title, platform, edition)) is not None) if items else []
    if not ranked:
        return None
    it = ranked[0][2]
    return {"okladka": [it["image"] + "?x=1200&y=1200&format=jpg&quality=85"], "_shop": "MediaMarkt", "_shop_url": it["url"]}


def xkom(title, platform, edition, products):
    q = " ".join(filter(None, [title, edition, platform.replace("Nintendo ", "")]))
    _, page = shop_page("https://www.x-kom.pl/szukaj?q=" + urllib.parse.quote(q))
    items = list(dict.fromkeys(re.findall(r'"productLink":"(/p/[^"]+)","photo":\{"url":"([^"]+)"', page)))
    ranked = sorted((r, i, it) for i, it in enumerate(items)
                    if (r := shop_rank(it[0], title, platform, edition)) is not None)
    if not ranked:
        return None
    link, photo = ranked[0][2]
    return {"okladka": [photo], "_shop": "x-kom", "_shop_url": "https://www.x-kom.pl" + link}


def shops_pl(title, platform, keys, screens, products, edition=None):
    errors = []
    # MediaMarkt ma największe okładki (JPG ~740x1200), Empik mniejsze (WebP ~430x700), x-kom z białymi marginesami.
    for shop in (mediamarkt, empik, xkom):
        try:
            found = shop(title, platform, edition, products)
        except Exception as e:  # sklep może zmienić stronę albo zablokować zapytanie
            errors.append(f"{shop.__name__}: {e}")
            continue
        if found:
            return found, None
    return {}, "; ".join(errors) or "nie znaleziono gry w Empik/MediaMarkt/x-kom"


# --- IGDB: okładka, artwork (baner), screeny. Brak logo. ---
def igdb_games(title, platform, keys, fields):
    """Wyszukuje grę w IGDB (Twitch client_credentials). Zwraca listę gier albo None bez kluczy.
    Używane też przez fetch_meta.py."""
    cid, secret = keys.get("IGDB_CLIENT_ID"), keys.get("IGDB_CLIENT_SECRET")
    if not (cid and secret):
        return None
    token = http_json("https://id.twitch.tv/oauth2/token?" + urllib.parse.urlencode(
        {"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}), data=b"")["access_token"]
    where = f" where platforms = ({IGDB_PLATFORMS[platform]});" if platform in IGDB_PLATFORMS else ""
    title_q = title.replace('"', '\\"')
    query = f'search "{title_q}"; fields name,{fields};{where} limit 5;'
    return http_json("https://api.igdb.com/v4/games", data=query.encode(),
                     headers={"Client-ID": cid, "Authorization": f"Bearer {token}"})


def igdb(title, platform, keys, screens, products):
    games = igdb_games(title, platform, keys, "cover.image_id,artworks.image_id,screenshots.image_id")
    if games is None:
        return None, "brak IGDB_CLIENT_ID/SECRET"
    if not games:
        return {}, "nie znaleziono gry"
    g = next((g for g in games if norm(g["name"]) == norm(title)), games[0])
    img = "https://images.igdb.com/igdb/image/upload/{size}/{id}.jpg"
    return {"okladka": [img.format(size="t_cover_big_2x", id=g["cover"]["image_id"])] if g.get("cover") else [],
            "baner": [img.format(size="t_1080p", id=a["image_id"]) for a in g.get("artworks", [])[:1]],
            "screen": [img.format(size="t_1080p", id=s["image_id"]) for s in g.get("screenshots", [])[:screens]]}, None


SOURCES = [("Sklepy PL", shops_pl), ("SteamGridDB", steamgriddb), ("LaunchBox", launchbox), ("IGDB", igdb)]
KIND_ORDER = {
    "okladka": ["Sklepy PL", "LaunchBox", "IGDB", "SteamGridDB"],
    "baner": ["SteamGridDB", "LaunchBox", "IGDB"],
    "logo": ["SteamGridDB", "LaunchBox"],
    "screen": ["LaunchBox", "IGDB"],
    "produkt": ["Sklepy PL", "LaunchBox"],  # sklepy dają zdjęcia produktu tylko z --edition
}


PS_RESIZE = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$p = $env:GRA_IMG; $dst = $env:GRA_OUT; $edge = [double]$env:GRA_EDGE
$ms = New-Object IO.MemoryStream(,[IO.File]::ReadAllBytes($p))
$img = [Drawing.Image]::FromStream($ms)
$scale = [Math]::Min([double]1.0, $edge / [Math]::Max($img.Width, $img.Height))
if ($scale -lt 1 -or $dst -ne $p) {
  $w = [int]($img.Width * $scale); $h = [int]($img.Height * $scale)
  $bmp = New-Object Drawing.Bitmap $w, $h
  $g = [Drawing.Graphics]::FromImage($bmp); $g.InterpolationMode = 'HighQualityBicubic'
  $g.DrawImage($img, 0, 0, $w, $h); $g.Dispose(); $img.Dispose()
  $fmt = if ($dst -like '*.png') { [Drawing.Imaging.ImageFormat]::Png } else { [Drawing.Imaging.ImageFormat]::Jpeg }
  $bmp.Save($dst, $fmt); $bmp.Dispose()
}
"""


def shrink(path, max_edge, dst=None):
    """Zmniejsza obraz do max_edge px (dłuższy bok); z dst zapisuje go pod inną nazwą/formatem.
    Zwraca None albo opis problemu."""
    dst = dst or path
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.load()
            if max(im.size) > max_edge:
                im.thumbnail((max_edge, max_edge))
            if dst.suffix == ".jpg":
                im = im.convert("RGB")
            im.save(dst)
        return None
    except ImportError:
        pass
    if os.name == "nt":
        env = {**os.environ, "GRA_IMG": str(path.resolve()), "GRA_OUT": str(dst.resolve()), "GRA_EDGE": str(max_edge)}
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_RESIZE],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return None if r.returncode == 0 else f"zmniejszanie nieudane: {r.stderr.strip()[:200]}"
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        return "brak Pillow/ImageMagick, plik nie zmniejszony"
    r = subprocess.run([tool, str(path), "-resize", f"{max_edge}x{max_edge}>", str(dst)], capture_output=True)
    return None if r.returncode == 0 else "zmniejszanie nieudane"


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="tytuł do wyszukania (najlepiej angielski)")
    ap.add_argument("--platform", required=True, help='np. "Nintendo Switch"')
    ap.add_argument("--out", required=True, help="folder docelowy w vaulcie")
    ap.add_argument("--name", help="nazwa plików (domyślnie = title)")
    ap.add_argument("--screens", type=int, default=2)
    ap.add_argument("--products", type=int, default=3, help="max zdjęć produktu (tył pudełka, 3D, nośnik)")
    ap.add_argument("--edition", help='wydanie specjalne z "# Notatki", np. "Dagdan Collection"')
    args = ap.parse_args()

    keys = load_keys()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = safe_name(args.name or args.title)
    result, log = {}, {}

    found = {}  # źródło -> {typ: [url]}
    for src_name, fn in SOURCES:
        if fn is shops_pl:
            fn = functools.partial(shops_pl, edition=args.edition)
        try:
            urls, err = fn(args.title, args.platform, keys, args.screens, args.products)
        except Exception as e:  # jedno źródło nie może zatrzymać reszty
            urls, err = {}, f"błąd: {e}"
        if err:
            log[src_name] = err
        found[src_name] = urls or {}

    for kind in KINDS:
        for src_name in KIND_ORDER[kind]:
            urls = found.get(src_name, {})
            if kind in result or not urls.get(kind):
                continue
            picked = list(urls[kind])
            if kind == "screen":  # za mało screenów: dobierz z kolejnych źródeł
                for other in KIND_ORDER[kind]:
                    if other != src_name and len(picked) < args.screens:
                        picked += found.get(other, {}).get(kind, [])[:args.screens - len(picked)]
            files = []
            for i, url in enumerate(picked, 1):
                ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
                suffix = f"{kind}{i}" if kind in ("screen", "produkt") else kind
                path = out / f"{name} - {suffix}{ext}"
                try:
                    path.write_bytes(http(url))
                    # baner nie potrzebuje przezroczystości, a jako PNG potrafi mieć kilka MB
                    dst = path.with_suffix(".jpg") if kind == "baner" and ext == ".png" else path
                    # WebP (Empik) przychodzi już zmniejszony, a System.Drawing go nie czyta
                    problem = None if ext == ".webp" else shrink(path, MAX_EDGE[kind], dst)
                    if dst != path and dst.exists():
                        path.unlink()
                        path = dst
                    files.append(path.name)
                    if problem:
                        log[path.name] = problem
                except Exception as e:
                    log[src_name] = f"pobieranie nieudane: {e}"
            if files:
                result[kind] = {"files": files, "source": src_name}
                if urls.get("_shop"):  # do "## Źródła" w karcie
                    result[kind].update(shop=urls["_shop"], shop_url=urls["_shop_url"])

    result["missing"] = [k for k in KINDS if k not in result]
    result["log"] = log
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
