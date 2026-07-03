/* ════════════════════════════════════════════════════════════════════
   MIELS DU MONDE · Admin (autonome)
   « Connecté en direct » : lit les vraies commandes passées sur la boutique
   (même navigateur, via localStorage 'mdm_orders'). Recherche par nom,
   n° de commande ou e-mail. Pour un backend multi-appareils, brancher
   Supabase/Firebase sur load()/save() (voir README).
   ════════════════════════════════════════════════════════════════════ */
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const euro = n => (Math.round(n * 100) / 100).toFixed(2).replace('.', ',').replace(',00', '') + '€';
const KEY = 'mdm_orders';
const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { return []; } };
const save = o => localStorage.setItem(KEY, JSON.stringify(o));

const IMG = { litchi:'litchi.webp', jujubier:'jujubier.webp', curcuma:'curcuma.png',
  'gelee-royale':'gelee-royale.webp', 'citron-gingembre':'citron-gingembre.webp',
  nigelle:'nigelle.webp', hibiscus:'hibiscus.webp' };
const CATALOG = [
  { slug:'litchi', name:'Miel de Litchi', origin:'Madagascar', price:24 },
  { slug:'jujubier', name:'Miel de Jujubier', origin:'Algérie', price:34 },
  { slug:'curcuma', name:'Miel & Curcuma', origin:'France', price:19 },
  { slug:'gelee-royale', name:'Miel, Gelée Royale, Pollen & Propolis', origin:'France', price:29 },
  { slug:'citron-gingembre', name:'Miel, Citron Vert & Gingembre', origin:'France', price:19 },
  { slug:'nigelle', name:'Miel & Nigelle', origin:'France', price:21 },
  { slug:'hibiscus', name:'Miel & Hibiscus', origin:'France', price:21 }
];
const bySlug = s => CATALOG.find(p => p.slug === s);
const thumb = slug => `<span class="thumb-mini"><img src="assets/products/${IMG[slug] || slug + '.jpg'}" alt="" onerror="this.style.opacity=0"></span>`;
const STATUSES = { 'Payée':'b-paid', 'En préparation':'b-prep', 'Expédiée':'b-ship', 'Livrée':'b-done', 'Remboursée':'b-refund' };
const badge = s => `<span class="badge ${STATUSES[s] || 'b-paid'}">${s}</span>`;
const initials = (c) => ((c.first || '?')[0] + (c.last || '')[0] || '').toUpperCase();
const fullName = c => `${c.first || ''} ${c.last || ''}`.trim() || c.email;
const fmtDate = d => new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });

let orders = load();
let view = 'dashboard';
let query = '';

/* ─────────── AUTH (démo) ─────────── */
function boot() {
  if (sessionStorage.getItem('mdm_admin') === '1') return app();
  document.body.className = '';
  document.body.innerHTML = `<div class="adm-login">
    <form class="login-card" id="loginForm">
      <img src="assets/logo.png" alt="Miels du Monde" onerror="this.onerror=null;this.src='assets/logo.svg'">
      <h2>Espace administrateur</h2><p>Tableau de bord Miels du Monde</p>
      <div class="field"><label>E-mail</label><input type="email" id="lEmail" value="admin@mielsdumonde.fr" required></div>
      <div class="field"><label>Mot de passe</label><input type="password" id="lPass" placeholder="••••••••" required></div>
      <button class="btn btn-gold" type="submit">Se connecter</button>
      <div class="login-note">Démo — saisissez n'importe quel mot de passe pour accéder au tableau de bord.</div>
    </form></div>`;
  $('#loginForm').onsubmit = e => { e.preventDefault(); if (!$('#lPass').value) return; sessionStorage.setItem('mdm_admin', '1'); app(); };
}

