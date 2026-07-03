/* ════════════════════════════════════════════════════════════════════
   MIELS DU MONDE · Script partagé (multi-pages)
   - Injecte header / méga-menu / panier / footer sur chaque page
   - Panier persistant entre les pages (localStorage)
   - Catalogue réel · repli gracieux si une photo est absente
   ════════════════════════════════════════════════════════════════════ */
"use strict";
const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const euro = n => (Number.isInteger(n) ? n : n.toFixed(2).replace('.', ',')) + '€';
const RM = matchMedia('(prefers-reduced-motion:reduce)').matches;
// Logo : votre vrai fichier assets/logo(.png) est utilisé s'il existe, sinon la recréation SVG.
// variant 'dark' = wordmark sombre (fond clair) · 'light' = wordmark crème (fond sombre)
const logoImg = (variant = 'dark', cls = '') => { const base = variant === 'light' ? 'logo-light' : 'logo';
  return `<img class="${cls}" src="assets/${base}.png" alt="Miels du Monde" onerror="this.onerror=null;this.src='assets/${base}.svg'">`; };

/* ─────────────── CATALOGUE (produits réels) ───────────────
   img : déposez le fichier dans assets/products/<slug>.jpg
   Les prix sont des valeurs par défaut — à ajuster selon votre boutique. */
