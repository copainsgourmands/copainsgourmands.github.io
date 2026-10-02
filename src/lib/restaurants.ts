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

export function areaLabel(r: Restaurant, lang: Lang): string {
  if (r.arrondissement == null) return r.city;
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
      cuisine: r.cuisine,
      emoji: cuisineEmoji(r.cuisine),
      family: familyOf(r.cuisine),
      photo: r.photos[0] ? thumb(r.photos[0]) : null,
    }));
}

/** Vignette carrée générée par l'import (sinon l'image d'origine, ex. visuels de démo). */
export function thumb(path: string): string {
  return path.endsWith('.webp') ? path.replace(/\.webp$/, '-thumb.webp') : path;
}