/* ─────────── SHELL ─────────── */
function app() {
  orders = load();
  document.body.className = 'admin';
  document.body.innerHTML = `
  <div class="adm-layout">
    <aside class="adm-side">
      <a class="brand" href="index.html"><img src="assets/logo-light.png" alt="Miels du Monde" onerror="this.onerror=null;this.src='assets/logo-light.svg'"></a>
      <nav id="admNav">
        ${[['dashboard','Tableau de bord','M4 13h6V4H4zM14 20h6v-9h-6zM14 4v5h6V4zM4 20h6v-5H4z'],
           ['orders','Commandes','M6 8h12l-1 12H7zM9 8V6a3 3 0 016 0v2'],
           ['customers','Clients','M17 21v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8'],
           ['products','Produits','M3 7l9-4 9 4-9 4zM3 7v10l9 4 9-4V7']]
          .map(([v,l,d]) => `<button data-view="${v}"><svg class="ico" viewBox="0 0 24 24"><path d="${d}"/></svg>${l}</button>`).join('')}
      </nav>
      <div class="foot"><span class="adm-live"><i></i> Connecté en direct</span><br>
        <button id="logout">Déconnexion</button></div>
    </aside>
    <main class="adm-main">
      <div class="adm-top">
        <h1 id="admTitle">Tableau de bord</h1>
        <div class="adm-search"><svg class="ico" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input id="admSearch" placeholder="Rechercher : nom, n° commande, e-mail…"></div>
      </div>
      <div id="admMain"></div>
    </main>
  </div>
  <div id="admScrim"></div><div id="admDrawer"></div>`;
  $('#admNav').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; view = b.dataset.view; query = ''; $('#admSearch').value = ''; route(); });
  $('#logout').onclick = () => { sessionStorage.removeItem('mdm_admin'); boot(); };
  $('#admSearch').addEventListener('input', e => { query = e.target.value.trim().toLowerCase(); route(); });
  $('#admScrim').onclick = closeDrawer;
  route();
}
const TITLES = { dashboard:'Tableau de bord', orders:'Commandes', customers:'Clients', products:'Produits' };
function route() {
  $$('#admNav button').forEach(b => b.classList.toggle('sel', b.dataset.view === view));
  $('#admTitle').textContent = TITLES[view];
  $('.adm-search').style.display = view === 'dashboard' ? 'none' : '';
  ({ dashboard, orders: ordersView, customers: customersView, products: productsView }[view])();
}

/* ─────────── DASHBOARD ─────────── */
function dashboard() {
  const m = $('#admMain');
  if (!orders.length) return emptyState(m);
  const revenue = orders.reduce((a, o) => a + o.total, 0);
  const customers = new Set(orders.map(o => o.customer.email)).size;
  const aov = revenue / orders.length;
  // 7 derniers jours
  const days = [...Array(7)].map((_, i) => { const d = new Date(); d.setDate(d.getDate() - (6 - i)); return d; });
  const dayRev = days.map(d => orders.filter(o => new Date(o.date).toDateString() === d.toDateString()).reduce((a, o) => a + o.total, 0));
  const max = Math.max(...dayRev, 1);
  m.innerHTML = `
    <div class="kpis">
      ${kpi('Chiffre d\'affaires', euro(revenue), 'M3 12h4l3-9 4 18 3-9h4')}
      ${kpi('Commandes', orders.length, 'M6 8h12l-1 12H7zM9 8V6a3 3 0 016 0v2')}
      ${kpi('Panier moyen', euro(aov), 'M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0')}
      ${kpi('Clients', customers, 'M17 21v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8')}
    </div>
    <div class="adm-grid2">
      <div class="adm-card"><h3>Revenu · 7 derniers jours</h3>
        <div class="chart">${dayRev.map((v, i) => `<div class="bar" style="height:${Math.max(4, v / max * 140)}px"><span>${v ? euro(v) : ''}</span><small>${days[i].toLocaleDateString('fr-FR', { weekday: 'short' })}</small></div>`).join('')}</div>
      </div>
      <div class="adm-card"><h3>Top produits</h3>${topProducts()}</div>
    </div>
    <div class="adm-card"><h3>Commandes récentes <button class="link-u" onclick="__go('orders')" style="font-size:.85rem;color:var(--amber)">Tout voir →</button></h3>
      ${orderTable(orders.slice(0, 6))}</div>`;
  bindRows();
}
function kpi(lb, v, d) { return `<div class="kpi"><div class="lb"><svg class="ico" viewBox="0 0 24 24"><path d="${d}"/></svg>${lb}</div><div class="v">${v}</div></div>`; }
function topProducts() {
  const agg = {};
  orders.forEach(o => o.items.forEach(it => { agg[it.slug] = (agg[it.slug] || 0) + it.qty; }));
  const top = Object.entries(agg).sort((a, b) => b[1] - a[1]).slice(0, 4);
  if (!top.length) return '<p class="muted">Aucune vente.</p>';
  const max = top[0][1];
  return top.map(([s, q]) => { const p = bySlug(s); return `<div style="display:flex;align-items:center;gap:.7rem;margin-bottom:.7rem">
    ${thumb(s)}<div style="flex:1;min-width:0"><div style="font-size:.86rem;font-weight:500">${p ? p.name : s}</div>
      <div style="height:5px;background:var(--cream-2);border-radius:9px;margin-top:.3rem;overflow:hidden"><i style="display:block;height:100%;width:${q / max * 100}%;background:linear-gradient(90deg,var(--gold),var(--amber))"></i></div></div>
    <b style="font-family:'Cormorant Garamond',serif">${q}</b></div>`; }).join('');
}