const CATALOG = [
  { slug:'litchi', name:'Miel de Litchi', origin:{c:'Madagascar',f:'🇲🇬',city:'Est de Madagascar'},
    cat:'miel', price:24, old:28, tag:'Floral & fruité', hue:['#f0c98b','#d98a3a','#a8531f'], rating:5, count:96,
    desc:'Un miel clair et parfumé aux notes de fruits rouges.',
    lede:"Un miel rare et délicat, récolté au cœur des vergers de litchis de Madagascar. Sa fragrance fruitée en fait un miel à part.",
    story:["Sur la côte est de Madagascar, les litchis fleurissent brièvement chaque année. Les abeilles en tirent un miel clair, floral et subtilement fruité, aux notes de fruits rouges.",
      "Une récolte courte et limitée, tracée jusqu'à son apiculteur puis analysée en laboratoire français avant sa mise en vente."],
    tasting:[{ic:'🍓',t:'Fruité',d:'Notes de fruits rouges.'},{ic:'🌸',t:'Floral',d:'Parfum délicat de litchi.'},{ic:'💛',t:'Doux',d:'Rondeur en bouche.'},{ic:'🥐',t:'Tartine',d:'Idéal au petit-déjeuner.'}],
    texture:'Liquide, fin', nutrition:{'Énergie':'1 360 kJ / 320 kcal','Glucides':'79 g','— dont sucres':'78 g','Protéines':'0,3 g','Matières grasses':'0 g'} },
  { slug:'jujubier', name:'Miel de Jujubier', origin:{c:'Algérie',f:'🇩🇿',city:'Vallées du jujubier'},
    cat:'miel', price:34, old:39, tag:'Le plus rare', hue:['#e0a94e','#b3711f','#6e3a0c'], rating:5, count:128,
    desc:'Le cousin du Sidr : dense, ambré et résineux.',
    lede:"Un miel d'exception issu de l'arbre de jujubier (Sidr). Dense, ambré et résineux, c'est l'un des miels les plus recherchés au monde.",
    story:["Le jujubier pousse dans des vallées arides où il ne fleurit qu'un court moment. Son miel, cousin du célèbre Sidr, est dense, foncé et d'une profondeur aromatique remarquable.",
      "Une production confidentielle, récoltée à la main et analysée en laboratoire français pour en garantir l'authenticité."],
    tasting:[{ic:'🌰',t:'Résineux',d:'Caramel brun et datte.'},{ic:'🍯',t:'Dense',d:'Texture épaisse.'},{ic:'🔥',t:'Chaleureux',d:'Longueur boisée.'},{ic:'☕',t:'Nature',d:'Sublime en fin de repas.'}],
    texture:'Onctueux, dense', nutrition:{'Énergie':'1 380 kJ / 325 kcal','Glucides':'80 g','— dont sucres':'79 g','Protéines':'0,4 g','Matières grasses':'0 g'} },
  { slug:'curcuma', name:'Miel & Curcuma', origin:{c:'France',f:'🇫🇷',city:'Préparé en France'},
    cat:'prep', price:19, old:22, tag:'Bien-être', hue:['#f4cf5e','#e0a323','#b3701c'], rating:5, count:74,
    desc:'Préparation au miel et curcuma, dorée et réconfortante.',
    lede:"Une préparation à base de miel et de curcuma, alliant la douceur du miel à la chaleur épicée du curcuma.",
    story:["Nous associons un miel soigneusement sélectionné à du curcuma pour créer une préparation dorée, réconfortante et pleine de caractère.",
      "Préparée en France, sans additif superflu — le miel et l'épice, tout simplement."],
    tasting:[{ic:'🟡',t:'Épicé',d:'Chaleur du curcuma.'},{ic:'🍯',t:'Doux',d:'Rondeur du miel.'},{ic:'🍵',t:'Infusion',d:'Délicieux en boisson chaude.'},{ic:'🥄',t:'Cuillère',d:'Une cuillère par jour.'}],
    texture:'Crémeux', ingredients:'Miel (96%), curcuma (3%), poivre (1%)',
    nutrition:{'Énergie':'1 350 kJ / 318 kcal','Glucides':'78 g','— dont sucres':'76 g','Protéines':'0,4 g','Matières grasses':'0 g'} },
  { slug:'gelee-royale', name:'Miel, Gelée Royale, Pollen & Propolis', origin:{c:'France',f:'🇫🇷',city:'Préparé en France'},
    cat:'prep', price:29, old:34, tag:'Le trésor de la ruche', hue:['#caa46a','#8a6a3a','#4a3418'], rating:5, count:63,
    desc:'Le concentré fortifiant de la ruche.',
    lede:"Le trésor complet de la ruche : miel, gelée royale, pollen et propolis réunis dans une préparation fortifiante.",
    story:["Cette préparation réunit les quatre trésors de la ruche — miel, gelée royale, pollen et propolis — pour une synergie unique.",
      "Préparée en France, pensée comme une cure de vitalité à savourer chaque matin."],
    tasting:[{ic:'💪',t:'Fortifiant',d:'La vitalité de la ruche.'},{ic:'🌼',t:'Complet',d:'4 trésors réunis.'},{ic:'🌰',t:'Complexe',d:'Notes profondes.'},{ic:'🥄',t:'Cure',d:'Une cuillère à jeun.'}],
    texture:'Crémeux, dense', ingredients:'Miel, propolis 5%, pollen 5%, gelée royale 0,5%',
    nutrition:{'Énergie':'1 340 kJ / 316 kcal','Glucides':'77 g','— dont sucres':'74 g','Protéines':'0,8 g','Matières grasses':'0,2 g'} },
  { slug:'citron-gingembre', name:'Miel, Citron Vert & Gingembre', origin:{c:'France',f:'🇫🇷',city:'Préparé en France'},
    cat:'prep', price:19, old:22, tag:'Tonique', hue:['#e6e2a2','#c2b45a','#8a7a2e'], rating:5, count:81,
    desc:'Vif et vivifiant : miel, citron vert et gingembre.',
    lede:"Une préparation tonique et vivifiante, où le miel rencontre la fraîcheur du citron vert et le piquant du gingembre.",
    story:["Le miel s'associe au citron vert et au gingembre pour une préparation à la fois douce et vive, parfaite pour affronter l'hiver.",
      "Préparée en France, à savourer en infusion ou à la cuillère."],
    tasting:[{ic:'🍋',t:'Vif',d:'Fraîcheur du citron vert.'},{ic:'🫚',t:'Piquant',d:'Chaleur du gingembre.'},{ic:'🍵',t:'Infusion',d:'Idéal en boisson chaude.'},{ic:'❄️',t:'Hiver',d:'Le réconfort des saisons froides.'}],
    texture:'Crémeux', ingredients:'Miel (94%), gingembre (4%), citron vert (2%)',
    nutrition:{'Énergie':'1 350 kJ / 318 kcal','Glucides':'78 g','— dont sucres':'76 g','Protéines':'0,4 g','Matières grasses':'0 g'} },
  { slug:'nigelle', name:'Miel & Nigelle', origin:{c:'France',f:'🇫🇷',city:'Préparé en France'},
    cat:'prep', price:21, old:25, tag:'Habba Sawda', hue:['#9a9384','#55524a','#26241f'], rating:5, count:88,
    desc:'Miel et graine de nigelle, la précieuse « graine bénie ».',
    lede:"Une préparation au miel et à la nigelle (habba sawda), la fameuse « graine bénie », au caractère puissant et poivré.",
    story:["La nigelle, ou « graine bénie », est réputée depuis des millénaires. Nous l'associons à un miel soigneusement sélectionné pour une préparation au caractère affirmé.",
      "Préparée en France, à savourer en cure, à la petite cuillère."],
    tasting:[{ic:'⚫',t:'Poivré',d:'Caractère de la nigelle.'},{ic:'🍯',t:'Doux',d:'Adouci par le miel.'},{ic:'💪',t:'Tonique',d:'Une cure de vitalité.'},{ic:'🥄',t:'Cuillère',d:'Une cuillère à jeun.'}],
    texture:'Crémeux, grainé', ingredients:'Miel (94%), graines de nigelle (6%)',
    nutrition:{'Énergie':'1 350 kJ / 318 kcal','Glucides':'77 g','— dont sucres':'75 g','Protéines':'0,6 g','Matières grasses':'0,5 g'} },
  { slug:'hibiscus', name:'Miel & Hibiscus', origin:{c:'France',f:'🇫🇷',city:'Préparé en France'},
    cat:'prep', price:21, old:25, tag:'Floral & acidulé', hue:['#d06b82','#9c2846','#5a1022'], rating:5, count:71,
    desc:'Miel et fleur d\'hibiscus, rubis et délicatement acidulé.',
    lede:"Une préparation au miel et à la fleur d'hibiscus, d'une couleur rubis intense et d'une acidité délicate.",
    story:["La fleur d'hibiscus offre sa robe rubis et ses notes acidulées à cette préparation au miel, aussi belle que gourmande.",
      "Préparée en France, sublime en infusion, sur un fromage frais ou à la cuillère."],
    tasting:[{ic:'🌺',t:'Floral',d:'Parfum d\'hibiscus.'},{ic:'🍒',t:'Acidulé',d:'Fraîcheur fruitée.'},{ic:'💗',t:'Rubis',d:'Couleur intense.'},{ic:'🧀',t:'Accord',d:'Superbe sur un fromage frais.'}],
    texture:'Crémeux', ingredients:'Miel (91%), hibiscus (9%)',
    nutrition:{'Énergie':'1 350 kJ / 318 kcal','Glucides':'78 g','— dont sucres':'76 g','Protéines':'0,4 g','Matières grasses':'0 g'} }
];
const byslug = s => CATALOG.find(p => p.slug === s);
const FREE = 79;

/* fichiers photos réels (fournis par la maison) */
const IMG = { litchi:'litchi.webp', jujubier:'jujubier.webp', curcuma:'curcuma.webp',
  'gelee-royale':'gelee-royale.webp', 'citron-gingembre':'citron-gingembre.webp',
  nigelle:'nigelle.webp', hibiscus:'hibiscus.webp' };
/* image produit avec repli gracieux (dégradé + nom si le fichier manque) */
function pimg(p, cls = '') {
  const bg = `linear-gradient(150deg,${p.hue[0]},${p.hue[1]} 55%,${p.hue[2]})`;
  return `<div class="pvis ${cls}" style="--fb:${bg}">
    <img src="assets/products/${IMG[p.slug] || p.slug + '.jpg'}" alt="${p.name}" loading="lazy"
      onerror="this.parentNode.classList.add('noimg');this.remove()">
    <span class="ph">${p.name}</span></div>`;
}
const starsHTML = n => Array.from({length:5},(_,i)=>`<svg class="ico" viewBox="0 0 24 24" ${i<n?'':'opacity=".25"'}><path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L4.2 7.7l5.4-.8z"/></svg>`).join('');

