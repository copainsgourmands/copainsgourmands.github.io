import { defineConfig } from 'astro/config';

// SITE et BASE sont fournis par le workflow GitHub Pages (ex. BASE=/food-site).
export default defineConfig({
  site: process.env.SITE || 'http://localhost:4321',
  base: process.env.BASE || '/',
  trailingSlash: 'ignore',
  vite: {
    // Pré-compilées dès le lancement de `npm run dev`, sinon la carte peut rester vide (erreur 504 de Vite).
    optimizeDeps: { include: ['leaflet', 'leaflet.markercluster'] },
    // L'export Instagram (des milliers de fichiers) n'a pas à être surveillé.
    server: { watch: { ignored: ['**/data/raw/**'] } },
  },
});
