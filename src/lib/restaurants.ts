import { existsSync } from 'node:fs';
import { join } from 'node:path';
import data from '../../data/restaurants.json';
import type { Lang } from './i18n';

export interface Restaurant {
  slug: string;
  name: string;
  address: string;
  city: string;
  arrondissement: number | null;
  other_addresses?: string[];
  lat: number | null;
  lng: number | null;
  rating: number | null;
  review: string;
  /** Avis en anglais (colonne « avis_en » du CSV). */
  review_en?: string;
  cuisine: string | null;
  price: string | null;
  date: string;
  photos: string[];
  instagram_url: string | null;
  instagram_handle?: string | null;
}

export const IS_DEMO: boolean = data.demo;

/** Plus récents d'abord. */
export const restaurants: Restaurant[] = [...(data.restaurants as Restaurant[])].sort((a, b) =>
  b.date.localeCompare(a.date),
);

/** Noms de ville du CSV (en anglais) traduits pour le site FR. */
const CITY_FR: Record<string, string> = { London: 'Londres', 'Mexico City': 'Mexico' };
export function cityLabel(city: string, lang: Lang): string {
  return lang === 'fr' ? CITY_FR[city] ?? city : city;
}

export function areaLabel(r: Restaurant, lang: Lang): string {
  if (r.arrondissement == null) return cityLabel(r.city, lang);
  const n = r.arrondissement;
  if (lang === 'fr') return `Paris ${n}${n === 1 ? 'er' : 'e'}`;
  const suffix = n % 10 === 1 && n !== 11 ? 'st' : n % 10 === 2 && n !== 12 ? 'nd' : n % 10 === 3 && n !== 13 ? 'rd' : 'th';
  return `Paris ${n}${suffix}`;
}

/** Clé de tri : arrondissements dans l'ordre, puis les autres villes. */
export function areaKey(r: Restaurant): string {
  return r.arrondissement != null ? `0-${String(r.arrondissement).padStart(2, '0')}` : `1-${r.city}`;
}

/** Le compte ne note pas (encore) ses restos : toute l'interface « note » se masque tant qu'aucune n'est saisie. */
export const HAS_RATINGS = restaurants.some((r) => r.rating != null);

/** Couleur d'une note : du rouge (moyen) au jaune citron (top). */
export function ratingColor(rating: number | null): string {
  if (rating == null) return HAS_RATINGS ? '#9CA3AF' : '#F0D58C';
  if (rating >= 4.5) return '#F0D58C';
  if (rating >= 4) return '#A9D3B4';
  if (rating >= 3) return '#F2B98C';
  return '#E5938C';
}

export function formatRating(rating: number | null, lang: Lang): string {
  if (rating == null) return '–';
  const s = Number.isInteger(rating) ? String(rating) : rating.toFixed(1);
  return lang === 'fr' ? s.replace('.', ',') : s;
}

export function stats() {
  const rated = restaurants.filter((r) => r.rating != null);
  const avg = rated.reduce((s, r) => s + (r.rating as number), 0) / (rated.length || 1);
  const areas = new Set(restaurants.map(areaKey));
  const cities = new Set(restaurants.map((r) => r.city).filter(Boolean));
  return { count: restaurants.length, areas: areas.size, cities: cities.size, avg };
}