function productCard(p) {
  return `<article class="card reveal" data-slug="${p.slug}" role="button" tabindex="0" aria-label="${p.name}">
    <a class="card-vis" href="produit.html?p=${p.slug}" aria-label="${p.name}">
      ${pimg(p)}
      <span class="card-tag">${p.tag}</span>
      <button class="card-fav" aria-label="Favori" data-fav="${p.slug}"><svg class="ico" viewBox="0 0 24 24" style="width:18px;height:18px"><path d="M12 21s-7-4.3-7-10a4 4 0 017-2.6A4 4 0 0119 11c0 5.7-7 10-7 10z"/></svg></button>
      <span class="card-quick">Découvrir</span>
    </a>
    <div class="card-body">
      <div class="org">${p.origin.f} ${p.origin.c}</div>
      <h3>${p.name}</h3>
      <p class="desc">${p.desc}</p>
      <div class="card-foot"><div class="price"><s>${euro(p.old)}</s>${euro(p.price)}</div><div class="stars">${starsHTML(p.rating)}</div></div>
    </div></article>`;
}

/* ─────────────── PANIER (localStorage) ─────────────── */
const CART_KEY = 'mdm_cart_v1';
const loadCart = () => { try { return new Map(Object.entries(JSON.parse(localStorage.getItem(CART_KEY) || '{}'))); } catch { return new Map(); } };
const saveCart = () => localStorage.setItem(CART_KEY, JSON.stringify(Object.fromEntries(cart)));
let cart = loadCart();
function addToCart(slug, qty = 1, fromEl) { cart.set(slug, (cart.get(slug) || 0) + qty); saveCart(); renderCart(); pulseCart(); if (fromEl) flyToCart(fromEl, slug); toast(`${byslug(slug).name} ajouté`); }
function setQty(slug, q) { q <= 0 ? cart.delete(slug) : cart.set(slug, q); saveCart(); renderCart(); pulseCart(); }
const cartCount = () => [...cart.values()].reduce((a, b) => a + b, 0);
const cartTotal = () => [...cart].reduce((a, [s, q]) => a + byslug(s).price * q, 0);
function pulseCart() { const c = $('#cartCount'), n = cartCount(); if (!c) return; c.textContent = n; c.classList.toggle('on', n > 0); c.animate([{ transform: 'scale(1.5)' }, { transform: 'scale(1)' }], { duration: 400, easing: 'cubic-bezier(.22,1,.36,1)' }); }
function renderCart() {
  const wrap = $('#cartItems'), foot = $('#cartFoot'); if (!wrap) return;
  if (cart.size === 0) {
    wrap.innerHTML = `<div class="cart-empty"><svg class="ico" viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7L6 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg><p>Votre panier est vide.</p><a class="btn btn-ghost" href="boutique.html">Voir la boutique</a></div>`;
    foot.hidden = true; $('#cartShip').innerHTML = `<span>Plus que <b>${euro(FREE)}</b> pour la livraison offerte 🎁</span><div class="bar"><i></i></div>`; return;
  }
  wrap.innerHTML = [...cart].map(([s, q]) => { const p = byslug(s); return `
    <div class="ci"><div class="thumb">${pimg(p)}</div>
      <div class="info"><div class="o">${p.origin.f} ${p.origin.c}</div><h4>${p.name}</h4>
        <div class="qty"><button data-act="dec" data-slug="${s}" aria-label="Moins">−</button><span>${q}</span><button data-act="inc" data-slug="${s}" aria-label="Plus">+</button></div></div>
      <div class="right"><button class="rm" data-act="rm" data-slug="${s}">Retirer</button><b>${euro(p.price * q)}</b></div></div>`; }).join('');
  const sub = cartTotal(), ship = sub >= FREE ? 0 : 5.9;
  foot.hidden = false; $('#cartSub').textContent = euro(sub);
  $('#cartShipCost').textContent = ship === 0 ? 'Offerte' : euro(ship);
  $('#cartTot').textContent = euro(sub + ship);
  $('#cartShip').innerHTML = sub >= FREE
    ? `<span>🎁 Livraison <b>offerte</b> débloquée !</span><div class="bar"><i style="width:100%"></i></div>`
    : `<span>Plus que <b>${euro(FREE - sub)}</b> pour la livraison offerte</span><div class="bar"><i style="width:${Math.min(100, sub / FREE * 100)}%"></i></div>`;
}
function flyToCart(from, slug) {
  const p = byslug(slug), r = from.getBoundingClientRect(), t = $('#openCart').getBoundingClientRect();
  const f = document.createElement('div'); f.className = 'fly';
  f.innerHTML = pimg(p); f.style.left = r.left + r.width / 2 - 26 + 'px'; f.style.top = r.top + r.height / 2 - 26 + 'px';
  document.body.appendChild(f);
  f.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: `translate(${t.left - r.left - r.width / 2 + 26}px,${t.top - r.top - r.height / 2 + 26}px) scale(.2)`, opacity: .3 }], { duration: 750, easing: 'cubic-bezier(.5,.05,.4,1)' }).onfinish = () => f.remove();
}
const openCart = () => { $('#cart').classList.add('on'); $('#scrim').classList.add('on'); document.body.classList.add('lock'); };
const closeCart = () => { $('#cart').classList.remove('on'); $('#scrim').classList.remove('on'); document.body.classList.remove('lock'); };
// navigation avec voile "miel"
function goTo(href) { const v = $('#veil'); if (RM || !v) { location.href = href; return; } v.classList.add('on'); setTimeout(() => { location.href = href; }, 460); }