/* ─────────── COMMANDES ─────────── */
function matchOrder(o) {
  if (!query) return true;
  return (o.no + ' ' + fullName(o.customer) + ' ' + o.customer.email + ' ' + o.customer.city).toLowerCase().includes(query);
}
function ordersView() {
  const m = $('#admMain');
  if (!orders.length) return emptyState(m);
  const list = orders.filter(matchOrder);
  m.innerHTML = `<div class="adm-card">
    <h3>${list.length} commande${list.length > 1 ? 's' : ''}${query ? ` · « ${query} »` : ''}</h3>
    ${list.length ? orderTable(list) : '<p class="adm-empty">Aucune commande ne correspond à votre recherche.</p>'}</div>`;
  bindRows();
}
function orderTable(list) {
  return `<div style="overflow-x:auto"><table class="adm-table"><thead><tr>
    <th>N°</th><th>Date</th><th>Client</th><th>Articles</th><th>Total</th><th>Statut</th></tr></thead><tbody>
    ${list.map(o => `<tr data-no="${o.no}">
      <td class="mono">${o.no}</td><td>${fmtDate(o.date)}</td>
      <td><div class="cell-cust"><span class="av">${initials(o.customer)}</span><div><div style="font-weight:500">${fullName(o.customer)}</div><div style="font-size:.78rem;color:var(--ink-mut)">${o.customer.email}</div></div></div></td>
      <td>${o.items.reduce((a, i) => a + i.qty, 0)}</td><td style="font-weight:600">${euro(o.total)}</td><td>${badge(o.status)}</td>
    </tr>`).join('')}</tbody></table></div>`;
}
function bindRows() { $$('.adm-table tbody tr[data-no]').forEach(r => r.onclick = () => openOrder(r.dataset.no)); $$('.adm-table tbody tr[data-email]').forEach(r => r.onclick = () => openCustomer(r.dataset.email)); }

/* ─────────── CLIENTS ─────────── */
function customersView() {
  const m = $('#admMain');
  const map = {};
  orders.forEach(o => { const e = o.customer.email; (map[e] = map[e] || { c: o.customer, n: 0, total: 0, last: o.date }).n++; map[e].total += o.total; if (o.date > map[e].last) map[e].last = o.date; });
  let list = Object.entries(map).map(([email, v]) => ({ email, ...v }));
  if (query) list = list.filter(x => (fullName(x.c) + ' ' + x.email + ' ' + x.c.city).toLowerCase().includes(query));
  list.sort((a, b) => b.total - a.total);
  if (!orders.length) return emptyState(m);
  m.innerHTML = `<div class="adm-card"><h3>${list.length} client${list.length > 1 ? 's' : ''}${query ? ` · « ${query} »` : ''}</h3>
    ${list.length ? `<div style="overflow-x:auto"><table class="adm-table"><thead><tr><th>Client</th><th>Ville</th><th>Commandes</th><th>Total dépensé</th><th>Dernière</th></tr></thead><tbody>
    ${list.map(x => `<tr data-email="${x.email}"><td><div class="cell-cust"><span class="av">${initials(x.c)}</span><div><div style="font-weight:500">${fullName(x.c)}</div><div style="font-size:.78rem;color:var(--ink-mut)">${x.email}</div></div></div></td>
      <td>${x.c.city || '—'}</td><td>${x.n}</td><td style="font-weight:600">${euro(x.total)}</td><td>${fmtDate(x.last)}</td></tr>`).join('')}
    </tbody></table></div>` : '<p class="adm-empty">Aucun client ne correspond.</p>'}</div>`;
  bindRows();
}

