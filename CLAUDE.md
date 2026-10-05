# Copains Gourmands — notes pour Claude

Site statique Astro (FR/EN) qui catalogue les restos du compte Instagram @copainsgourmands : catalogue, carte, fiches.
En ligne sur https://copainsgourmands.github.io (dépôt **public** `copainsgourmands/copainsgourmands.github.io`, GitHub Pages).
L'utilisateur écrit en français : lui répondre en français, en termes simples (il n'est pas développeur).

## Flux des données
Export Instagram (`data/raw/`) ou API Instagram → `scripts/import_instagram.py` → `data/restaurants.csv` → `data/restaurants.json` → site.
- **`data/restaurants.csv` est la source de vérité** : il contient des corrections faites à la main (noms, adresses, positions vérifiées). Ne jamais le régénérer de zéro ; modifier les lignes, puis `npm run import -- --csv-only`.
- Le déploiement (`.github/workflows/deploy.yml`) relance `--csv-only` avant le build : une correction du CSV suffit.

## Commandes
- `npm run dev` → http://localhost:4321 · `npm run build`
- `npm run import` (export dans `data/raw/`) · `-- --csv-only` · `-- --no-geo` · `-- --api` (variable `IG_TOKEN`, utilisé par le robot)
- Python : `/opt/anaconda3/bin/python3` (Pillow installé).

## Robot Instagram (`.github/workflows/instagram.yml`)
- Tous les soirs : lit les nouveaux posts via l'API, ouvre la PR « 🍽️ Nouveaux restos à valider » (branche `robot/nouveaux-posts`). L'utilisateur valide (merge) ou refuse (close : les ids en commentaire HTML de la PR ne sont plus proposés).
- Secret `IG_TOKEN` (clé Instagram, 60 jours, renouvelée le lundi ; `GH_PAT` facultatif pour l'enregistrer). Variable `ALERT_USER`.
- Clé refusée → ticket « 🔑 Clé Instagram à renouveler » (label `cle-instagram`) assigné à `ALERT_USER`, fermé automatiquement quand la clé remarche. Test : Run workflow avec `test_alerte`.
- `data/instagram_state.json` : date du dernier post traité.

## Confidentialité (dépôt public !)
- `data/raw/` (export : messages, téléphone, date de naissance) est dans `.gitignore` : ne jamais le committer ni en citer le contenu.
- Commits signés avec l'adresse noreply GitHub (config git locale du dépôt). Ne jamais mettre d'e-mail perso, de clé ou de token dans un fichier, un commit, un ticket ou une PR.
- Avant tout commit : `git status` et ne committer que ses propres changements (d'autres discussions Claude travaillent aussi ici).
- Publier = commit + push sur `main` (site à jour ~2 min après). Pas de push forcé ni de réécriture d'historique sans accord explicite.

## Légal
- Aucun cookie, aucun traceur → pas de bandeau. Ajouter de l'analytics, une vidéo intégrée, un widget Instagram, etc. impose un bandeau de consentement **et** la mise à jour de `src/pages/[lang]/mentions-legales.astro`.
- Polices hébergées localement (`@fontsource-variable/*`) : ne pas revenir à Google Fonts.
- Éditeur non professionnel et anonyme (LCEN art. 6-III-2), contact par DM Instagram. Si l'activité devient payée, les mentions doivent afficher l'identité.
- Avis avec « *invitation » → mention « Collaboration commerciale » (`isSponsored` dans `src/lib/restaurants.ts`, loi n° 2023-451).

## Contenu
- Les légendes n'ont pas de note /5 ; les étoiles (🌟, ⭐️⭐️⭐️) désignent le guide Michelin, pas une note. L'interface « note » reste masquée tant qu'aucune note n'est saisie.
- Ton « nous / on » (plusieurs copains). Émojis et familles de cuisine : `CUISINE_EMOJI` et `FAMILIES` dans `src/lib/restaurants.ts`.

## Pièges connus
- `package-lock.json` régénéré sur Mac perd des dépendances Linux (`@emnapi/*`) → `npm ci` échoue sur GitHub. Ajouter un paquet sans réécrire le reste du lock, et vérifier `npm ci` avant de pousser.
- Carte vide en `npm run dev` = Vite qui renvoie 504 sur Leaflet : `optimizeDeps` dans `astro.config.mjs` + redémarrer le serveur.
- L'API Adresse (data.geopf.fr) tombe parfois : le script bascule sur OpenStreetMap (Nominatim).
- Le Bureau est synchronisé par iCloud : des copies « fichier 2.ext » peuvent apparaître ; ne pas les committer.