/* ─────────────── TOAST ─────────────── */
let toastT; function toast(msg) { const el = $('#toast'); if (!el) return; $('#toastMsg').textContent = msg; el.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove('on'), 2600); }

/* ─────────────── CHROME (header / menu / footer / panier) ─────────────── */
const NAV = [['Boutique', 'boutique.html'], ['À propos', 'a-propos.html'], ['FAQ', 'faq.html']];
function injectChrome() {
  const path = location.pathname.split('/').pop() || 'index.html';
  const navLinks = NAV.map(([t, h]) => `<a href="${h}" class="${path === h ? 'active' : ''}">${t}</a>`).join('');
  const header = document.createElement('header'); header.className = 'hd'; header.id = 'hd';
  if (document.body.dataset.head === 'light') header.classList.add('light');
  header.innerHTML = `
    <a class="logo" href="index.html" aria-label="Miels du Monde — accueil">${logoImg('dark', 'lg-dark')}${logoImg('light', 'lg-light')}</a>
    <nav class="top-nav" aria-label="Principale">${navLinks}</nav>
    <div class="hd-act">
      <a class="iconbtn" href="boutique.html" aria-label="Rechercher"><svg class="ico" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></a>
      <button class="iconbtn" id="openCart" aria-label="Panier"><svg class="ico" viewBox="0 0 24 24"><path d="M6 8h12l-1 12H7L6 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg><span class="cart-count" id="cartCount">0</span></button>
      <button class="iconbtn burger" id="openMenu" aria-label="Menu"><svg class="ico" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
    </div>`;
  document.body.prepend(header);

  const menu = document.createElement('nav'); menu.id = 'menu'; menu.setAttribute('aria-label', 'Menu');
  menu.innerHTML = `
    <button class="menu-close" id="closeMenu" aria-label="Fermer"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
    <div class="menu-grid">
      <div class="menu-links">
        <a href="boutique.html">La boutique <span>01</span></a>
        <a href="boutique.html?f=miel">Miels d'origine <span>02</span></a>
        <a href="boutique.html?f=prep">Préparations au miel <span>03</span></a>
        <a href="a-propos.html">La maison <span>04</span></a>
        <a href="faq.html">FAQ <span>05</span></a>
      </div>
      <aside class="menu-side"><h4>Des miels analysés</h4>
        <p>Chaque miel est importé en direct puis analysé dans un laboratoire français. L'authenticité, prouvée.</p></aside>
    </div>`;
  document.body.append(menu);

  const cartWrap = document.createElement('div');
  cartWrap.innerHTML = `
    <div id="scrim"></div>
    <aside id="cart" aria-label="Panier">
      <div class="cart-h"><h3>Votre panier</h3><button class="iconbtn" id="closeCart" aria-label="Fermer"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
      <div class="cart-ship" id="cartShip"></div>
      <div class="cart-items" id="cartItems"></div>
      <div class="cart-f" id="cartFoot" hidden>
        <div class="line"><span>Sous-total</span><span id="cartSub">0€</span></div>
        <div class="line"><span>Livraison</span><span id="cartShipCost">—</span></div>
        <div class="tot" id="cartTot">0€</div>
        <button class="btn btn-gold" id="cartCheckout">Passer commande</button>
        <div class="re">Paiement sécurisé · Satisfait ou remboursé 14 jours</div>
      </div>
    </aside>
    <div id="toast" role="status"><svg class="ico" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg><span id="toastMsg">Ajouté</span></div>`;
  document.body.append(cartWrap);

  const foot = $('#site-footer');
  if (foot) foot.outerHTML = `
    <footer class="ft"><div class="shell">
      <div class="ft-top">
        <div class="ft-brand"><a class="logo" href="index.html">${logoImg('light')}</a>
          <p>Maison de miels rares, importés en direct et analysés en laboratoire français. La rareté, prouvée.</p>
          <div class="socials">
            <a href="https://www.tiktok.com/@mielsdumonde" aria-label="TikTok"><svg class="ico" viewBox="0 0 24 24" style="width:18px;height:18px"><path d="M15 4v8.5a4 4 0 1 1-4-4"/><path d="M15 4a4.5 4.5 0 0 0 4.5 4.5"/></svg></a>
            <a href="#" aria-label="Instagram"><svg class="ico" viewBox="0 0 24 24" style="width:18px;height:18px"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></a>
            <a href="#" aria-label="Email"><svg class="ico" viewBox="0 0 24 24" style="width:18px;height:18px"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg></a>
          </div></div>
        <div class="ft-col"><h5>Boutique</h5><a href="boutique.html">Tous les produits</a><a href="boutique.html?f=miel">Miels d'origine</a><a href="boutique.html?f=prep">Préparations</a></div>
        <div class="ft-col"><h5>Maison</h5><a href="a-propos.html">Qui sommes-nous</a><a href="faq.html">FAQ</a><a href="#">Contact</a></div>
        <div class="ft-col"><h5>Service</h5><a href="#">Livraison &amp; retours</a><a href="#">Suivi de commande</a><a href="#">CGV &amp; mentions légales</a></div>
      </div>
      <div class="ft-bar"><span>© ${new Date().getFullYear()} Miels du Monde — Tous droits réservés.</span>
        <div class="pay"><span>VISA</span><span>MASTERCARD</span><span>PAYPAL</span></div></div>
    </div></footer>`;

  // events
  $('#openCart').onclick = openCart; $('#closeCart').onclick = closeCart; $('#scrim').onclick = closeCart;
  $('#openMenu').onclick = () => { menu.classList.add('open'); document.body.classList.add('lock'); };
  $('#closeMenu').onclick = () => { menu.classList.remove('open'); document.body.classList.remove('lock'); };
  $('#cartItems').addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (!b) return; const s = b.dataset.slug, n = cart.get(s) || 0; if (b.dataset.act === 'inc') setQty(s, n + 1); else if (b.dataset.act === 'dec') setQty(s, n - 1); else if (b.dataset.act === 'rm') setQty(s, 0); });
  addEventListener('keydown', e => { if (e.key === 'Escape') { closeCart(); menu.classList.remove('open'); document.body.classList.remove('lock'); } });
  // header solid on scroll (uniquement pour header transparent sur hero)
  if (!header.classList.contains('light')) { const on = () => header.classList.toggle('solid', scrollY > 40); addEventListener('scroll', on, { passive: true }); on(); }

  // voile de transition entre les pages
  const veil = document.createElement('div'); veil.id = 'veil';
  veil.innerHTML = `<img src="assets/logo.png" alt="" onerror="this.onerror=null;this.src='assets/logo.svg'">`;
  document.body.append(veil);
  if (!RM) {
    document.addEventListener('click', e => {
      const a = e.target.closest('a'); if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href[0] === '#' || /^(https?:|mailto:|tel:)/.test(href) || a.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault(); goTo(href);
    });
  }
  $('#cartCheckout').onclick = () => goTo('checkout.html');
}

