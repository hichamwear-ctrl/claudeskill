/* Assemble le site multi-pages en un seul fichier autonome : node build/build-spa.cjs
   (à lancer depuis la racine du dépôt). Produit miels-du-monde.html. */
const fs = require('fs');
const rd = f => fs.readFileSync(f, 'utf8');
const b64 = (f, mime) => 'data:' + mime + ';base64,' + fs.readFileSync(f).toString('base64');

const SLUGS = ['litchi', 'jujubier', 'curcuma', 'gelee-royale', 'citron-gingembre', 'nigelle', 'hibiscus'];
const PHOTOS = {}; for (const s of SLUGS) PHOTOS[s] = b64('assets/products/' + s + '.webp', 'image/webp');
const LOGO = b64('assets/logo.png', 'image/png');
const LOGO_LIGHT = b64('assets/logo-light.png', 'image/png');
const EARTH = b64('assets/textures/earth.jpg', 'image/jpeg');
const THREE = rd('assets/vendor/three.module.min.js');

const FF = [
  ['Inter', 'normal', 300, 'inter-latin-300-normal'], ['Inter', 'normal', 400, 'inter-latin-400-normal'],
  ['Inter', 'normal', 500, 'inter-latin-500-normal'], ['Inter', 'normal', 600, 'inter-latin-600-normal'],
  ['Inter', 'normal', 700, 'inter-latin-700-normal'],
  ['Cormorant Garamond', 'normal', 400, 'cormorant-garamond-latin-400-normal'],
  ['Cormorant Garamond', 'normal', 500, 'cormorant-garamond-latin-500-normal'],
  ['Cormorant Garamond', 'normal', 600, 'cormorant-garamond-latin-600-normal'],
  ['Cormorant Garamond', 'italic', 400, 'cormorant-garamond-latin-400-italic'],
  ['Cormorant Garamond', 'italic', 500, 'cormorant-garamond-latin-500-italic'],
].map(([fam, st, w, file]) => `@font-face{font-family:'${fam}';font-style:${st};font-weight:${w};font-display:swap;src:url(${b64('assets/fonts/' + file + '.woff2', 'font/woff2')}) format('woff2')}`).join('\n');

const spaCSS = `#app{display:block;min-height:60vh}
body.route-admin .hd,body.route-admin .ft,body.route-admin #veil{display:none!important}
body.route-admin{overflow:auto;animation:none}`;
const CSS = FF + '\n' + rd('assets/style.css') + '\n' + rd('assets/admin.css') + '\n' + spaCSS;

let APP = rd('assets/app.js');
APP = APP.split('src="assets/products/${IMG[p.slug] || p.slug + \'.jpg\'}"').join('src="${window.PHOTOS[p.slug]||\'\'}"');
APP = APP.split('`<img class="${cls}" src="assets/${base}.png" alt="Miels du Monde" onerror="this.onerror=null;this.src=\'assets/${base}.svg\'">`')
  .join('`<img class="${cls}" src="${variant===\'light\'?window.LOGO_LIGHT:window.LOGO}" alt="Miels du Monde">`');
APP = APP.split('`<img src="assets/logo.png" alt="" onerror="this.onerror=null;this.src=\'assets/logo.svg\'">`').join('`<img src="${window.LOGO}" alt="">`');
APP = APP.split("const slug = new URLSearchParams(location.search).get('p');").join("const slug = (window.__params&&window.__params.p) || new URLSearchParams(location.search).get('p');");
APP = APP.split("let filter = params.get('f') || 'all';").join("let filter = (window.__params&&window.__params.f) || params.get('f') || 'all';");
APP = APP.split("document.readyState === 'loading' ? addEventListener('DOMContentLoaded', boot) : boot();").join("window.__appReady=1;");

let ADM = rd('assets/admin.js');
ADM = ADM.split('document.body.innerHTML').join("document.getElementById('app').innerHTML");
ADM = ADM.split("document.body.className = '';").join("document.body.classList.add('admin');");
ADM = ADM.split("document.body.className = 'admin';").join("document.body.classList.add('admin');");
ADM = ADM.split('`<span class="thumb-mini"><img src="assets/products/${IMG[slug] || slug + \'.jpg\'}" alt="" onerror="this.style.opacity=0"></span>`')
  .join('`<span class="thumb-mini"><img src="${window.PHOTOS[slug]||\'\'}" alt=""></span>`');
ADM = ADM.split('<img src="assets/logo.png" alt="Miels du Monde" onerror="this.onerror=null;this.src=\'assets/logo.svg\'">').join('<img src="${window.LOGO}" alt="Miels du Monde">');
ADM = ADM.split('<img src="assets/logo-light.png" alt="Miels du Monde" onerror="this.onerror=null;this.src=\'assets/logo-light.svg\'">').join('<img src="${window.LOGO_LIGHT}" alt="Miels du Monde">');
ADM = ADM.replace(/\nboot\(\);\s*$/, '\nwindow.initAdmin=boot;\n');
ADM = '(function(){\n' + ADM + '\n})();';

const pages = { home: 'index.html', boutique: 'boutique.html', produit: 'produit.html', apropos: 'a-propos.html', faq: 'faq.html', checkout: 'checkout.html' };
const T = {};
for (const [name, file] of Object.entries(pages)) {
  const html = rd(file);
  const m = html.match(/<body[^>]*>([\s\S]*?)<div id="site-footer">/);
  if (!m) { console.error('no body match', file); process.exit(1); }
  T[name] = m[1].trim();
}

const GLUE = rd('build/glue.js');

const OUT = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#3e2809">
<meta name="description" content="Miels du Monde — Maison française de miels rares, importés en direct et analysés en laboratoire français.">
<title>Miels du Monde — Miels rares du monde, analysés en laboratoire</title>
<link rel="icon" type="image/png" href="${LOGO}">
<link rel="apple-touch-icon" href="${LOGO}">
<style>${CSS}</style>
</head>
<body>
<div id="app"></div>
<div id="site-footer"></div>
<div id="originModal" aria-hidden="true"></div>
<script type="text/plain" id="three-src">${THREE}</script>
<script>
window.PHOTOS=${JSON.stringify(PHOTOS)};
window.LOGO=${JSON.stringify(LOGO)};
window.LOGO_LIGHT=${JSON.stringify(LOGO_LIGHT)};
window.EARTH=${JSON.stringify(EARTH)};
window.__T=${JSON.stringify(T)};
</script>
<script>${APP}</script>
<script>${ADM}</script>
<script>${GLUE}</script>
</body>
</html>`;
fs.writeFileSync('miels-du-monde.html', OUT);
console.log('miels-du-monde.html:', (fs.statSync('miels-du-monde.html').size / 1024 / 1024).toFixed(2) + 'MB');
