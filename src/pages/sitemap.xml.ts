// Plan du site pour Google et Bing : chaque page, avec son équivalent dans l'autre langue.
import type { APIRoute } from 'astro';
import { LANGS, url } from '../lib/i18n';
import { restaurants } from '../lib/restaurants';

export const GET: APIRoute = ({ site }) => {
  const abs = (p: string) => new URL(url(p), site).href;
  const latest = restaurants[0]?.date;
  const pages: { path: string; lastmod?: string }[] = [
    { path: '', lastmod: latest },
    { path: 'catalogue/', lastmod: latest },
    { path: 'carte/', lastmod: latest },
    { path: 'mentions-legales/' },
    ...restaurants.map((r) => ({ path: `resto/${r.slug}/`, lastmod: r.date })),
  ];
  const urls = pages.flatMap(({ path, lastmod }) =>
    LANGS.map((lang) => [
      '  <url>',
      `    <loc>${abs(`${lang}/${path}`)}</loc>`,
      lastmod ? `    <lastmod>${lastmod}</lastmod>` : '',
      ...LANGS.map((l) => `    <xhtml:link rel="alternate" hreflang="${l}" href="${abs(`${l}/${path}`)}"/>`),
      `    <xhtml:link rel="alternate" hreflang="x-default" href="${path ? abs(`fr/${path}`) : abs('/')}"/>`,
      '  </url>',
    ].filter(Boolean).join('\n')),
  );
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${urls.join('\n')}
</urlset>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