/* ─────────────── REVEAL ─────────────── */
const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } }), { threshold: .12, rootMargin: '0px 0px -6% 0px' });
function observeReveals(root = document) { $$('.reveal', root).forEach(el => RM ? el.classList.add('in') : io.observe(el)); }
function animateCounters(root = document) {
  $$('[data-count]', root).forEach(el => new IntersectionObserver((es, ob) => es.forEach(en => {
    if (!en.isIntersecting) return; ob.disconnect();
    const end = parseFloat(el.dataset.count), suf = el.dataset.suffix || '', dec = end % 1 !== 0; let s = null;
    const step = t => { s = s || t; const k = Math.min(1, (t - s) / 1100); el.textContent = (dec ? (end * (1 - Math.pow(1 - k, 3))).toFixed(1) : Math.round(end * (1 - Math.pow(1 - k, 3)))) + suf; if (k < 1) requestAnimationFrame(step); };
    RM ? el.textContent = (dec ? end.toFixed(1) : end) + suf : requestAnimationFrame(step);
  }), { threshold: .5 }).observe(el));
}

/* ─────────────── RENDU PAR PAGE ─────────────── */
function renderShop() {
  const grid = $('#shopGrid'); if (!grid) return;
  const params = new URLSearchParams(location.search);
  let filter = params.get('f') || 'all';
  const draw = f => { filter = f; grid.innerHTML = CATALOG.filter(p => f === 'all' || p.cat === f).map(productCard).join(''); observeReveals(grid); bindCards(grid);
    $$('#shopFilters button').forEach(b => b.classList.toggle('sel', b.dataset.f === f)); };
  $('#shopFilters')?.addEventListener('click', e => { const b = e.target.closest('button'); if (b) draw(b.dataset.f); });
  draw(filter);
}
function renderFeatured() {
  const grid = $('#featGrid'); if (!grid) return;
  grid.innerHTML = CATALOG.slice(0, 3).map(productCard).join(''); observeReveals(grid); bindCards(grid);
}
function bindCards(root) {
  $$('.card-fav', root).forEach(b => b.addEventListener('click', e => { e.preventDefault(); toast('Ajouté aux favoris ♥'); }));
}
function renderProduct() {
  const host = $('#product'); if (!host) return;
  const slug = new URLSearchParams(location.search).get('p');
  const p = byslug(slug) || CATALOG[0];
  document.title = `${p.name} — Miels du Monde`;
  const cross = CATALOG.filter(x => x.slug !== p.slug).slice(0, 3);
  const nut = Object.entries(p.nutrition).map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  const FAQ = [
    ['Ce miel est-il analysé ?', "Oui. Chaque lot est analysé dans un laboratoire français (origine florale, absence de sirops ajoutés, taux d'HMF). Le rapport est disponible sur demande."],
    ['Comment le conserver ?', "À l'abri de la lumière et de la chaleur. Une cristallisation est un gage de pureté ; réchauffez doucement au bain-marie pour refluidifier."],
    ['Livraison ?', "Expédition sous 48 à 72h. Livraison offerte dès 79€ en point relais, en France et dans l'Union européenne."]
  ];
  host.innerHTML = `
  <div class="pdp-hero shell">
    <div class="pdp-media">
      <div class="pdp-main">${pimg(p)}</div>
      <div class="pdp-thumbs">
        <button class="sel">${pimg(p)}</button>
        <button>${pimg(p)}</button>
        <button>${pimg(p)}</button>
      </div>
    </div>
    <div class="pdp-info reveal in">
      <div class="org">${p.origin.f} ${p.origin.c} · ${p.origin.city}</div>
      <h1>${p.name}</h1>
      <div class="rr"><div class="stars">${starsHTML(p.rating)}</div> ${p.rating}.0 · ${p.count} avis</div>
      <p class="lede">${p.lede}</p>
      <div class="pdp-price"><span class="p">${euro(p.price)}</span><s>${euro(p.old)}</s><span class="save">−${Math.round((1 - p.price / p.old) * 100)}%</span></div>
      <div class="pdp-note">Pot de 250g · Édition limitée · ${p.texture}${p.ingredients ? ' · ' + p.ingredients : ''}</div>
      <div class="pdp-buy">
        <div class="qtybox"><button data-q="-1" aria-label="Moins">−</button><span id="pq">1</span><button data-q="1" aria-label="Plus">+</button></div>
        <button class="btn btn-gold btn-lg" id="pAdd">Ajouter au panier · <span id="pTot">${euro(p.price)}</span></button>
      </div>
      <div class="assure">
        <div><svg class="ico" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>Analysé en labo français</div>
        <div><svg class="ico" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>Expédié sous 48h</div>
        <div><svg class="ico" viewBox="0 0 24 24"><path d="M12 21s-7-4.3-7-10a7 7 0 0114 0c0 5.7-7 10-7 10z"/></svg>Traçabilité totale</div>
      </div>
      <div class="acc" id="pAcc">
        <div class="acc-item"><button class="acc-q">Dégustation & conseils<svg class="ico" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button><div class="acc-a"><div class="in">Savourez à température ambiante, à la petite cuillère. Évitez de chauffer au-delà de 40°C pour préserver les enzymes. Texture : ${p.texture}.</div></div></div>
        <div class="acc-item"><button class="acc-q">Valeurs nutritionnelles<svg class="ico" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button><div class="acc-a"><div class="in"><table class="nut-table">${nut}</table><p class="muted" style="font-size:.82rem;margin-top:.6rem">Pour 100 g${p.ingredients ? ' · Ingrédients : ' + p.ingredients : ''}</p></div></div></div>
        ${FAQ.map(([q, a]) => `<div class="acc-item"><button class="acc-q">${q}<svg class="ico" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button><div class="acc-a"><div class="in">${a}</div></div></div>`).join('')}
      </div>
    </div>
  </div>

  <section class="blk cream"><div class="shell">
    <div class="sec-head center reveal"><span class="eyebrow center">L'histoire</span><h2>De la ruche à votre table</h2></div>
    <div class="prose reveal">${p.story.map(s => `<p>${s}</p>`).join('')}</div>
    <div class="tnotes">${p.tasting.map(t => `<div class="tnote reveal"><div class="ic">${t.ic}</div><h4>${t.t}</h4><p>${t.d}</p></div>`).join('')}</div>
  </div></section>

  <section class="blk"><div class="shell">
    <div class="sec-head reveal"><span class="eyebrow">À découvrir aussi</span><h2>Complétez la dégustation</h2></div>
    <div class="card-grid" id="crossGrid">${cross.map(productCard).join('')}</div>
  </div></section>`;

  // interactions
  let q = 1; const upd = () => { $('#pq').textContent = q; $('#pTot').textContent = euro(p.price * q); };
  $('.qtybox').addEventListener('click', e => { const b = e.target.closest('[data-q]'); if (!b) return; q = Math.max(1, q + +b.dataset.q); upd(); });
  $('#pAdd').onclick = () => addToCart(p.slug, q, $('.pdp-main'));
  $('#pAcc').addEventListener('click', e => { const btn = e.target.closest('.acc-q'); if (!btn) return; const it = btn.parentElement, a = it.querySelector('.acc-a'); const open = it.classList.toggle('open'); a.style.maxHeight = open ? a.scrollHeight + 'px' : 0; });
  $$('.pdp-thumbs button').forEach(b => b.onclick = () => { $$('.pdp-thumbs button').forEach(x => x.classList.remove('sel')); b.classList.add('sel'); });
  observeReveals(host); bindCards(host);
}

