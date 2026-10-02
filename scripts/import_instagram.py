"""
Import de l'export Instagram → data/restaurants.csv (éditable dans Excel) → data/restaurants.json (lu par le site).

Usage :
    npm run import                 # lit le .zip ou le dossier présent dans data/raw/
    npm run import -- --api        # lit les nouveaux posts via l'API Instagram (variable IG_TOKEN), utilisé par le robot GitHub
    npm run import -- --no-geo     # sans géocodage (hors ligne)
    npm run import -- --csv-only   # ne relit pas l'export : regénère juste le JSON depuis le CSV corrigé

L'export peut être au format JSON ou HTML (les deux choix proposés par Instagram).

Règles :
- Une ligne du CSV = un restaurant. Les lignes existantes ne sont JAMAIS écrasées : tes corrections restent.
  Un nouvel import ajoute seulement les nouveaux restos, et les nouvelles photos des restos déjà connus.
- Colonne `inclure` : mettre `non` pour cacher un post qui n'est pas un resto.
- Colonne `statut` : ce que le script n'a pas su trouver (adresse, position…).
- Si tu modifies une adresse, le resto est re-géocodé au prochain lancement.
- Colonne `position` : d'où vient l'épingle (adresse / nom / gps photo). Quand elle vient du nom,
  vérifie-la sur le site puis écris `vérifiée`. Tu peux aussi saisir lat/lng à la main.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CSV_PATH = ROOT / "data" / "restaurants.csv"
JSON_PATH = ROOT / "data" / "restaurants.json"
GEOCACHE_PATH = ROOT / "data" / "geocache.json"
API_STATE_PATH = ROOT / "data" / "instagram_state.json"  # date du dernier post déjà traité
API_CACHE = RAW / "api"  # photos téléchargées depuis l'API (jamais publiées telles quelles)
PHOTOS_DIR = ROOT / "public" / "photos"

COLUMNS = [
    "slug", "inclure", "statut", "nom", "note", "cuisine", "prix", "adresse", "autres_adresses", "ville",
    "arrondissement", "lat", "lng", "date", "avis", "instagram_resto", "lien_instagram", "photos", "position",
    "adresse_geocodee", "sources_export",
]
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic")
USER_AGENT = "food-site-import/1.0 (site perso de critiques de restaurants)"

CUISINES = {
    "francaise": "Français", "francais": "Français", "frenchfood": "Français", "frenchrestaurant": "Français",
    "bistronomie": "Français", "frenchbistro": "Français",
    "brasserie": "Brasserie", "brasserieparisienne": "Brasserie", "bistrot": "Bistrot", "bistro": "Bistrot",
    "bistrotparisien": "Bistrot",
    "italien": "Italien", "italienne": "Italien", "italian": "Italien", "italianfood": "Italien",
    "italianrestaurant": "Italien", "restaurantitalien": "Italien", "trattoria": "Italien", "pasta": "Italien",
    "pates": "Italien", "pizza": "Italien",
    "japonais": "Japonais", "japonaise": "Japonais", "japanese": "Japonais", "japanesefood": "Japonais", "sushi": "Japonais",
    "maki": "Japonais", "ramen": "Japonais", "izakaya": "Japonais",
    "chinois": "Chinois", "chinoise": "Chinois", "chinese": "Chinois", "chinesefood": "Chinois",
    "dimsum": "Chinois", "dimsums": "Chinois",
    "coreen": "Coréen", "korean": "Coréen", "thai": "Thaï", "thaifood": "Thaï", "thailandais": "Thaï",
    "vietnamien": "Vietnamien", "pho": "Vietnamien", "taiwanais": "Taïwanais", "francotaiwanais": "Taïwanais",
    "asianfusion": "Asiatique", "asiatique": "Asiatique",
    "indien": "Indien", "indian": "Indien", "libanais": "Libanais", "lebanese": "Libanais",
    "turc": "Turc", "turkish": "Turc", "turkishfood": "Turc", "israelienne": "Israélien",
    "mediterraneen": "Méditerranéen", "mediterraneenne": "Méditerranéen", "mediterranean": "Méditerranéen",
    "mexicain": "Mexicain", "mexican": "Mexicain", "tacos": "Mexicain", "sudamericain": "Sud-américain",
    "peruvien": "Péruvien", "grec": "Grec", "africain": "Africain",
    "tapas": "Tapas", "tapasbar": "Tapas",
    "burger": "Burger", "burgers": "Burger", "brunch": "Brunch",
    "matcha": "Matcha & café", "coffeeshop": "Matcha & café", "cafe": "Matcha & café",
    "winebar": "Bar à vin", "naturalwinebar": "Bar à vin", "vinnaturel": "Bar à vin",
    "cocktails": "Bar à cocktails", "cocktailsbar": "Bar à cocktails",
    "gastronomique": "Gastronomique", "gastro": "Gastronomique", "michelinstar": "Gastronomique",
    "patisserie": "Pâtisserie", "boulangerie": "Boulangerie", "bakery": "Boulangerie",
    "streetfood": "Street food", "foodmarket": "Food market",
    "vegan": "Végétarien", "vegetarien": "Végétarien",
}
# Dernier recours : l'émoji placé à côté du nom.
EMOJI_CUISINES = {
    "🍝": "Italien", "🍕": "Italien", "🍣": "Japonais", "🍱": "Japonais", "🥟": "Chinois", "🥢": "Asiatique",
    "🍜": "Asiatique", "🍛": "Indien", "🌮": "Mexicain", "🥩": "Viande", "🧆": "Méditerranéen",
    "🥞": "Brunch", "🍳": "Brunch", "🥯": "Brunch", "🥐": "Boulangerie", "🍵": "Matcha & café", "☕": "Matcha & café",
    "🍷": "Français", "🍸": "Bar à cocktails",
}

# Villes reconnues dans les adresses et les légendes (nom affiché sur le site).
CITIES = [
    (r"paris", "Paris"), (r"london|londres", "London"), (r"madrid", "Madrid"),
    (r"ciudad de m[ée]xico|mexico city|cdmx|polanco|roma norte", "Mexico City"), (r"tulum", "Tulum"),
    (r"lombok", "Lombok"), (r"vaux de cernay", "Cernay-la-Ville"),
]
# Pas d'API Adresse (France uniquement) pour ces villes : on passe directement par OpenStreetMap.
FOREIGN_CITIES = {"London", "Madrid", "Mexico City", "Tulum", "Lombok"}

STREET = (r"(?:rue|avenue|av\.?|boulevard|bd|place|pl\.?|quai|passage|impasse|all[ée]e|cours|chemin|route|square|"
          r"villa|cit[ée]|faubourg|fbg|road|rd|street|st|lane|gardens|mews|row|court|calle|c\.|avenida|plaza|paseo|"
          r"costanilla|corredera)")
ADDRESS_RE = re.compile(
    rf"(\d{{1,4}}\s?(?:bis|ter)?,?\s+{STREET}\b[^\n,]*?(?:,\s*|\s+)\d{{5}}(?:\s+[A-Za-zÀ-ÿ' -]+)?)", re.I
)
STREET_ONLY_RE = re.compile(rf"(\d{{1,4}}\s?(?:bis|ter)?,?\s+{STREET}\b[^\n]*)", re.I)
RATING_RE = re.compile(r"(\d(?:[.,]\d{1,2})?)\s*/\s*5(?!\d)")
# Étoiles comptées seulement après « note : » (sinon ⭐️⭐️⭐️ désigne souvent les étoiles Michelin).
STAR_RE = re.compile(r"(?:note|rating|score)\s*:?\s*((?:[⭐★🌟]\ufe0f?)+)\s*(½|\.5|,5)?", re.I)
PRICE_RE = re.compile(r"(?<![\w€])(?<!\d )(€{1,4})(?![\w€])")  # « €€ », mais pas le « € » de « 34 € »
LOC_RE = re.compile(r"^\s*(?:📍|🔍|🔎)\s*(.*)$")
SUB_RE = re.compile(r"^\s*[-•–]\s+(.+)$")
MENTION_RE = re.compile(r"@([\w.]*\w)")
HASHTAG_RE = re.compile(r"#[\wÀ-ÿ]+")
ARR_RE = re.compile(r"\b(?:paris\s*)?(\d{1,2})\s*(?:e|er|ème|eme|ᵉ)\b", re.I)

OWN_HANDLE = ""  # le compte qui a fait l'export : ses @mentions ne désignent pas le resto


# ---------- utilitaires ----------

def fix_text(s: str) -> str:
    """Les exports Instagram JSON encodent l'UTF-8 comme du latin-1 (Ã© au lieu de é)."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "resto"


