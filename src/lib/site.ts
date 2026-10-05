// Identité du compte.
export const SITE = {
  name: 'Copains Gourmands',
  handle: 'copainsgourmands',
  instagram: 'https://www.instagram.com/copainsgourmands/',
};

// Données structurées « site + compte » pour Google, identiques sur l'adresse racine et les accueils FR/EN :
// le nom du site dans les résultats (WebSite, porté par l'adresse racine) et le lien avec le compte Instagram.
export function siteSchema(abs: (p: string) => string) {
  return [
    { '@type': 'WebSite', '@id': abs('/#website'), name: SITE.name, alternateName: ['CopainsGourmands', `@${SITE.handle}`], url: abs('/'), inLanguage: ['fr', 'en'], publisher: { '@id': abs('/#org') } },
    { '@type': 'Organization', '@id': abs('/#org'), name: SITE.name, alternateName: `@${SITE.handle}`, url: abs('/'), logo: abs('logo.png'), sameAs: [SITE.instagram] },
  ];
}
