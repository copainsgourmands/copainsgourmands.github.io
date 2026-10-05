"""Images dérivées des photos, refaites à chaque déploiement (non versionnées) :
- public/og/<lang>/<slug>.jpg : aperçu de la fiche quand on partage son lien (WhatsApp, Instagram, iMessage…), 1200×630 ;
- public/og/<lang>/default.jpg : aperçu de l'accueil, du catalogue et de la carte ;
- public/pins/<slug>.webp : vignette 128 px des épingles de la carte (au lieu de la vignette 480 px).

Usage : python scripts/make_images.py   (après l'import, qui produit data/restaurants.json)
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
FONT = ROOT / "scripts" / "fonts" / "BricolageGrotesque.ttf"
LOGO = PUBLIC / "logo.png"

W, H = 1200, 630
BLUE, BLUE_DEEP, BLUE_LIGHT = (2, 35, 125), (1, 24, 90), (20, 56, 154)
RED, PAPER, ROSE = (172, 18, 17), (251, 249, 244), (248, 230, 228)

# Mêmes libellés que le site (src/lib/restaurants.ts).
CITY = {"fr": {"London": "Londres", "Mexico City": "Mexico"}, "en": {}}
TEXT = {
    "fr": {"tagline": "Nos adresses préférées.\nParis, et parfois ailleurs.", "count": "{n} adresses testées"},
    "en": {"tagline": "Our favourite spots.\nParis, and sometimes elsewhere.", "count": "{n} places tried"},
}


def font(size: int, weight: int = 800) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([min(96, max(12, size)), weight])  # taille optique, graisse
    return f


def area(r: dict, lang: str) -> str:
    n = r.get("arrondissement")
    if n is None:
        return CITY[lang].get(r["city"], r["city"])
    if lang == "fr":
        return f"Paris {n}{'er' if n == 1 else 'e'}"
    suffix = "st" if n % 10 == 1 and n != 11 else "nd" if n % 10 == 2 and n != 12 else "rd" if n % 10 == 3 and n != 13 else "th"
    return f"Paris {n}{suffix}"


def gradient() -> Image.Image:
    """Fond bleu du bandeau d'accueil : plus clair en haut à droite."""
    small = Image.new("RGB", (120, 63))
    px = small.load()
    for y in range(63):
        for x in range(120):
            d = min(1.0, (((x - 102) / 120) ** 2 + ((y - 6) / 63) ** 2) ** 0.5 / 1.1)
            c = [BLUE_LIGHT, BLUE, BLUE_DEEP]
            a, b, t = (c[0], c[1], d / 0.5) if d < 0.5 else (c[1], c[2], (d - 0.5) / 0.5)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return small.resize((W, H), Image.BICUBIC)


def logo_badge(size: int) -> Image.Image:
    """Le logo dans un rond blanc, comme dans le menu du site."""
    big = size * 4
    badge = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(badge).ellipse((0, 0, big - 1, big - 1), fill=(255, 255, 255, 255))
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((int(big * 0.74), int(big * 0.74)), Image.LANCZOS)
    badge.alpha_composite(logo, ((big - logo.width) // 2, (big - logo.height) // 2 + big // 60))
    return badge.resize((size, size), Image.LANCZOS)


def sticker(text: str, size: int) -> Image.Image:
    """Pastille rouge en capitales, légèrement penchée (classe .sticker du site)."""
    f = font(size, 800)
    text = text.upper()
    spacing = size * 0.08
    widths = [f.getlength(c) for c in text]
    tw = sum(widths) + spacing * (len(text) - 1)
    pad_x, pad_y = size * 1.0, size * 0.55
    w, h = int(tw + 2 * pad_x), int(size + 2 * pad_y)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=RED)
    x = pad_x
    for c, cw in zip(text, widths):
        d.text((x, h / 2), c, font=f, fill="white", anchor="lm")
        x += cw + spacing
    return img.rotate(2, resample=Image.BICUBIC, expand=True)


def wrap(text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if f.getlength(test) <= width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    return lines + [line]


def fit_title(text: str, width: int, max_lines: int, sizes: range) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in sizes:
        f = font(size)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines and all(f.getlength(l) <= width for l in lines):
            return f, lines
    return f, lines


def photo(path: Path, w: int, h: int) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.12))  # haut de la photo : le nom de la ville est incrusté en bas


