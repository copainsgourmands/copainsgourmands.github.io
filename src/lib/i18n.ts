import fr from '../i18n/fr.json';
import en from '../i18n/en.json';

export const LANGS = ['fr', 'en'] as const;
export type Lang = (typeof LANGS)[number];

const dicts: Record<Lang, Record<string, string>> = { fr, en };

export function t(lang: Lang, key: string): string {
  return dicts[lang][key] ?? dicts.fr[key] ?? key;
}

export function langPaths() {
  return LANGS.map((lang) => ({ params: { lang } }));
}

/** Lien interne qui respecte le `base` (GitHub Pages sert le site sous /nom-du-repo/). */
export function url(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
}

export function otherLang(lang: Lang): Lang {
  return lang === 'fr' ? 'en' : 'fr';
}

export function formatMonth(iso: string, lang: Lang): string {
  return new Date(iso).toLocaleDateString(lang === 'fr' ? 'fr-FR' : 'en-GB', {
    month: 'long',
    year: 'numeric',
  });
}
