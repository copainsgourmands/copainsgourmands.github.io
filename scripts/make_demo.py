"""Génère des données et visuels de démonstration (remplacés ensuite par l'import Instagram)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "public" / "photos" / "demo"
PHOTOS.mkdir(parents=True, exist_ok=True)

DEMO = [
    ("pasta-nonna", "Pasta Nonna", "12 rue de Charonne, 75011 Paris", 48.8534, 2.3760, 4.5, "Italien", "€€", "2026-09-14", ["🍝", "🍷"], ("#FF5A5F", "#FFB4A2"),
     "Les rigatoni à la vodka sont DINGUES, sauce ultra crémeuse et pâtes al dente comme il faut. Service rapide, petite salle bruyante mais on s'en fiche. J'y retourne la semaine pro."),
    ("bao-club", "Bao Club", "5 rue du Faubourg Saint-Denis, 75010 Paris", 48.8706, 2.3537, 4.0, "Taïwanais", "€", "2026-08-30", ["🥟", "🧋"], ("#00C2A8", "#B8F3E8"),
     "Le bao poulet frit est parfait, pâte moelleuse et croustillant. Le bubble tea est trop sucré à mon goût. Super rapport qualité-prix pour un déj."),
    ("le-petit-zinc", "Le Petit Zinc", "8 rue des Martyrs, 75009 Paris", 48.8779, 2.3399, 3.5, "Bistrot", "€€", "2026-08-02", ["🥩", "🍟"], ("#8B5CF6", "#DDD6FE"),
     "Bistrot classique, l'onglet frites fait le job mais rien d'inoubliable. Ambiance sympa en terrasse. Bien pour un dîner sans prise de tête."),
    ("tacos-loco", "Tacos Loco", "41 rue Oberkampf, 75011 Paris", 48.8648, 2.3742, 4.5, "Mexicain", "€", "2026-07-21", ["🌮", "🌶️"], ("#F59E0B", "#FDE68A"),
     "Les meilleurs tacos al pastor que j'ai mangés à Paris. Tortillas maison, salsa verde qui pique bien. File d'attente le week-end, viens tôt."),
    ("sushi-hana", "Sushi Hana", "22 rue Sainte-Anne, 75001 Paris", 48.8665, 2.3363, 5.0, "Japonais", "€€€", "2026-06-11", ["🍣", "🍵"], ("#EF4444", "#FECACA"),
     "Omakase incroyable, poisson d'une fraîcheur folle. Le chef explique chaque pièce. Cher mais clairement le meilleur repas de l'année."),
    ("burger-bro", "Burger Bro", "3 rue de Lappe, 75011 Paris", 48.8538, 2.3712, 3.0, "Burger", "€€", "2026-05-18", ["🍔", "🥤"], ("#2563EB", "#BFDBFE"),
     "Burger correct mais pain un peu sec et frites molles. Pas mauvais, pas ouf. Il y a mieux dans le quartier."),
    ("cafe-montmartre", "Café Montmartre", "15 rue Lepic, 75018 Paris", 48.8853, 2.3336, 4.0, "Brunch", "€€", "2026-04-27", ["🥞", "☕"], ("#EC4899", "#FBCFE8"),
     "Brunch très généreux, pancakes fluffy et œufs Benedict bien faits. Réserve sinon 45 min d'attente. Vue sympa en sortant."),
    ("pho-saigon", "Phở Saigon", "88 avenue de Choisy, 75013 Paris", 48.8236, 2.3613, 4.5, "Vietnamien", "€", "2026-03-09", ["🍜", "🌿"], ("#10B981", "#A7F3D0"),
     "Bouillon qui a mijoté des heures, ça se sent. Portion énorme pour 13€. Le spot parfait quand il fait froid."),
    ("bouchon-lyonnais", "Le Bouchon du Coin", "9 rue Mercière, 69002 Lyon", 45.7614, 4.8335, 4.0, "Lyonnais", "€€", "2025-12-20", ["🍲", "🍷"], ("#B45309", "#FCD34D"),
     "Quenelle de brochet sauce Nantua parfaite. Ambiance nappes à carreaux, très authentique. Prévois une sieste après."),
]

def svg(emoji, c1, c2):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<rect width="800" height="800" fill="url(#g)"/>
<circle cx="400" cy="400" r="250" fill="#ffffff" opacity=".25"/>
<text x="400" y="470" font-size="300" text-anchor="middle">{emoji}</text>
</svg>'''

restaurants = []
for slug, name, address, lat, lng, rating, cuisine, price, date, emojis, colors, review in DEMO:
    photos = []
    for i, e in enumerate(emojis):
        f = PHOTOS / f"{slug}-{i}.svg"
        f.write_text(svg(e, *(colors if i == 0 else colors[::-1])), encoding="utf-8")
        photos.append(f"photos/demo/{f.name}")
    postcode = address.split(",")[-1].split()[0]
    city = address.split(",")[-1].split()[1]
    arr = int(postcode[-2:]) if postcode.startswith("75") else None
    restaurants.append({
        "slug": slug, "name": name, "address": address, "city": city,
        "arrondissement": arr, "lat": lat, "lng": lng, "rating": rating,
        "review": review, "cuisine": cuisine, "price": price, "date": date,
        "photos": photos, "instagram_url": None,
    })

out = ROOT / "data" / "restaurants.json"
out.write_text(json.dumps({"demo": True, "restaurants": restaurants}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(restaurants)} restaurants de démo → {out}")