def strip_emoji(s: str) -> str:
    return "".join(c for c in s if unicodedata.category(c)[0] in "LNPZ" or c in "&'’-").strip(" -–—|·,")


def arrondissement_from(postcode: str | None) -> int | None:
    if postcode and re.fullmatch(r"750\d\d", postcode):
        n = int(postcode[-2:])
        return n if 1 <= n <= 20 else None
    if postcode == "75116":
        return 16
    return None


def looks_like_address(s: str) -> bool:
    """Adresse avec numéro : « 8 rue Levert, 75020 Paris », « Calle de Caracas 21, Madrid » oui ;
    « Paris 16ème », « Rue Cler, Paris 7e » ou « Mayfair, London » non."""
    return bool(re.search(r"\b\d{5}\b", s) or re.search(r"\d+[a-z]?,", s, re.I)
                or re.match(r"\s*\d{1,4}[a-z]?(?:-\d+)?,?\s+(?!(?:e|er|ème|eme|ᵉ)\b)[^\W\d]", s, re.I))


def detect_city(*texts: str) -> str:
    for text in texts:
        hits = [(m.start(), city) for pat, city in CITIES for m in [re.search(rf"\b(?:{pat})\b", text, re.I)] if m]
        if hits:
            return min(hits)[1]
    return ""