/* ─────────── PRODUITS ─────────── */
function productsView() {
  const m = $('#admMain');
  const agg = {};
  orders.forEach(o => o.items.forEach(it => { const a = agg[it.slug] = agg[it.slug] || { units: 0, rev: 0 }; a.units += it.qty; a.rev += it.qty * it.price; }));
  let rows = CATALOG.map(p => ({ ...p, units: (agg[p.slug] || {}).units || 0, rev: (agg[p.slug] || {}).rev || 0 }));
  if (query) rows = rows.filter(p => (p.name + ' ' + p.origin).toLowerCase().includes(query));
  rows.sort((a, b) => b.rev - a.rev);
  m.innerHTML = `<div class="adm-card"><h3>Catalogue · ${rows.length} produits</h3>
    <div style="overflow-x:auto"><table class="adm-table"><thead><tr><th>Produit</th><th>Origine</th><th>Prix</th><th>Vendus</th><th>Revenu</th></tr></thead><tbody>
    ${rows.map(p => `<tr><td><div class="cell-cust">${thumb(p.slug)}<b style="font-weight:500">${p.name}</b></div></td>
      <td>${p.origin}</td><td>${euro(p.price)}</td><td>${p.units}</td><td style="font-weight:600">${euro(p.rev)}</td></tr>`).join('')}
    </tbody></table></div></div>`;
}

/* ─────────── DRAWER ─────────── */
function openOrder(no) {
  const o = orders.find(x => x.no === no); if (!o) return;
  $('#admDrawer').innerHTML = `
    <div class="dr-h"><h3>${o.no}</h3><button class="iconbtn" onclick="__closeDrawer()"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
    <div class="dr-b">
      <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1rem">${badge(o.status)}<span class="muted" style="font-size:.85rem">${fmtDate(o.date)}</span></div>
      <div class="dr-sec-t">Client</div>
      <div style="display:flex;align-items:center;gap:.7rem;margin-bottom:.6rem"><span class="av">${initials(o.customer)}</span><div><div style="font-weight:600">${fullName(o.customer)}</div><div style="font-size:.82rem;color:var(--ink-mut)">${o.customer.email}</div></div></div>
      <div class="dr-row"><span class="k">Adresse</span><span>${o.customer.addr || '—'}</span></div>
      <div class="dr-row"><span class="k">Ville</span><span>${o.customer.zip || ''} ${o.customer.city || '—'}, ${o.customer.country || ''}</span></div>
      <div class="dr-row"><span class="k">Livraison</span><span>${o.delivery}</span></div>
      <div class="dr-row"><span class="k">Paiement</span><span>${o.payment}</span></div>
      <div class="dr-sec-t">Articles</div>
      ${o.items.map(it => `<div class="dr-item">${thumb(it.slug)}<div><div style="font-weight:500;font-size:.9rem">${it.name}</div><div style="font-size:.8rem;color:var(--ink-mut)">${it.origin} · ×${it.qty}</div></div><b>${euro(it.price * it.qty)}</b></div>`).join('')}
      <div class="dr-row" style="margin-top:.8rem"><span class="k">Sous-total</span><span>${euro(o.subtotal)}</span></div>
      ${o.discount ? `<div class="dr-row"><span class="k">Réduction</span><span>−${euro(o.discount)}</span></div>` : ''}
      <div class="dr-row"><span class="k">Livraison</span><span>${o.shipping ? euro(o.shipping) : 'Offerte'}</span></div>
      <div class="dr-row" style="font-size:1.15rem"><span class="k" style="color:var(--ink);font-weight:600">Total</span><b style="font-family:'Cormorant Garamond',serif;font-size:1.3rem">${euro(o.total)}</b></div>
      <div class="dr-sec-t">Statut de la commande</div>
      <div class="status-sel">${Object.keys(STATUSES).map(s => `<button class="${s === o.status ? 'on' : ''}" data-s="${s}">${s}</button>`).join('')}</div>
    </div>`;
  $$('#admDrawer .status-sel button').forEach(b => b.onclick = () => { o.status = b.dataset.s; save(orders); openOrder(no); route(); });
  openDrawer();
}
function openCustomer(email) {
  const co = orders.filter(o => o.customer.email === email); if (!co.length) return;
  const c = co[0].customer, spent = co.reduce((a, o) => a + o.total, 0);
  $('#admDrawer').innerHTML = `
    <div class="dr-h"><h3>${fullName(c)}</h3><button class="iconbtn" onclick="__closeDrawer()"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
    <div class="dr-b">
      <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1rem"><span class="av" style="width:48px;height:48px">${initials(c)}</span><div><div style="font-size:.85rem;color:var(--ink-mut)">${c.email}</div><div style="font-size:.85rem;color:var(--ink-mut)">${c.city || ''} ${c.country || ''}</div></div></div>
      <div class="kpis" style="grid-template-columns:1fr 1fr;gap:.7rem;margin-bottom:1rem">
        <div class="kpi"><div class="lb">Commandes</div><div class="v">${co.length}</div></div>
        <div class="kpi"><div class="lb">Total dépensé</div><div class="v">${euro(spent)}</div></div></div>
      <div class="dr-sec-t">Historique</div>
      ${co.map(o => `<div class="dr-item" style="cursor:pointer" onclick="__openOrder('${o.no}')"><div><div class="mono" style="font-weight:600">${o.no}</div><div style="font-size:.8rem;color:var(--ink-mut)">${fmtDate(o.date)} · ${o.items.reduce((a, i) => a + i.qty, 0)} art.</div></div>${badge(o.status)}<b style="margin-left:auto">${euro(o.total)}</b></div>`).join('')}
    </div>`;
  openDrawer();
}
function openDrawer() { $('#admDrawer').classList.add('on'); $('#admScrim').classList.add('on'); }
function closeDrawer() { $('#admDrawer').classList.remove('on'); $('#admScrim').classList.remove('on'); }
window.__closeDrawer = closeDrawer; window.__openOrder = openOrder;
window.__go = v => { view = v; query = ''; const s = $('#admSearch'); if (s) s.value = ''; route(); };

