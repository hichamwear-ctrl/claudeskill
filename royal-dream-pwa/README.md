# Royal Dream Events — PWA (application web installable)

Version **PWA** du site [happy-jump-analysis.lovable.app](https://happy-jump-analysis.lovable.app).
Contrairement à une app native, cette PWA réutilise **le HTML exact de votre site** et se
relie à **la vraie feuille de style et aux vraies images du site en ligne** → le rendu est
quasi **pixel-identique** à l'original, avec toutes les sections, animations et la FAQ.

Elle s'installe sur l'iPhone via Safari (« Ajouter à l'écran d'accueil ») et s'ouvre en
**plein écran, comme une vraie application**.

### Contenu
`index.html` · `manifest.webmanifest` · `sw.js` (service worker, mode hors-ligne) ·
`icon.svg` + `icon-180/192/512.png` (icônes couronne royale).

---

## 📲 Tester sur votre iPhone

### ✅ Option 1 — Netlify Drop (le plus simple, aucun ordinateur technique requis)
1. Sur un ordinateur, allez sur **https://app.netlify.com/drop**
2. **Glissez-déposez le dossier `royal-dream-pwa`** dans la zone → vous obtenez une adresse
   **https://…netlify.app** (en HTTPS).
3. Ouvrez cette adresse dans **Safari sur l'iPhone**.
4. Touchez le bouton **Partager** (carré avec une flèche ⬆️) → **« Sur l'écran d'accueil »**.
5. L'icône Royal Dream apparaît sur l'iPhone et s'ouvre en plein écran. 🎉

### ✅ Option 2 — Test local rapide (même Wi-Fi)
Sur un ordinateur, dans ce dossier :
```bash
cd royal-dream-pwa
python3 -m http.server 8080      # ou : npx serve .
```
Trouvez l'IP locale de l'ordinateur (ex. `192.168.1.20`), puis sur Safari iPhone ouvrez
`http://192.168.1.20:8080`. Puis **Partager → Sur l'écran d'accueil**.
> En local (http), le mode hors-ligne du service worker est désactivé, mais l'app
> s'installe et s'affiche en plein écran normalement.

### ✅ Option 3 — GitHub Pages (URL permanente)
1. Renommez le dossier `royal-dream-pwa` en `docs` (Pages sert depuis `/docs`).
2. GitHub → **Settings → Pages → Source: Deploy from a branch**, branche `claude/busy-lamport-mfgiR`,
   dossier **`/docs`** → Save.
3. L'URL `https://hichamwear-ctrl.github.io/claudeskill/` devient votre PWA → ouvrez-la sur
   iPhone → **Partager → Sur l'écran d'accueil**.

---

## ⚠️ À savoir
- Le style et les images sont chargés depuis votre site Lovable en ligne. **Tant que le site
  reste publié**, tout s'affiche parfaitement.
- Si vous **re-publiez** le site sur Lovable, le nom du fichier CSS peut changer
  (`styles-XXXX.css`). Si le style « casse », il suffit de mettre à jour cette ligne dans
  `index.html` (ou envoyez-moi le contenu du CSS et je l'intègre directement dans le fichier
  pour le rendre 100 % autonome).
- Boutons interactifs ajoutés : chaque **château** ouvre WhatsApp pré-rempli avec son nom ;
  la **FAQ** fonctionne nativement ; le sélecteur **FR/NL/EN** change l'état visuel.