def price_level(text: str) -> str:
    """Ordre de grandeur à partir des lignes de prix (« ~ plats de 16 à 48€ ») : € < 15, €€ < 30, €€€ < 50."""
    lines = [l for l in text.split("\n") if re.search(r"[€£]", l) and re.search(r"\d", l)]
    if not lines:
        return ""
    mains = [l for l in lines if re.search(r"plat|main|assiette|plate|pasta|pizza|dish", l, re.I)]
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", (mains or lines)[0])]
    nums = [n for n in nums if 1 <= n < 500]
    if not nums:
        return ""
    v = (min(nums) + max(nums)) / 2
    return "€" if v < 15 else "€€" if v < 30 else "€€€" if v < 50 else "€€€€"


# ---------- lecture de l'export ----------

def find_export() -> Path:
    zips = sorted(RAW.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if zips:
        target = RAW / zips[0].stem
        if not target.exists():
            print(f"Décompression de {zips[0].name}…")
            with zipfile.ZipFile(zips[0]) as z:
                z.extractall(target)
        return target
    dirs = [d for d in RAW.iterdir() if d.is_dir()] if RAW.exists() else []
    if dirs:
        return max(dirs, key=lambda p: p.stat().st_mtime)
    sys.exit(f"Aucun export trouvé dans {RAW}. Dépose le .zip Instagram dans ce dossier.")


HTML_MONTHS = {
    "jan": 1, "janv": 1, "feb": 2, "fev": 2, "fév": 2, "févr": 2, "mar": 3, "mars": 3, "apr": 4, "avr": 4,
    "may": 5, "mai": 5, "jun": 6, "juin": 6, "jul": 7, "juil": 7, "aug": 8, "aoû": 8, "aou": 8, "août": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12,
}
HTML_DATE_RE = re.compile(r">\s*([a-zéû]{3,5})\.?\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap]m)?\s*<", re.I)


def load_posts_html(export: Path, files: list[Path]) -> list[dict]:
    posts = []
    for f in files:
        page = f.read_text(encoding="utf-8")
        for block in re.split(r'<div class="pam [^"]*uiBoxWhite[^"]*">', page)[1:]:
            h = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
            caption = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", "\n", h.group(1)))) if h else ""
            srcs = [html.unescape(u) for u in re.findall(r'<img src="([^"]+)"', block)]
            images = [export / u for u in srcs if u.startswith("media/") and u.lower().endswith(IMAGE_EXT)]
            if not images:
                continue
            ts = 0
            d = HTML_DATE_RE.search(block)
            if d and d.group(1).lower() in HTML_MONTHS:
                hour = int(d.group(4)) % 12 + (12 if (d.group(6) or "").lower() == "pm" else 0)
                if not d.group(6):
                    hour = int(d.group(4))
                ts = datetime(int(d.group(3)), HTML_MONTHS[d.group(1).lower()], int(d.group(2)), hour,
                              int(d.group(5)), tzinfo=timezone.utc).timestamp()
            posts.append({"caption": caption, "ts": ts, "images": images, "exif_geo": None})
    return posts


def load_posts(export: Path) -> list[dict]:
    global OWN_HANDLE
    m = re.match(r"instagram-(.+?)-\d{4}-\d{2}-\d{2}", export.name)
    OWN_HANDLE = m.group(1).lower() if m else ""

    files = sorted(export.rglob("posts_*.json"))
    html_files = sorted(export.rglob("posts_*.html"))
    if not files and not html_files:
        sys.exit(f"Pas de posts_*.json ni posts_*.html dans {export}. L'export contient-il bien tes publications ?")
    if not files:
        posts = load_posts_html(export, html_files)
        print(f"{len(posts)} posts lus dans {len(html_files)} fichier(s) HTML.")
        return posts

    posts = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        for item in data:
            media = item.get("media", [])
            if not media:
                continue
            caption = fix_text(item.get("title") or media[0].get("title") or "")
            ts = item.get("creation_timestamp") or media[0].get("creation_timestamp") or 0
            geo = None
            for m in media:
                for ex in (m.get("media_metadata", {}).get("photo_metadata", {}).get("exif_data") or []):
                    if ex.get("latitude") and ex.get("longitude"):
                        geo = (float(ex["latitude"]), float(ex["longitude"]))
            images = [export / m["uri"] for m in media if m.get("uri", "").lower().endswith(IMAGE_EXT)]
            posts.append({"caption": caption, "ts": ts, "images": images, "exif_geo": geo})
    print(f"{len(posts)} posts lus dans {len(files)} fichier(s).")
    return posts


# ---------- extraction depuis la légende ----------

def parse_caption(caption: str) -> dict:
    """Format attendu (souple) : « Nom 🍝 @compte », l'avis, des lignes 📍 (adresses ou quartiers),
    des lignes de prix « ~ … », puis les hashtags."""
    text = caption.strip()
    out: dict = {"rating": None, "name": None, "address": None, "others": [], "price": None, "cuisine": None,
                 "arr": None, "handle": None, "city": ""}
    lines = text.split("\n")

    # 1. Nom sur la première ligne, avant le @compte ou le 📍. Le reste de la ligne est rendu à l'avis.
    first = lines[0].strip() if lines else ""
    bare = re.sub(r"^(?:📍|🔍|🔎)\s*", "", first)
    if bare.startswith("@"):
        h = MENTION_RE.match(bare)
        out["name"] = h.group(1).replace("_", " ").replace(".", " ").strip().title()
        rest = bare[h.end():]
    else:
        cut = re.split(r"@|📍|\s[–—|-]\s", bare, maxsplit=1)[0]
        name = strip_emoji(cut)
        if name and len(name) <= 40:
            out["name"] = name
            rest = bare[len(cut):]
        else:
            rest = first
    rest = MENTION_RE.sub("", rest, count=1) if rest.lstrip().startswith("@") else rest
    rest = rest.strip(" –—|-")
    lines = ([rest] if strip_emoji(rest) else []) + lines[1:]

    # 2. Blocs 📍 (et leurs sous-lignes « - … ») : adresse principale + autres adresses.
    kept, locs = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = LOC_RE.match(line)
        if m:
            if kept and kept[-1].strip().endswith(":") and len(kept[-1]) < 60:
                kept.pop()  # « Trois adresses parisiennes : »
            head = m.group(1).strip()
            if head and not head.endswith((":", "?")):
                locs.append(head)
            while i + 1 < len(lines) and SUB_RE.match(lines[i + 1]):
                i += 1
                locs.append(SUB_RE.match(lines[i]).group(1).strip())
        elif re.fullmatch(r"\s*@[\w.]+\s*", line) or re.fullmatch(r"\s*[.…]+\s*", line):
            pass  # ligne réduite au @compte (affiché à part) ou séparateur « . »
        else:
            kept.append(line)
        i += 1
    locs = [re.sub(r"^[^:\d]{2,40}:\s*(?=\d)", "", l) for l in locs]  # « Kinugawa Rive Gauche : 55 avenue… »
    for loc in locs:
        if not out["address"] and looks_like_address(loc):
            out["address"] = loc
        else:
            out["others"].append(loc)
    if not out["name"] and locs and not out["address"]:
        out["name"] = strip_emoji(re.split(r"[,–—|]", locs[0])[0])
    if not out["address"]:
        m = ADDRESS_RE.search(text) or STREET_ONLY_RE.search(text)
        if m:
            out["address"] = m.group(1).strip(" .")

    handles = [h for h in MENTION_RE.findall(text) if h.lower() != OWN_HANDLE]
    out["handle"] = handles[0] if handles else None
    if not out["name"] and out["handle"]:
        out["name"] = out["handle"].replace("_", " ").replace(".", " ").strip().title()

    m = RATING_RE.search(text)
    if m:
        out["rating"] = float(m.group(1).replace(",", "."))
    else:
        m = STAR_RE.search(text)
        if m:
            out["rating"] = len(re.findall("[⭐★🌟]", m.group(1))) + (0.5 if m.group(2) else 0)
    if out["rating"] is not None and not 0 <= out["rating"] <= 5:
        out["rating"] = None

    pc = re.search(r"\b75\d{3}\b", out["address"] or "")
    m = ARR_RE.search(" ".join(locs) + "\n" + text)
    if pc:
        out["arr"] = arrondissement_from(pc.group(0))
    elif m and 1 <= int(m.group(1)) <= 20:
        out["arr"] = int(m.group(1))

    m = PRICE_RE.search(text)
    out["price"] = m.group(1) if m else price_level(text)
    out["city"] = detect_city(out["address"] or "", " ".join(locs), HASHTAG_RE.sub("", text))

    tags = [slugify(h[1:]).replace("-", "") for h in HASHTAG_RE.findall(text)]
    words = [slugify(w).replace("-", "") for w in re.findall(r"[\wÀ-ÿ]+", HASHTAG_RE.sub("", text))]
    out["cuisine"] = next((CUISINES[w] for w in words + tags if w in CUISINES), None) \
        or next((c for e, c in EMOJI_CUISINES.items() if e in first), None)

    # Avis = légende sans hashtags, sans la note ni les lignes 📍 (affichées à part).
    review = HASHTAG_RE.sub("", "\n".join(kept))
    review = RATING_RE.sub("", review)
    review = STAR_RE.sub("", review)
    review = PRICE_RE.sub("", review)
    review = "\n".join(l for l in review.split("\n") if not l.strip() or re.search(r"\w", l))  # « 📈 » resté seul
    review = "\n".join(l for l in review.split("\n") if l.strip() == "" or not re.fullmatch(r"\s*(?:ma\s+)?(?:note|rating|score)?\s*:?\s*", l, re.I))
    review = re.sub(r"[ \t]+\n", "\n", review)
    out["review"] = re.sub(r"\n{3,}", "\n\n", review).strip(" \n-–—|·")
    return out


# ---------- géocodage ----------

def http_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


class Geocoder:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.cache = json.loads(GEOCACHE_PATH.read_text()) if GEOCACHE_PATH.exists() else {}
        self.last_nominatim = 0.0
        self.ban_down = False

    def save(self):
        GEOCACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # Géoplateforme IGN (successeur de l'API Adresse), puis l'API Adresse historique en secours.
    BAN_URLS = ("https://data.geopf.fr/geocodage/search?", "https://api-adresse.data.gouv.fr/search/?")

    def ban(self, q: str) -> dict | None:
        """Adresse postale française → coordonnées. Une erreur réseau n'est jamais mise en cache."""
        key = f"ban:{q}"
        if key not in self.cache and self.enabled and not self.ban_down:
            data, last_err = None, None
            for base in self.BAN_URLS:
                try:
                    data = http_json(base + urllib.parse.urlencode({"q": q, "limit": 1}))
                    break
                except Exception as e:
                    last_err = e
            if data is None:
                print(f"  ! API Adresse injoignable ({last_err}) : repli sur OpenStreetMap")
                self.ban_down = True
                return None
            f = (data.get("features") or [None])[0]
            self.cache[key] = None if not f or f["properties"]["score"] < 0.5 else {
                "lat": f["geometry"]["coordinates"][1], "lng": f["geometry"]["coordinates"][0],
                "postcode": f["properties"].get("postcode"), "city": f["properties"].get("city"),
                "label": f["properties"].get("label"),
            }
        return self.cache.get(key)

    def osm(self, q: str, places_only: bool) -> dict | None:
        """Nominatim (OpenStreetMap). Max 1 requête/seconde."""
        key = f"osm:{q}" if places_only else f"osmaddr:{q}"
        if key not in self.cache and self.enabled:
            wait = 1.1 - (time.time() - self.last_nominatim)
            if wait > 0:
                time.sleep(wait)
            try:
                data = http_json("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
                    {"q": q, "format": "jsonv2", "limit": 1, "addressdetails": 1}))
                self.last_nominatim = time.time()
                hit = data[0] if data else None
                if places_only and hit and hit.get("category") not in ("amenity", "shop", "tourism", "leisure"):
                    hit = None  # on a trouvé une rue ou une ville, pas un resto
                a = (hit or {}).get("address", {})
                self.cache[key] = None if not hit else {
                    "lat": float(hit["lat"]), "lng": float(hit["lon"]), "postcode": a.get("postcode"),
                    "city": a.get("city") or a.get("town") or a.get("village"),
                    "label": ", ".join(x for x in [" ".join(filter(None, [a.get("house_number"), a.get("road")])),
                                                     " ".join(filter(None, [a.get("postcode"), a.get("city") or a.get("town")]))] if x),
                }
            except Exception as e:
                print(f"  ! géocodage OpenStreetMap échoué pour « {q} » : {e}")
                return None
        return self.cache.get(key)

    def address(self, q: str, city: str = "") -> dict | None:
        """Adresse postale : API Adresse en France, OpenStreetMap à l'étranger ou en secours."""
        hit = None if city in FOREIGN_CITIES else self.ban(q)
        if hit is None:
            full = q if not city or city.lower() in q.lower() else f"{q}, {city}"
            hit = self.osm(full, places_only=False)
        return hit

    def place(self, name: str, hint: str = "Paris") -> dict | None:
        """Recherche par nom de lieu."""
        return self.osm(f"{name}, {hint}", places_only=True)


