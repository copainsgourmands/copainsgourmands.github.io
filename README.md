# Copains Gourmands : le site

Catalogue de tous les restos testés, avec photos, avis, note sur 5 et carte. Il est construit à partir de l'export de ton compte Instagram.

## 1. Lancer le site sur ton Mac

```bash
cd ~/Desktop/"Projets perso"/"site CG"
npm run dev
```
Ouvre ensuite http://localhost:4321 dans ton navigateur. **Laisse le terminal ouvert** : si tu le fermes, la page localhost ne répond plus. Le site se met à jour à chaque modification. Pour l'arrêter : `Ctrl + C`.

## 2. Nom du compte

Il est défini dans `src/lib/site.ts` (`name`, `handle`, `instagram`).

## 3. Importer tes vrais posts Instagram

1. Dans Instagram : **Paramètres → Espace Comptes → Vos informations et autorisations → Télécharger vos informations**.
   - Choisis ton compte food.
   - Prends « Toutes les informations » ou au minimum « Contenu ».
   - Format **JSON** ou **HTML** (les deux marchent), qualité **élevée**, période **depuis toujours**.
2. Quand l'email arrive, télécharge le `.zip` et dépose-le dans `site CG/data/raw/` (zippé ou décompressé).
   **Jamais à la racine du projet** : `data/raw/` est exclu de git, alors que l'export contient tes messages et infos de connexion.
3. Lance l'import :
   ```bash
   npm run import
   ```
   Le script :
   - lit tes posts photo ;
   - trouve dans chaque légende le nom du resto (première ligne, avant le @compte), le @compte du resto, l'adresse (📍) et les autres adresses, la ville, le prix (`€€` ou les lignes « ~ plats de 16 à 48€ ») et la cuisine ;
   - la note est facultative : `4,5/5` ou `note : ⭐⭐⭐⭐` dans la légende, ou la colonne `note` du CSV. Tant qu'aucun resto n'a de note, le site masque tout ce qui concerne les notes ;
   - regroupe plusieurs visites d'un même resto ;
   - place chaque resto sur la carte ;
   - convertit les photos.

   À la fin, il affiche un rapport et la liste de ce qui est **à vérifier**.

## 4. Corriger dans Excel

Ouvre `data/restaurants.csv` dans Excel. Il y a une ligne par resto, et la colonne **statut** indique ce qui manque.

| Colonne | À quoi elle sert |
|---|---|
| `inclure` | Mets `non` pour cacher un post qui n'est pas un resto. Ses photos ne sont jamais publiées. |
| `note` | Note sur 5, par exemple `4,5`. |
| `adresse` | Si tu la changes, le resto est replacé sur la carte au prochain import. |
| `position` | `nom` = l'épingle a été devinée à partir du nom du resto ; `quartier` = épingle au centre du quartier. Vérifie-la (ou saisis lat/lng), puis écris `vérifiée`. |
| `autres_adresses` | Autres adresses de la même enseigne, séparées par ` · `. Affichées sur la fiche. |
| `instagram_resto` | Compte Instagram du resto (sans @), affiché en bouton sur la fiche. |
| `lat` / `lng` | Tu peux saisir des coordonnées à la main (clic droit dans Google Maps). |
| `lien_instagram` | Lien du post. L'export ne le fournit pas, donc il faut le coller à la main. |
| `cuisine`, `prix`, `avis`, `nom`, `ville` | Modifiables librement. |

Enregistre le fichier en gardant le format CSV, puis lance :
```bash
npm run import -- --csv-only
```
**Tes corrections ne sont jamais écrasées**, même si tu renommes un resto (il est reconnu grâce à ses photos) : un nouvel import (par exemple dans six mois, avec un nouvel export) ajoute seulement les nouveaux restos et les nouvelles photos.

## 5. Mettre en ligne (gratuit, GitHub Pages)

1. Crée un compte sur github.com, puis un dépôt **public** nommé par exemple `food-site`.
2. Envoie le projet sur GitHub :
   ```bash
   cd ~/Desktop/"Projets perso"/"site CG"
   git init && git add . && git commit -m "Premier envoi"
   git branch -M main
   git remote add origin https://github.com/TON-PSEUDO/food-site.git
   git push -u origin main
   ```
3. Sur GitHub, va dans **Settings → Pages → Source : GitHub Actions**.
4. Environ deux minutes plus tard, le site est en ligne sur `https://TON-PSEUDO.github.io/food-site/`. C'est l'URL à mettre en bio.

Pour toute mise à jour : `npm run import`, puis `git add . && git commit -m "Nouveaux restos" && git push`.

Pour un nom de domaine perso (environ 10 €/an), va dans Settings → Pages → Custom domain.

## 6. Mise à jour automatique à chaque nouveau post

Le site est en ligne sur https://copainsgourmands.github.io/.

Un robot GitHub (`.github/workflows/instagram.yml`) regarde le compte Instagram **tous les soirs** (vers 20h l'été, 19h l'hiver). À chaque nouveau post, il prépare la fiche (photos, adresse, carte) et ouvre une **pull request « Nouveaux restos à valider »**. Tu reçois un e-mail de GitHub.
- **Valider** : « Merge pull request ». Le site est à jour 2 minutes après.
- **Corriger avant** : onglet « Files changed », puis `data/restaurants.csv`, puis « Edit file ».
- **Refuser** : « Close pull request ». Ces posts ne seront plus proposés.

Le robot a besoin d'une clé d'accès Instagram, enregistrée dans le secret `IG_TOKEN` (Settings → Secrets and variables → Actions). Le lundi, il renouvelle cette clé, valable 60 jours. **Si la clé ne marche plus**, il ouvre un ticket « 🔑 Clé Instagram à renouveler » assigné au compte indiqué dans la variable `ALERT_USER` : tu le reçois par e-mail, avec la marche à suivre. Pour que ce renouvellement soit enregistré automatiquement, ajoute aussi un secret `GH_PAT` : un jeton GitHub limité à ce dépôt, avec la permission « Secrets : read and write ». Sans lui, il faudra recoller une nouvelle clé tous les 60 jours.

Pour lancer le robot tout de suite : onglet Actions, puis « Nouveaux posts Instagram », puis « Run workflow ».

## Structure

```
data/restaurants.csv     ← le tableau que tu édites
data/restaurants.json    ← généré, lu par le site
data/raw/                ← ton export Instagram (jamais publié)
data/instagram_state.json ← date du dernier post traité par le robot
scripts/import_instagram.py
src/pages/[lang]/        ← accueil, catalogue, carte, fiche resto (FR + EN)
src/i18n/fr.json, en.json ← textes de l'interface
src/styles/global.css    ← couleurs et polices (--blue, --lime…)
```
