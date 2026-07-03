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
const LOGO = 'assets/logo.svg';

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
    nutrition:{'Énergie':'1 350 kJ / 318 kcal','Glucides':'78 g','— dont sucres':'76 g','Protéines':'0,4 g','Matières grasses':'0 g'} }
];
const byslug = s => CATALOG.find(p => p.slug === s);
const FREE = 79;

/* image produit avec repli gracieux (dégradé + nom si le fichier manque) */
function pimg(p, cls = '') {
  const bg = `linear-gradient(150deg,${p.hue[0]},${p.hue[1]} 55%,${p.hue[2]})`;
  return `<div class="pvis ${cls}" style="--fb:${bg}">
    <img src="assets/products/${p.slug}.jpg" alt="${p.name}" loading="lazy"
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
    <a class="logo" href="index.html" aria-label="Miels du Monde — accueil"><img src="${LOGO}" alt="Miels du Monde"></a>
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

  const cart = document.createElement('div');
  cart.innerHTML = `
    <div id="scrim"></div>
    <aside id="cart" aria-label="Panier">
      <div class="cart-h"><h3>Votre panier</h3><button class="iconbtn" id="closeCart" aria-label="Fermer"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
      <div class="cart-ship" id="cartShip"></div>
      <div class="cart-items" id="cartItems"></div>
      <div class="cart-f" id="cartFoot" hidden>
        <div class="line"><span>Sous-total</span><span id="cartSub">0€</span></div>
        <div class="line"><span>Livraison</span><span id="cartShipCost">—</span></div>
        <div class="tot" id="cartTot">0€</div>
        <button class="btn btn-gold" id="checkout">Passer commande</button>
        <div class="re">Paiement sécurisé · Satisfait ou remboursé 14 jours</div>
      </div>
    </aside>
    <div id="toast" role="status"><svg class="ico" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg><span id="toastMsg">Ajouté</span></div>`;
  document.body.append(cart);

  const foot = $('#site-footer');
  if (foot) foot.outerHTML = `
    <footer class="ft"><div class="shell">
      <div class="ft-top">
        <div class="ft-brand"><a class="logo" href="index.html"><img src="${LOGO}" alt="Miels du Monde"></a>
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
  $('#checkout').onclick = () => toast('Redirection vers le paiement sécurisé…');
  $('#cartItems').addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (!b) return; const s = b.dataset.slug, n = cart.get(s) || 0; if (b.dataset.act === 'inc') setQty(s, n + 1); else if (b.dataset.act === 'dec') setQty(s, n - 1); else if (b.dataset.act === 'rm') setQty(s, 0); });
  addEventListener('keydown', e => { if (e.key === 'Escape') { closeCart(); menu.classList.remove('open'); document.body.classList.remove('lock'); } });
  // header solid on scroll (uniquement pour header transparent sur hero)
  if (!header.classList.contains('light')) { const on = () => header.classList.toggle('solid', scrollY > 40); addEventListener('scroll', on, { passive: true }); on(); }
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

/* ─────────────── AMORÇAGE ─────────────── */
function boot() {
  injectChrome(); renderCart(); pulseCart();
  renderFeatured(); renderShop(); renderProduct();
  observeReveals(); animateCounters();
  const mq = $('#mq'); if (mq) mq.innerHTML += mq.innerHTML;
  $('#newsForm')?.addEventListener('submit', e => { e.preventDefault(); e.target.reset(); toast('Bienvenue dans le cercle 🐝'); });
}
document.readyState === 'loading' ? addEventListener('DOMContentLoaded', boot) : boot();