# ---------- photos ----------

def convert_photos(slug: str, images: list[Path], start: int) -> list[str]:
    out_dir = PHOTOS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, src in enumerate(images, start=start):
        if not src.exists():
            print(f"  ! photo introuvable : {src}")
            continue
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                full = im.copy()
                full.thumbnail((1200, 1200))
                full.save(out_dir / f"{i}.webp", "WEBP", quality=82)
                side = min(im.size)
                thumb = ImageOps.fit(im, (side, side)).resize((480, 480), Image.LANCZOS)
                thumb.save(out_dir / f"{i}-thumb.webp", "WEBP", quality=78)
            paths.append(f"photos/{slug}/{i}.webp")
        except Exception as e:
            print(f"  ! photo illisible {src.name} : {e}")
    return paths


# ---------- CSV ----------

def read_csv() -> dict[str, dict]:
    if not CSV_PATH.exists():
        return {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return {r["slug"]: {c: (r.get(c) or "").strip() for c in COLUMNS} for r in csv.DictReader(f, delimiter=";") if r.get("slug")}


def write_csv(rows: dict[str, dict]):
    ordered = sorted(rows.values(), key=lambda r: r["date"], reverse=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig + ";" : s'ouvre proprement dans Excel FR
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=";")
        w.writeheader()
        w.writerows(ordered)


# ---------- étapes ----------

def merge_export(rows: dict[str, dict], posts: list[dict], export: Path) -> tuple[int, int]:
    added = updated = 0
    groups: dict[str, list[tuple[dict, dict]]] = {}
    for p in sorted(posts, key=lambda p: p["ts"]):
        info = parse_caption(p["caption"])
        name = info["name"] or f"Post du {datetime.fromtimestamp(p['ts'], timezone.utc):%d-%m-%Y}"
        groups.setdefault(slugify(name), []).append((p, {**info, "name": name}))

    # Un resto renommé dans le CSV (nom ou slug) est retrouvé grâce à ses photos.
    by_photo = {Path(s).name: slug for slug, r in rows.items() for s in r["sources_export"].split("|") if s}

    for slug, items in groups.items():
        latest_post, latest = items[-1]
        all_images = [img for p, _ in items for img in p["images"]]
        sources = "|".join(str(img.relative_to(export)) for img in all_images)
        slug = next((by_photo[img.name] for img in all_images if img.name in by_photo), slug)
        if slug in rows:
            # Resto connu : on n'ajoute que les nouvelles photos, sans toucher aux corrections.
            row = rows[slug]
            if len(all_images) > len(list(filter(None, row["sources_export"].split("|")))):
                row["sources_export"] = sources
                row["date"] = max(row["date"], datetime.fromtimestamp(latest_post["ts"], timezone.utc).date().isoformat())
                updated += 1
            continue

        def pick(field):
            return next((i[field] for _, i in reversed(items) if i[field]), None)

        rating = next((i["rating"] for _, i in reversed(items) if i["rating"] is not None), None)
        is_review = rating is not None or any(i["address"] or i["others"] or "📍" in p["caption"] for p, i in items)
        rows[slug] = {
            "slug": slug,
            "inclure": "oui" if is_review else "non",
            "statut": "",
            "nom": latest["name"],
            "note": "" if rating is None else f"{rating:g}".replace(".", ","),
            "cuisine": pick("cuisine") or "",
            "prix": pick("price") or "",
            "adresse": pick("address") or "",
            "autres_adresses": " · ".join(pick("others") or []),
            "ville": pick("city") or "",
            "arrondissement": str(pick("arr") or ""),
            "position": "gps photo" if latest_post["exif_geo"] else "",
            "lat": f"{latest_post['exif_geo'][0]:.6f}" if latest_post["exif_geo"] else "",
            "lng": f"{latest_post['exif_geo'][1]:.6f}" if latest_post["exif_geo"] else "",
            "date": datetime.fromtimestamp(latest_post["ts"], timezone.utc).date().isoformat(),
            "avis": "\n\n".join(i["review"] for _, i in reversed(items) if i["review"]),
            "instagram_resto": pick("handle") or "",
            "lien_instagram": latest_post.get("permalink", ""),
            "photos": "",
            "adresse_geocodee": "",
            "sources_export": sources,
        }
        added += 1
    return added, updated


def sync_photos(rows: dict[str, dict], export: Path | None):
    """Convertit les photos des seuls restos inclus : un post exclu n'a jamais ses photos publiées."""
    for r in rows.values():
        if r["inclure"].lower() == "non":
            continue
        sources = [export / s for s in filter(None, r["sources_export"].split("|"))] if export else []
        current = [p for p in r["photos"].split("|") if p]
        generated = [p for p in current if p.startswith(f"photos/{r['slug']}/")]
        if len(sources) > len(generated):
            current += convert_photos(r["slug"], sources[len(generated):], start=len(generated))
        r["photos"] = "|".join(current)


def geocode_rows(rows: dict[str, dict], geo: Geocoder) -> int:
    done = 0
    for r in rows.values():
        if r["inclure"].lower() == "non":
            continue
        changed_address = r["adresse"] and r["adresse"] != r["adresse_geocodee"]
        if r["lat"] and r["lng"] and not changed_address:
            continue
        hit, source = None, ""
        if r["adresse"] and looks_like_address(r["adresse"]):
            # Adresse précise : on ne devine JAMAIS par le nom (risque d'homonyme ailleurs).
            hit, source = geo.address(r["adresse"], r["ville"]), "adresse"
        else:
            # Pas d'adresse, ou seulement un quartier (« Salamanca, Madrid ») : on cherche le resto par son nom.
            hint = r["adresse"] or (f"Paris {r['arrondissement']}e" if r["arrondissement"] and r["ville"] in ("", "Paris") else (r["ville"] or "Paris"))
            if r["ville"] and r["ville"].lower() not in hint.lower():
                hint = f"{hint}, {r['ville']}"
            hit, source = geo.place(r["nom"], hint), "nom"
            if hit and r["arrondissement"] and arrondissement_from(hit.get("postcode")) not in (None, int(r["arrondissement"])):
                print(f"  ! « {r['nom']} » trouvé dans le {hit['postcode']} alors que la légende dit {r['arrondissement']}e : ignoré")
                hit = None
            if not hit and r["adresse"]:
                hit, source = geo.address(r["adresse"], r["ville"]), "quartier"
        if hit:
            r["position"] = source
            r["lat"], r["lng"] = f"{hit['lat']:.6f}", f"{hit['lng']:.6f}"
            if not r["adresse"] and hit.get("label"):
                r["adresse"] = hit["label"]
            r["ville"] = r["ville"] or (hit.get("city") or "")
            # Le code postal écrit dans l'adresse prime sur celui renvoyé par le géocodeur.
            pc = re.search(r"\b75\d{3}\b", r["adresse"])
            arr = arrondissement_from(pc.group(0) if pc else hit.get("postcode"))
            if arr and (pc or not r["arrondissement"]):
                r["arrondissement"] = str(arr)
            r["adresse_geocodee"] = r["adresse"]
            done += 1
    geo.save()
    return done


def refresh_status(rows: dict[str, dict]):
    for r in rows.values():
        issues = []
        if r["inclure"].lower() == "non":
            issues.append("exclu (pas de lieu : est-ce un resto ?)")
        else:
            if not r["adresse"]:
                issues.append("adresse manquante")
            if not (r["lat"] and r["lng"]):
                issues.append("pas sur la carte")
            elif r["position"] == "nom":
                issues.append("position devinée par le nom : vérifie l'adresse puis mets « vérifiée » dans position")
            elif r["position"] == "quartier":
                issues.append("épingle approximative (centre du quartier) : saisis lat/lng puis mets « vérifiée » dans position")
            if not r["photos"]:
                issues.append("pas de photo (non publié)")
            if r["nom"].startswith("Post du "):
                issues.append("nom à renseigner")
        r["statut"] = " ; ".join(issues) or "ok"


def to_float(s: str) -> float | None:
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def write_json(rows: dict[str, dict]) -> int:
    out = []
    for r in rows.values():
        if r["inclure"].lower() == "non" or not r["photos"]:
            continue
        arr = int(r["arrondissement"]) if r["arrondissement"].isdigit() else None
        ville = r["ville"] or ("Paris" if arr else "")
        out.append({
            "slug": r["slug"], "name": r["nom"], "address": r["adresse"], "city": ville,
            "arrondissement": arr if ville in ("", "Paris") else None,
            "other_addresses": [a.strip() for a in r["autres_adresses"].split("·") if a.strip()],
            "lat": to_float(r["lat"]), "lng": to_float(r["lng"]), "rating": to_float(r["note"]),
            "review": r["avis"], "cuisine": r["cuisine"] or None, "price": r["prix"] or None,
            "date": r["date"], "photos": r["photos"].split("|"), "instagram_url": r["lien_instagram"] or None,
            "instagram_handle": r["instagram_resto"].lstrip("@") or None,
        })
    JSON_PATH.write_text(json.dumps({"demo": False, "restaurants": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(out)


# ---------- API Instagram (robot GitHub) ----------

def load_posts_api(token: str, ignore: set[str]) -> tuple[list[dict], list[dict]]:
    """Tous les posts du compte via l'API Instagram. Renvoie (nouveaux posts, tous les posts).
    Nouveau = publié après la date enregistrée dans data/instagram_state.json et pas refusé."""
    state = json.loads(API_STATE_PATH.read_text()) if API_STATE_PATH.exists() else {}
    since = state.get("last_timestamp", "")
    fields = "id,caption,media_type,media_url,permalink,timestamp,children{id,media_type,media_url}"
    url = "https://graph.instagram.com/me/media?" + urllib.parse.urlencode({"fields": fields, "limit": 50, "access_token": token})
    items = []
    while url:
        data = http_json(url)
        items += data.get("data", [])
        url = data.get("paging", {}).get("next")
    print(f"{len(items)} posts sur le compte (API).")

    API_CACHE.mkdir(parents=True, exist_ok=True)
    new = []
    for it in items:
        if it["timestamp"] <= since or it["id"] in ignore:
            continue
        media = it.get("children", {}).get("data") or [it]
        images = []
        for m in media:
            if m.get("media_type") != "IMAGE" or not m.get("media_url"):
                continue  # vidéos ignorées, comme pour l'export
            dest = API_CACHE / f"{m['id']}.jpg"
            if not dest.exists():
                req = urllib.request.Request(m["media_url"], headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dest.write_bytes(r.read())
            images.append(dest)
        if images:
            new.append({"id": it["id"], "caption": it.get("caption") or "", "images": images, "exif_geo": None,
                        "ts": datetime.strptime(it["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp(),
                        "permalink": it.get("permalink", "")})
    if items:
        state["last_timestamp"] = max(state.get("last_timestamp", ""), max(it["timestamp"] for it in items))
    API_STATE_PATH.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    return new, items


def fill_links(rows: dict[str, dict], items: list[dict]) -> int:
    """Remplit « lien_instagram » des restos déjà connus (l'export ne donne pas les liens des posts)."""
    done = 0
    for it in items:
        if not it.get("permalink"):
            continue
        day = datetime.strptime(it["timestamp"], "%Y-%m-%dT%H:%M:%S%z").date()
        slug = slugify(parse_caption(it.get("caption") or "")["name"] or "")
        free = [r for r in rows.values() if not r["lien_instagram"] and r["date"]]
        near = [r for r in free if abs((datetime.fromisoformat(r["date"]).date() - day).days) <= 1]
        same_day = [r for r in free if r["date"] == day.isoformat()]
        match = next((r for r in near if r["slug"] == slug), None) or (same_day[0] if len(same_day) == 1 else None)
        if match:
            match["lien_instagram"] = it["permalink"]
            done += 1
    return done


def write_summary(path: str, rows: dict[str, dict], new_slugs: list[str], posts: list[dict], links: int):
    """Texte de la demande de validation (pull request) ouverte par le robot."""
    repo, branch = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("ROBOT_BRANCH", "robot/nouveaux-posts")
    lines = []
    if new_slugs:
        lines += [f"## {len(new_slugs)} nouveau(x) resto(s) à valider", ""]
        for slug in new_slugs:
            r = rows[slug]
            img = f"https://raw.githubusercontent.com/{repo}/{branch}/public/photos/{slug}/0-thumb.webp"
            facts = " · ".join(x for x in [r["ville"], r["cuisine"], r["prix"]] if x)
            lines += [f"### {r['nom']}", "",
                      f'<img src="{img}" width="160" align="right">' if r["photos"] else "",
                      f"- **Où** : {r['adresse'] or '—'} {f'({facts})' if facts else ''}",
                      f"- **Post** : {r['lien_instagram'] or '—'}",
                      f"- **À vérifier** : {r['statut']}" if r["statut"] != "ok" else "- **À vérifier** : rien, tout a été trouvé",
                      "", "> " + r["avis"][:300].replace("\n", "\n> "), "", '<br clear="right">', ""]
    if links:
        lines += [f"{links} lien(s) « Voir le post » ajouté(s) aux restos déjà publiés.", ""]
    lines += ["---",
              "**Valider** : bouton « Merge pull request » → le site est mis à jour 2 minutes après.  ",
              "**Corriger avant** : onglet « Files changed » → `data/restaurants.csv` → « Edit file ».  ",
              "**Refuser** : « Close pull request » → ces posts ne seront plus proposés.", "",
              f"<!-- ids: {','.join(p['id'] for p in posts)} -->"]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-geo", action="store_true", help="ne pas appeler les API de géocodage")
    ap.add_argument("--csv-only", action="store_true", help="ne pas relire l'export, juste CSV → JSON")
    ap.add_argument("--api", action="store_true", help="nouveaux posts via l'API Instagram (variable IG_TOKEN)")
    ap.add_argument("--ignore-ids", default="", help="posts refusés (identifiants séparés par des virgules)")
    ap.add_argument("--summary", help="fichier où écrire le résumé des nouveautés (pour la pull request)")
    args = ap.parse_args()

    rows = read_csv()
    added = updated = 0
    posts = []
    if args.api:
        token = os.environ.get("IG_TOKEN") or sys.exit("Variable IG_TOKEN absente : clé d'accès Instagram manquante.")
        posts, items = load_posts_api(token, set(filter(None, args.ignore_ids.split(","))))
        before = set(rows)
        added, updated = merge_export(rows, posts, API_CACHE)
        sync_photos(rows, API_CACHE)
        links = fill_links(rows, items)
        new_slugs = [s for s in rows if s not in before]
    elif not args.csv_only:
        export = find_export()
        posts = load_posts(export)
        added, updated = merge_export(rows, posts, export)
        sync_photos(rows, export)
    if args.csv_only and any(r["inclure"].lower() != "non" and not r["photos"] for r in rows.values()):
        try:
            export = find_export()
        except SystemExit:
            export = None
        sync_photos(rows, export)  # resto ré-inclus à la main dans le CSV
    geocoded = geocode_rows(rows, Geocoder(enabled=not args.no_geo))
    refresh_status(rows)
    write_csv(rows)
    published = write_json(rows)
    if args.api and args.summary and (new_slugs or links):
        write_summary(args.summary, rows, new_slugs, posts, links)

    flagged = [r for r in rows.values() if r["statut"] != "ok"]
    print("\n── Rapport ──")
    if posts:
        print(f"Posts lus            : {len(posts)}")
    print(f"Restaurants (CSV)    : {len(rows)}  (+{added} nouveaux, {updated} avec nouvelles photos)")
    print(f"Géocodés ce lancement: {geocoded}")
    print(f"Sur la carte         : {sum(1 for r in rows.values() if r['lat'] and r['inclure'].lower() != 'non')}")
    print(f"Publiés sur le site  : {published}")
    print(f"À vérifier           : {len(flagged)}  → ouvre data/restaurants.csv, colonne « statut »")
    for r in flagged[:15]:
        print(f"   - {r['nom']}: {r['statut']}")
    if len(flagged) > 15:
        print(f"   … et {len(flagged) - 15} autres")


if __name__ == "__main__":
    main()