/** Villes les plus fournies, dans la langue de la page (descriptions pour Google et les aperçus). */
export function topCities(lang: Lang, n = 4): string[] {
  const counts = new Map<string, number>();
  for (const r of restaurants) if (r.city) counts.set(r.city, (counts.get(r.city) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([c]) => cityLabel(c, lang));
}

/** Villes, de la plus fournie à la moins fournie, avec l'emprise de leurs épingles (boutons de la carte). */
export function cityGroups() {
  const groups = new Map<string, Restaurant[]>();
  for (const r of restaurants) if (r.city && r.lat != null && r.lng != null) groups.set(r.city, [...(groups.get(r.city) ?? []), r]);
  return [...groups.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([city, rs]) => ({
      city,
      count: rs.length,
      bounds: [
        [Math.min(...rs.map((r) => r.lat!)), Math.min(...rs.map((r) => r.lng!))],
        [Math.max(...rs.map((r) => r.lat!)), Math.max(...rs.map((r) => r.lng!))],
      ] as [[number, number], [number, number]],
    }));
}

/** Avis fait sur invitation (« *invitation » dans la légende) : signalé comme collaboration commerciale
 * (loi n° 2023-451 du 9 juin 2023 sur l'influence commerciale). */
const INVITATION_RE = /^[ \t]*\*[ \t]*invitation[ \t]*$/im;
export function isSponsored(r: Restaurant): boolean {
  return INVITATION_RE.test(r.review);
}
/** Avis dans la langue de la page. */
export function reviewIn(r: Restaurant, lang: Lang): string {
  return lang === 'en' ? r.review_en ?? r.review : r.review;
}
/** Avis affiché, sans la ligne « *invitation » (remplacée par la mention de collaboration). */
export function reviewText(r: Restaurant, lang: Lang): string {
  return reviewIn(r, lang).replace(new RegExp(INVITATION_RE.source, 'gim'), '').replace(/\n{3,}/g, '\n\n').trim();
}

/** Émoji affiché sur l'épingle, selon la cuisine (colonne « cuisine » du CSV). */
const CUISINE_EMOJI: Record<string, string> = {
  'Matcha & café': '🍵', Boulangerie: '🥐', Brunch: '🥞', Healthy: '🥗',
  Italien: '🍝', Français: '🍽️', Brasserie: '🍽️', Bistrot: '🍲', Gastronomique: '🥂',
  Japonais: '🍣', Chinois: '🥟', Thaï: '🍜', Taïwanais: '🧋', Asiatique: '🥢', Indien: '🍛', Coréen: '🍜', Vietnamien: '🍜',
  Méditerranéen: '🫒', Libanais: '🧆', Turc: '🧆', Israélien: '🥙', Grec: '🫒',
  Mexicain: '🌮', 'Sud-américain': '🌶️', Péruvien: '🌶️',
  Tapas: '🥘', 'Bar à vin': '🍷', 'Bar à cocktails': '🍸', 'Beach club': '🏝️',
  Viande: '🥩', Burger: '🍔', 'Food market': '🛍️', 'Street food': '🥙', Pâtisserie: '🧁', Végétarien: '🥗',
};
/** Nom anglais des cuisines (le CSV les écrit en français). Une cuisine absente d'ici garde son nom français. */
const CUISINE_EN: Record<string, string> = {
  'Matcha & café': 'Matcha & coffee', Boulangerie: 'Bakery', Brunch: 'Brunch', Healthy: 'Healthy',
  Italien: 'Italian', Français: 'French', Brasserie: 'Brasserie', Bistrot: 'Bistro', Gastronomique: 'Fine dining',
  Japonais: 'Japanese', Chinois: 'Chinese', Thaï: 'Thai', Taïwanais: 'Taiwanese', Asiatique: 'Asian', Indien: 'Indian', Coréen: 'Korean', Vietnamien: 'Vietnamese',
  Méditerranéen: 'Mediterranean', Libanais: 'Lebanese', Turc: 'Turkish', Israélien: 'Israeli', Grec: 'Greek',
  Mexicain: 'Mexican', 'Sud-américain': 'South American', Péruvien: 'Peruvian',
  Tapas: 'Tapas', 'Bar à vin': 'Wine bar', 'Bar à cocktails': 'Cocktail bar', 'Beach club': 'Beach club',
  Viande: 'Grill & meat', Burger: 'Burgers', 'Food market': 'Food market', 'Street food': 'Street food', Pâtisserie: 'Pastry', Végétarien: 'Vegetarian',
};
export function cuisineLabel(cuisine: string | null, lang: Lang): string {
  if (!cuisine) return '';
  return lang === 'en' ? CUISINE_EN[cuisine] ?? cuisine : cuisine;
}

export function cuisineEmoji(cuisine: string | null): string {
  return (cuisine && CUISINE_EMOJI[cuisine]) || '🍴';
}

/** Grandes familles pour filtrer la carte (une cuisine absente d'ici tombe dans « Autres »). */
export const FAMILIES: { id: string; emoji: string; fr: string; en: string; cuisines: string[] }[] = [
  { id: 'cafe', emoji: '☕', fr: 'Café & matcha', en: 'Coffee & matcha', cuisines: ['Matcha & café', 'Boulangerie', 'Pâtisserie'] },
  { id: 'brunch', emoji: '🥞', fr: 'Brunch', en: 'Brunch', cuisines: ['Brunch', 'Healthy'] },
  { id: 'italien', emoji: '🍝', fr: 'Italien', en: 'Italian', cuisines: ['Italien'] },
  { id: 'francais', emoji: '🍽️', fr: 'Français', en: 'French', cuisines: ['Français', 'Brasserie', 'Bistrot', 'Gastronomique'] },
  { id: 'asiatique', emoji: '🥢', fr: 'Asiatique', en: 'Asian', cuisines: ['Japonais', 'Chinois', 'Thaï', 'Taïwanais', 'Asiatique', 'Indien', 'Coréen', 'Vietnamien'] },
  { id: 'medit', emoji: '🧆', fr: 'Méditerranéen', en: 'Mediterranean', cuisines: ['Méditerranéen', 'Libanais', 'Turc', 'Israélien', 'Grec'] },
  { id: 'latino', emoji: '🌮', fr: 'Latino', en: 'Latin', cuisines: ['Mexicain', 'Sud-américain', 'Péruvien'] },
  { id: 'bars', emoji: '🍸', fr: 'Bars & tapas', en: 'Bars & tapas', cuisines: ['Bar à vin', 'Bar à cocktails', 'Beach club', 'Tapas'] },
];
export function familyOf(cuisine: string | null): string {
  return FAMILIES.find((f) => cuisine && f.cuisines.includes(cuisine))?.id ?? 'autres';
}

export function mapPoints(lang: Lang) {
  return restaurants
    .filter((r) => r.lat != null && r.lng != null)
    .map((r) => ({
      slug: r.slug,
      name: r.name,
      lat: r.lat,
      lng: r.lng,
      rating: r.rating,
      ratingLabel: r.rating == null ? '' : formatRating(r.rating, lang),
      color: ratingColor(r.rating),
      area: areaLabel(r, lang),
      cuisine: cuisineLabel(r.cuisine, lang) || null,
      sponsored: isSponsored(r),
      emoji: cuisineEmoji(r.cuisine),
      family: familyOf(r.cuisine),
      photo: pinPhoto(r),
    }));
}

/** Fichier de public/ produit par scripts/make_images.py (absent tant que le script n'a pas tourné). */
const generated = (path: string) => existsSync(join(process.cwd(), 'public', path));

/** Vignette 128 px des épingles, sinon la vignette 480 px. */
function pinPhoto(r: Restaurant): string | null {
  if (!r.photos[0]) return null;
  return generated(`pins/${r.slug}.webp`) ? `pins/${r.slug}.webp` : thumb(r.photos[0]);
}

/** Image d'aperçu (partage du lien) : celle de la fiche, sinon celle du site. */
export function ogImage(lang: Lang, slug?: string): string | undefined {
  if (slug && generated(`og/${lang}/${slug}.jpg`)) return `og/${lang}/${slug}.jpg`;
  return generated(`og/${lang}/default.jpg`) ? `og/${lang}/default.jpg` : undefined;
}

/** Description de la fiche pour Google et les aperçus : « Nom (quartier, cuisine) : début de l'avis… »,
 * sans émoji ni retour à la ligne, 155 caractères au plus, coupée après un mot entier. */
export function metaDescription(r: Restaurant, lang: Lang): string {
  const head = `${r.name.replace(/\s+/g, ' ')} (${[areaLabel(r, lang), cuisineLabel(r.cuisine, lang)].filter(Boolean).join(', ')})`;
  const sep = lang === 'fr' ? ' : ' : ': ';
  // Chaque ligne de l'avis devient une phrase (sinon deux phrases se collent une fois les retours à la ligne retirés).
  const text = reviewText(r, lang)
    .replace(/[\p{Extended_Pictographic}\u{FE0F}\u{200D}\u{20E3}]/gu, '')
    .split(/\n+/)
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .map((line, i, all) => (i < all.length - 1 && !/[.!?…:;,]$/.test(line) ? `${line}.` : line))
    .join(' ');
  // Un avis réduit à un prix (« ~€10/20 ») n'apprend rien : on le remplace par une phrase type.
  const useful = /[\p{L}]{4,}/u.test(text) && text.length >= 40;
  const fallback = lang === 'fr' ? 'notre avis, les photos et l’adresse.' : 'our review, photos and address.';
  const full = head + sep + (useful ? text : fallback);
  if (full.length <= 155) return full;
  const cut = full.slice(0, 154);
  return cut.slice(0, cut.lastIndexOf(' ')).replace(/[\s,;:.\-–—]+$/, '') + '…';
}

/** Vignette carrée générée par l'import (sinon l'image d'origine, ex. visuels de démo). */
export function thumb(path: string): string {
  return path.endsWith('.webp') ? path.replace(/\.webp$/, '-thumb.webp') : path;
}
