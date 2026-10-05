// Consignes aux robots des moteurs de recherche : tout est ouvert, et voici le plan du site.
import type { APIRoute } from 'astro';
import { url } from '../lib/i18n';

export const GET: APIRoute = ({ site }) =>
  new Response(`User-agent: *\nAllow: /\n\nSitemap: ${new URL(url('sitemap.xml'), site).href}\n`, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