def resto_card(r: dict, lang: str) -> Image.Image:
    img = gradient()
    pw = 560
    img.paste(photo(PUBLIC / r["photos"][0].lstrip("/"), pw, H), (0, 0))
    x0, x1 = pw + 64, W - 64
    s = sticker(area(r, lang), 22)
    img.paste(s, (x0 - 4, 74), s)
    name = " ".join(r["name"].split())
    f, lines = fit_title(name, x1 - x0, 3, range(96, 40, -4))
    lh = int(f.size * 1.02)
    y = 74 + s.height + 26 + (3 - len(lines)) * lh // 3
    d = ImageDraw.Draw(img)
    for line in lines:
        d.text((x0, y), line, font=f, fill="white")
        y += lh
    b = logo_badge(104)
    by = H - 64 - b.height
    img.paste(b, (x0, by), b)
    d.text((x0 + b.width + 22, by + b.height / 2 - 2), "Copains Gourmands", font=font(34), fill="white", anchor="ls")
    d.text((x0 + b.width + 22, by + b.height / 2 + 10), "@copainsgourmands", font=font(24, 500), fill=ROSE, anchor="lt")
    return img


def default_card(restos: list[dict], lang: str) -> Image.Image:
    img = gradient().convert("RGBA")
    d = ImageDraw.Draw(img)
    # Collage de photos à droite, comme sur l'accueil.
    spots = [((690, 40), -6, 270), ((930, 60), 5, 230), ((740, 330), 4, 250), ((990, 340), -4, 190)]
    for r, ((x, y), angle, size) in zip(restos, spots):
        p = photo(PUBLIC / r["photos"][0].lstrip("/"), size, size)
        framed = Image.new("RGBA", (size + 16, size + 16), PAPER + (255,))
        framed.paste(p, (8, 8))
        mask = Image.new("L", framed.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, framed.width - 1, framed.height - 1), radius=22, fill=255)
        framed.putalpha(mask)
        framed = framed.rotate(angle, resample=Image.BICUBIC, expand=True)
        shadow = Image.new("RGBA", framed.size, (0, 0, 0, 0))
        shadow.putalpha(framed.getchannel("A").point(lambda a: int(a * 0.4)).filter(ImageFilter.GaussianBlur(14)))
        img.alpha_composite(shadow, (x + 4, y + 16))
        img.alpha_composite(framed, (x, y))
    b = logo_badge(150)
    img.alpha_composite(b, (70, 62))
    title = font(92)
    d.text((70, 240), "Copains", font=title, fill="white")
    d.text((70, 330), "Gourmands", font=title, fill="white")
    y = 450
    for line in TEXT[lang]["tagline"].split("\n"):
        d.text((72, y), line, font=font(32, 500), fill=ROSE)
        y += 42
    return img.convert("RGB")


def main():
    data = json.loads((ROOT / "data" / "restaurants.json").read_text(encoding="utf-8"))
    restos = sorted((r for r in data["restaurants"] if r["photos"]), key=lambda r: r["date"], reverse=True)
    pins = PUBLIC / "pins"
    pins.mkdir(exist_ok=True)
    for lang in ("fr", "en"):
        out = PUBLIC / "og" / lang
        out.mkdir(parents=True, exist_ok=True)
        default_card(restos[:4], lang).save(out / "default.jpg", quality=84, optimize=True, progressive=True)
        for r in restos:
            resto_card(r, lang).save(out / f"{r['slug']}.jpg", quality=82, optimize=True, progressive=True)
    for r in restos:
        src = PUBLIC / r["photos"][0].lstrip("/")
        thumb = src.with_name(src.stem + "-thumb.webp")
        im = Image.open(thumb if thumb.exists() else src).convert("RGB")
        ImageOps.fit(im, (128, 128), Image.LANCZOS).save(pins / f"{r['slug']}.webp", "WEBP", quality=80)
    print(f"Images de partage : accueil et {len(restos)} fiches, en FR et EN ; vignettes d'épingle : {len(restos)}.")


if __name__ == "__main__":
    main()