/* ─────────────── PAIEMENT (checkout) ─────────────── */
const PAY = {
  apple: `<svg viewBox="0 0 34 20" aria-hidden="true"><path fill="currentColor" d="M8.2 6.1c-.4.5-1 .8-1.6.75-.08-.62.22-1.28.58-1.68.4-.48 1.06-.82 1.62-.84.06.64-.2 1.28-.6 1.77zm.58.92c-.9-.05-1.66.5-2.09.5-.44 0-1.1-.48-1.8-.47-.93.01-1.78.54-2.26 1.37-.96 1.66-.25 4.12.69 5.47.46.66 1 1.4 1.72 1.37.68-.03.94-.44 1.77-.44.83 0 1.06.44 1.78.43.74-.01 1.2-.67 1.65-1.33.52-.76.74-1.5.75-1.53-.02-.01-1.44-.55-1.45-2.17-.01-1.36 1.1-2.01 1.16-2.05-.63-.94-1.62-1.04-1.97-1.06z"/><text x="14" y="14.5" font-family="-apple-system,Helvetica,Arial" font-size="12" font-weight="600" fill="currentColor">Pay</text></svg>`,
  google: `<span style="font-size:1rem"><b style="color:#4285f4">G</b> Pay</span>`,
  paypal: `<b style="font-style:italic;font-size:1rem"><span style="color:#003087">Pay</span><span style="color:#0070e0">Pal</span></b>`,
  bc: `<span style="display:inline-flex;align-items:center;gap:.35rem"><span style="display:inline-flex"><span style="width:13px;height:13px;border-radius:50%;background:#0057a3"></span><span style="width:13px;height:13px;border-radius:50%;background:#ffd800;margin-left:-6px"></span></span><b style="color:#004e91;font-size:.9rem">Bancontact</b></span>`
};
const CARD_BRANDS = `<svg viewBox="0 0 34 22" aria-label="Visa"><rect width="34" height="22" rx="4" fill="#1a1f71"/><text x="17" y="15" text-anchor="middle" fill="#fff" font-family="Arial" font-weight="700" font-style="italic" font-size="10">VISA</text></svg>
  <svg viewBox="0 0 34 22" aria-label="Mastercard"><rect width="34" height="22" rx="4" fill="#232323"/><circle cx="14" cy="11" r="6" fill="#eb001b"/><circle cx="20" cy="11" r="6" fill="#f79e1b" opacity=".9"/></svg>`;