/* ─────────── EMPTY / SEED ─────────── */
function emptyState(m) {
  m.innerHTML = `<div class="adm-card adm-empty">
    <h3>Aucune commande pour l'instant</h3>
    <p class="muted" style="margin-bottom:1.4rem">Les commandes passées sur la boutique apparaîtront ici automatiquement, en direct.</p>
    <button class="btn btn-gold" id="seedBtn">Générer des commandes de démonstration</button>
    <p class="muted" style="margin-top:1rem;font-size:.82rem"><a class="link-u" href="index.html">← Retour à la boutique</a></p></div>`;
  $('#seedBtn').onclick = () => { seed(); orders = load(); route(); };
}
function seed() {
  const people = [['Camille','Durand','Lyon','69003','France'],['Karim','Benali','Bruxelles','1000','Belgique'],['Élodie','Martin','Bordeaux','33000','France'],['Thomas','Rey','Genève','1201','Suisse'],['Sarah','Lefevre','Paris','75011','France'],['Marc','Vidal','Nantes','44000','France'],['Inès','Moreau','Lille','59000','France'],['Yanis','Cherif','Marseille','13006','France'],['Julie','Petit','Toulouse','31000','France'],['Nadia','Haddad','Luxembourg','1611','Luxembourg']];
  const out = [];
  const N = 14;
  for (let i = 0; i < N; i++) {
    const pr = people[Math.floor(Math.random() * people.length)];
    const nItems = 1 + Math.floor(Math.random() * 3);
    const chosen = [...CATALOG].sort(() => Math.random() - 0.5).slice(0, nItems);
    const items = chosen.map(p => ({ slug: p.slug, name: p.name, qty: 1 + Math.floor(Math.random() * 2), price: p.price, origin: p.origin }));
    const subtotal = items.reduce((a, it) => a + it.price * it.qty, 0);
    const discount = Math.random() < 0.35 ? subtotal * 0.15 : 0;
    const shipping = (subtotal - discount) >= 79 ? 0 : 3.9;
    const date = new Date(); date.setDate(date.getDate() - Math.floor(Math.random() * 14)); date.setHours(Math.floor(Math.random() * 24));
    out.push({ no: 'MDM-' + Math.random().toString(36).slice(2, 8).toUpperCase(), date: date.toISOString(),
      customer: { email: (pr[0] + '.' + pr[1]).toLowerCase() + '@email.com', first: pr[0], last: pr[1], addr: (1 + Math.floor(Math.random() * 90)) + ' rue des Abeilles', city: pr[2], zip: pr[3], country: pr[4] },
      items, subtotal, discount, shipping, total: subtotal - discount + shipping,
      payment: ['Carte bancaire', 'PayPal', 'Apple Pay', 'Bancontact'][Math.floor(Math.random() * 4)],
      delivery: Math.random() < 0.6 ? 'Point Relais' : 'À domicile',
      status: ['Payée', 'En préparation', 'Expédiée', 'Livrée'][Math.floor(Math.random() * 4)] });
  }
  const existing = load(); save(existing.concat(out).sort((a, b) => b.date.localeCompare(a.date)));
}

boot();