function renderCheckout() {
  const host = $('#checkout'); if (!host) return;
  if (cart.size === 0) { host.innerHTML = `<div class="co-empty shell"><h2>Votre panier est vide</h2><p class="muted" style="margin-bottom:1.5rem">Ajoutez un miel d'exception pour passer commande.</p><a href="boutique.html" class="btn btn-gold btn-lg">Voir la boutique</a></div>`; return; }

  const state = { promo: false, ship: 'relais', method: 'card' };
  const sub = () => cartTotal();
  const disc = () => state.promo ? sub() * 0.15 : 0;
  const shipCost = () => { const s = sub() - disc(); if (state.ship === 'domicile') return 5.9; return s >= FREE ? 0 : 3.9; };
  const total = () => sub() - disc() + shipCost();

  host.innerHTML = `
  <div class="co-wrap shell">
    <div class="co-main">
      <div class="crumb" style="color:var(--ink-mut);margin-bottom:.4rem"><a href="index.html">Accueil</a> · Paiement</div>
      <h1 style="font-size:clamp(2rem,4.5vw,3rem);font-weight:500;margin-bottom:2rem">Paiement sécurisé</h1>

      <div class="co-sec">
        <h3><span class="step">1</span> Contact & livraison</h3>
        <div class="field"><label>E-mail</label><input type="email" id="fEmail" placeholder="vous@email.com" autocomplete="email"></div>
        <div class="field-row">
          <div class="field"><label>Prénom</label><input id="fFirst" autocomplete="given-name"></div>
          <div class="field"><label>Nom</label><input id="fLast" autocomplete="family-name"></div>
        </div>
        <div class="field"><label>Adresse</label><input id="fAddr" autocomplete="address-line1"></div>
        <div class="field-row-3">
          <div class="field"><label>Ville</label><input id="fCity" autocomplete="address-level2"></div>
          <div class="field"><label>Code postal</label><input id="fZip" inputmode="numeric" autocomplete="postal-code"></div>
          <div class="field"><label>Pays</label><select id="fCountry"><option>France</option><option>Belgique</option><option>Luxembourg</option><option>Pays-Bas</option><option>Espagne</option><option>Portugal</option><option>Italie</option></select></div>
        </div>
      </div>

      <div class="co-sec">
        <h3><span class="step">2</span> Mode de livraison</h3>
        <div class="ship-opts" id="shipOpts">
          <div class="ship-opt sel" data-ship="relais"><span class="radio"></span><div class="t"><b>Point Relais</b><span>Livraison sous 48–72h</span></div><span class="pr" id="prRelais"></span></div>
          <div class="ship-opt" data-ship="domicile"><span class="radio"></span><div class="t"><b>À domicile</b><span>Livraison sous 48–72h</span></div><span class="pr">5,90€</span></div>
        </div>
      </div>
    </div>

    <aside class="co-summary">
      <h3>Votre commande</h3>
      <div id="coItems"></div>
      <div class="promo"><input id="promoInput" placeholder="Code promo" value=""><button id="promoBtn">Appliquer</button></div>
      <div class="sum-lines">
        <div class="sum-line"><span>Sous-total</span><span id="sSub"></span></div>
        <div class="sum-line disc" id="sDiscLine" hidden><span>Réduction (BIENVENUE15)</span><span id="sDisc"></span></div>
        <div class="sum-line"><span>Livraison</span><span id="sShip"></span></div>
        <div class="sum-tot"><span class="l">Total</span><span class="v" id="sTot"></span></div>
      </div>

      <div class="co-pay-block">
        <div class="pay-express">
          <button class="pm-btn pm-apple" data-express="Apple Pay">${PAY.apple}</button>
          <button class="pm-btn pm-google" data-express="Google Pay">${PAY.google}</button>
          <button class="pm-btn pm-paypal" data-express="PayPal">${PAY.paypal}</button>
          <button class="pm-btn pm-bc" data-express="Bancontact">${PAY.bc}</button>
        </div>
        <div class="co-divider">ou payer par carte</div>
        <div class="pm-list" id="pmList">
          <div class="pm-opt sel" data-method="card">
            <div class="pm-head"><span class="radio"></span><span class="lbl">Carte bancaire</span><span class="brands">${CARD_BRANDS}</span></div>
            <div class="pm-body"><div class="in">
              <div class="field"><label>Numéro de carte</label><input id="cNum" inputmode="numeric" placeholder="1234 5678 9012 3456" maxlength="19"></div>
              <div class="field-row">
                <div class="field"><label>Expiration</label><input id="cExp" inputmode="numeric" placeholder="MM/AA" maxlength="5"></div>
                <div class="field"><label>CVC</label><input id="cCvc" inputmode="numeric" placeholder="123" maxlength="4"></div>
              </div>
              <div class="field"><label>Nom sur la carte</label><input id="cName" autocomplete="cc-name"></div>
            </div></div>
          </div>
          <div class="pm-opt" data-method="paypal">
            <div class="pm-head"><span class="radio"></span><span class="lbl">PayPal</span><span class="brands">${PAY.paypal}</span></div>
            <div class="pm-body"><div class="in"><p class="muted" style="font-size:.86rem">Vous serez redirigé vers PayPal pour finaliser le paiement.</p></div></div>
          </div>
          <div class="pm-opt" data-method="bancontact">
            <div class="pm-head"><span class="radio"></span><span class="lbl">Bancontact</span><span class="brands">${PAY.bc}</span></div>
            <div class="pm-body"><div class="in"><p class="muted" style="font-size:.86rem">Redirection sécurisée vers Bancontact à la validation.</p></div></div>
          </div>
        </div>
        <button class="btn btn-gold btn-lg co-pay" id="coPay">Payer <span id="payTot"></span></button>
        <div class="co-legal"><svg class="ico" viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 018 0v3"/></svg> Paiement chiffré SSL · Données jamais stockées</div>
      </div>

      <div class="co-badges">
        <div><svg class="ico" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg> Miel analysé en laboratoire français</div>
        <div><svg class="ico" viewBox="0 0 24 24"><path d="M12 21s-7-4.3-7-10a7 7 0 0114 0c0 5.7-7 10-7 10z"/></svg> Satisfait ou remboursé 14 jours</div>
      </div>
    </aside>
  </div>

  <div id="coProcessing"><div><div class="spin"></div><p>Paiement en cours…</p></div></div>
  <div id="coSuccess"><div class="suc-in">
    <div class="suc-check"><svg class="ico" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg></div>
    <h1>Merci pour votre commande</h1>
    <p>Un e-mail de confirmation vous a été envoyé. Vos miels, analysés en laboratoire, sont préparés avec soin et expédiés sous 48 à 72h.</p>
    <div class="suc-order"><span class="lb">Numéro de commande</span><span class="no" id="ordNo"></span></div>
    <div><a href="index.html" class="btn btn-gold btn-lg">Retour à l'accueil</a></div>
  </div></div>`;

  const drawSummary = () => {
    $('#coItems').innerHTML = [...cart].map(([s, q]) => { const p = byslug(s); return `
      <div class="co-item"><div class="thumb">${pimg(p)}<span class="qb">${q}</span></div>
        <div class="info"><div class="o">${p.origin.f} ${p.origin.c}</div><h4>${p.name}</h4>
          <div class="q"><button data-cq="dec" data-slug="${s}">−</button>${q}<button data-cq="inc" data-slug="${s}">+</button></div></div>
        <b>${euro(p.price * q)}</b></div>`; }).join('');
    $('#prRelais').textContent = (sub() - disc()) >= FREE ? 'Offerte' : '3,90€';
    $('#sSub').textContent = euro(sub());
    $('#sDiscLine').hidden = !state.promo; $('#sDisc').textContent = '−' + euro(disc());
    $('#sShip').textContent = shipCost() === 0 ? 'Offerte' : euro(shipCost());
    $('#sTot').innerHTML = euro(total()) + ' <small>TTC</small>';
    $('#payTot').textContent = euro(total());
  };
  drawSummary();

  // quantités dans le résumé
  $('#coItems').addEventListener('click', e => { const b = e.target.closest('[data-cq]'); if (!b) return; const s = b.dataset.slug, n = cart.get(s) || 0; setQty(s, b.dataset.cq === 'inc' ? n + 1 : n - 1); if (cart.size === 0) return renderCheckout(); drawSummary(); });
  // promo
  $('#promoBtn').onclick = () => { const v = $('#promoInput').value.trim().toUpperCase(); if (v === 'BIENVENUE15') { state.promo = true; toast('Code BIENVENUE15 appliqué · −15%'); } else { toast('Code promo invalide'); } drawSummary(); };
  // livraison
  $('#shipOpts').addEventListener('click', e => { const o = e.target.closest('.ship-opt'); if (!o) return; state.ship = o.dataset.ship; $$('#shipOpts .ship-opt').forEach(x => x.classList.toggle('sel', x === o)); drawSummary(); });
  // méthode
  $('#pmList').addEventListener('click', e => { const o = e.target.closest('.pm-opt'); if (!o) return; state.method = o.dataset.method; $$('#pmList .pm-opt').forEach(x => x.classList.toggle('sel', x === o)); });
  // formatage carte
  $('#cNum').addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim(); });
  $('#cExp').addEventListener('input', e => { let v = e.target.value.replace(/\D/g, '').slice(0, 4); if (v.length >= 3) v = v.slice(0, 2) + '/' + v.slice(2); e.target.value = v; });
  $('#cCvc').addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g, ''); });

  const need = (id, cond) => { const el = $(id); const ok = !!cond(el.value.trim()); el.classList.toggle('err', !ok); return ok; };
  const recordOrder = (methodLabel) => {
    const no = 'MDM-' + Math.random().toString(36).slice(2, 8).toUpperCase();
    const email = $('#fEmail').value.trim();
    const first = $('#fFirst').value.trim() || (email.split('@')[0] || 'Client');
    const order = { no, date: new Date().toISOString(),
      customer: { email, first, last: $('#fLast').value.trim(), addr: $('#fAddr').value.trim(),
        city: $('#fCity').value.trim(), zip: $('#fZip').value.trim(), country: $('#fCountry').value },
      items: [...cart].map(([s, q]) => { const p = byslug(s); return { slug: s, name: p.name, qty: q, price: p.price, origin: p.origin.c }; }),
      subtotal: sub(), discount: disc(), shipping: shipCost(), total: total(),
      payment: methodLabel || 'Carte bancaire', delivery: state.ship === 'domicile' ? 'À domicile' : 'Point Relais', status: 'Payée' };
    const all = JSON.parse(localStorage.getItem('mdm_orders') || '[]'); all.unshift(order);
    localStorage.setItem('mdm_orders', JSON.stringify(all)); return no;
  };
  const pay = (express, methodLabel) => {
    let ok = need('#fEmail', v => /.+@.+\..+/.test(v));
    if (!express) { ok = need('#fFirst', v => v) & ok; ok = need('#fLast', v => v) & ok; ok = need('#fAddr', v => v) & ok; ok = need('#fCity', v => v) & ok; ok = need('#fZip', v => v.length >= 4) & ok;
      if (state.method === 'card') { ok = need('#cNum', v => v.replace(/\s/g, '').length >= 13) & ok; ok = need('#cExp', v => v.length === 5) & ok; ok = need('#cCvc', v => v.length >= 3) & ok; ok = need('#cName', v => v) & ok; } }
    if (!ok) { toast('Veuillez compléter les champs surlignés'); const first = $('.err'); first && first.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    $('#coProcessing').classList.add('on');
    setTimeout(() => {
      const no = recordOrder(methodLabel);
      $('#coProcessing').classList.remove('on');
      $('#ordNo').textContent = no;
      cart.clear(); saveCart(); pulseCart();
      $('#coSuccess').classList.add('on'); document.body.classList.add('lock');
    }, 1700);
  };
  const METHOD_LABEL = { card: 'Carte bancaire', paypal: 'PayPal', bancontact: 'Bancontact' };
  $('#coPay').onclick = () => pay(false, METHOD_LABEL[state.method]);
  $$('[data-express]').forEach(b => b.onclick = () => { toast('Paiement ' + b.dataset.express + '…'); pay(true, b.dataset.express); });
}

/* ─────────────── AMORÇAGE ─────────────── */
function boot() {
  injectChrome(); renderCart(); pulseCart();
  renderFeatured(); renderShop(); renderProduct(); renderCheckout();
  observeReveals(); animateCounters();
  const mq = $('#mq'); if (mq) mq.innerHTML += mq.innerHTML;
  $('#newsForm')?.addEventListener('submit', e => { e.preventDefault(); e.target.reset(); toast('Bienvenue dans le cercle 🐝'); });
}
document.readyState === 'loading' ? addEventListener('DOMContentLoaded', boot) : boot();
