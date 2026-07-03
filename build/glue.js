/* ════════════════════════════════════════════════════════════════════
   MIELS DU MONDE · SPA glue (single-file)
   Routeur interne + globe 3D + liaisons. Réutilise les fonctions globales
   de app.js (renderShop, renderProduct, renderCheckout, injectChrome…).
   ════════════════════════════════════════════════════════════════════ */
(function () {
  const RMq = matchMedia('(prefers-reduced-motion:reduce)');
  const T = window.__T;                     // templates injectés par le build
  const app = () => document.getElementById('app');

  function hrefToRoute(href) {
    if (!href || /^(https?:|mailto:|tel:)/.test(href)) return null;
    if (href.charAt(0) === '#') return null;
    const [path, qs] = href.split('?');
    const map = { '': 'home', 'index.html': 'home', 'boutique.html': 'boutique', 'produit.html': 'produit', 'a-propos.html': 'apropos', 'faq.html': 'faq', 'checkout.html': 'checkout', 'admin.html': 'admin' };
    const name = map[path]; if (!name) return null;
    return { name, params: Object.fromEntries(new URLSearchParams(qs || '')) };
  }

  function navigate(name, params) {
    window.__params = params || {};
    const root = app(); if (!root) return;
    document.body.classList.toggle('route-admin', name === 'admin');
    document.body.classList.toggle('admin', name === 'admin');
    document.body.classList.remove('lock');
    const hd = document.getElementById('hd');
    if (hd) { hd.classList.toggle('light', name === 'produit' || name === 'checkout'); hd.classList.remove('solid'); }

    if (name === 'admin') { root.innerHTML = ''; if (window.initAdmin) window.initAdmin(); }
    else {
      root.innerHTML = T[name] || T.home;
      if (typeof renderFeatured === 'function') renderFeatured();
      if (typeof renderShop === 'function') renderShop();
      if (typeof renderProduct === 'function') renderProduct();
      if (typeof renderCheckout === 'function') renderCheckout();
      bindFaq(); bindNews();
      if (typeof observeReveals === 'function') observeReveals(root);
      if (typeof animateCounters === 'function') animateCounters(root);
      if (name === 'home') {
        const mq = document.getElementById('mq'); if (mq && !mq.dataset.dup) { mq.dataset.dup = '1'; mq.innerHTML += mq.innerHTML; }
        if (window.initGlobe) window.initGlobe();
      }
    }
    document.querySelectorAll('#hd .top-nav a').forEach(a => { const r = hrefToRoute(a.getAttribute('href')); a.classList.toggle('active', r && r.name === name); });
    window.scrollTo(0, 0);
    const menu = document.getElementById('menu'); if (menu) menu.classList.remove('open');
    if (typeof closeCart === 'function') closeCart();
    if (hd) hd.classList.toggle('solid', name === 'home' ? scrollY > 40 : (name !== 'produit' && name !== 'checkout' && name !== 'admin' ? scrollY > 40 : false));
    location.hash = name === 'home' ? '' : ('#/' + name + (params && params.p ? '/' + params.p : (params && params.f ? '/' + params.f : '')));
  }
  window.__navigate = navigate;

  window.goTo = function (href) {
    const r = hrefToRoute(href);
    if (!r) { if (href && href.charAt(0) !== '#') location.href = href; return; }
    const v = document.getElementById('veil');
    if (v && !RMq.matches) { v.classList.add('on'); setTimeout(() => { v.classList.remove('on'); navigate(r.name, r.params); }, 420); }
    else navigate(r.name, r.params);
  };

  function bindFaq() {
    const acc = document.getElementById('faqAcc'); if (!acc || acc.dataset.b) return; acc.dataset.b = '1';
    acc.addEventListener('click', e => { const b = e.target.closest('.acc-q'); if (!b) return; const it = b.parentElement, a = it.querySelector('.acc-a'); const open = it.classList.toggle('open'); a.style.maxHeight = open ? a.scrollHeight + 'px' : 0; });
  }
  function bindNews() {
    const f = document.getElementById('newsForm'); if (!f || f.dataset.b) return; f.dataset.b = '1';
    f.addEventListener('submit', e => { e.preventDefault(); f.reset(); if (typeof toast === 'function') toast('Bienvenue dans le cercle 🐝'); });
  }

  /* ════════ GLOBE 3D (Terre) ════════ */
  const ORIGINS = [
    { code: 'MG', flag: '🇲🇬', name: 'Madagascar', lat: -18.9, lon: 46.7, img: 'litchi', honey: 'Miel de Litchi', href: 'produit.html?p=litchi', desc: "Récolté dans les vergers de litchis de la côte est de Madagascar, un miel clair et floral aux notes de fruits rouges.", benefits: ['Antioxydant', 'Énergisant', 'Floral & doux'] },
    { code: 'DZ', flag: '🇩🇿', name: 'Algérie', lat: 28, lon: 2.6, img: 'jujubier', honey: 'Miel de Jujubier', href: 'produit.html?p=jujubier', desc: "Le cousin du célèbre Sidr : dense, ambré et résineux, récolté sur l'arbre de jujubier des vallées arides.", benefits: ['Immunité', 'Reminéralisant', 'Rare & précieux'] },
    { code: 'FR', flag: '🇫🇷', name: 'France', lat: 46.6, lon: 2.3, img: 'curcuma', honey: 'Nos préparations au miel', href: 'boutique.html?f=prep', desc: "Curcuma, Nigelle, Hibiscus, Gelée royale… nos préparations bien-être élaborées et conditionnées en France.", benefits: ['Bien-être', 'Anti-inflammatoire', 'Élaboré en France'] }
  ];
  let selected = 0, pins = null, globe = null, faceTarget = null, GS = null;

  function tabs() {
    const t = document.getElementById('originTabs'); if (!t) return;
    t.innerHTML = ORIGINS.map((o, i) => '<button data-i="' + i + '" class="' + (i === selected ? 'sel' : '') + '"><span>' + o.flag + '</span>' + o.name + '</button>').join('');
    t.onclick = e => { const b = e.target.closest('button'); if (b) select(+b.dataset.i, true); };
  }
  function openOriginModal(i) {
    const o = ORIGINS[i], m = document.getElementById('originModal'); if (!m) return;
    m.innerHTML = '<div class="om-scrim"></div><div class="om-card" role="dialog" aria-label="' + o.name + '">' +
      '<button class="om-close" aria-label="Fermer"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>' +
      '<div class="om-photo"><img src="' + (window.PHOTOS ? window.PHOTOS[o.img] : '') + '" alt="' + o.honey + '"><span class="om-flag">' + o.flag + ' ' + o.name + '</span></div>' +
      '<div class="om-body"><span class="eyebrow">Origine · ' + o.code + '</span><h3>' + o.honey + '</h3><p>' + o.desc + '</p>' +
      '<div class="om-benes">' + o.benefits.map(x => '<span>✦ ' + x + '</span>').join('') + '</div>' +
      '<a class="btn btn-gold btn-lg" href="' + o.href + '">Découvrir & commander <svg class="ico" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a></div></div>';
    m.classList.add('on'); document.body.classList.add('lock');
    const c = () => { m.classList.remove('on'); document.body.classList.remove('lock'); };
    m.querySelector('.om-close').onclick = c; m.querySelector('.om-scrim').onclick = c;
    m.querySelector('.om-body .btn').onclick = e => { e.preventDefault(); c(); window.goTo(o.href); };
  }
  function select(i, open) {
    selected = i;
    document.querySelectorAll('#originTabs button').forEach(b => b.classList.toggle('sel', +b.dataset.i === i));
    if (pins) pins.forEach((p, j) => p.userData.sel = j === i);
    if (globe) faceOrigin(i);
    if (open) openOriginModal(i);
  }
  function faceOrigin(i) { const o = ORIGINS[i]; let ty = -Math.PI / 2 - o.lon * Math.PI / 180; while (ty - GS.rot.y > Math.PI) ty -= 2 * Math.PI; while (ty - GS.rot.y < -Math.PI) ty += 2 * Math.PI; faceTarget = { y: ty, x: Math.max(-1, Math.min(1, o.lat * Math.PI / 180)) }; }

  window.initGlobe = async function () {
    const canvas = document.getElementById('globe'); if (!canvas) return;
    selected = 0; tabs();
    if (!window.WebGLRenderingContext) { canvas.closest('.globe-stage').classList.add('nofx'); canvas.style.display = 'none'; return; }
    let THREE;
    try {
      if (!window.__threeMod) { const src = document.getElementById('three-src').textContent; window.__threeMod = await import(URL.createObjectURL(new Blob([src], { type: 'text/javascript' }))); }
      THREE = window.__threeMod;
    } catch (e) { canvas.closest('.globe-stage').classList.add('nofx'); canvas.style.display = 'none'; return; }
    if (GS) { cancelAnimationFrame(GS.raf); if (GS.ro) GS.ro.disconnect(); try { GS.renderer.dispose(); } catch (e) {} }
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(33, 1, .1, 100); camera.position.set(0, 0, 3.05);
    globe = new THREE.Group(); scene.add(globe);
    const R = 1, rot = { x: 0.28, y: -1.75 }, vel = { x: 0, y: 0 }, drag = { on: false, x: 0, y: 0, moved: 0 };
    GS = { renderer, rot, raf: 0, ro: null };
    const toVec = (lat, lon, r = R) => { const phi = (90 - lat) * Math.PI / 180, th = (lon + 180) * Math.PI / 180; return [-(r * Math.sin(phi) * Math.cos(th)), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th)]; };
    const tex = new THREE.TextureLoader().load(window.EARTH); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    globe.add(new THREE.Mesh(new THREE.SphereGeometry(R, 128, 128), new THREE.MeshStandardMaterial({ map: tex, roughness: .9, metalness: .06 })));
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.16, 64, 64), new THREE.MeshBasicMaterial({ color: 0x6fb0f0, transparent: true, opacity: .18, side: THREE.BackSide })));
    const sN = 1000, sp = new Float32Array(sN * 3);
    for (let i = 0; i < sN; i++) { const r = 18 + Math.random() * 24, a = Math.random() * Math.PI * 2, bb = Math.acos(2 * Math.random() - 1); sp[i * 3] = r * Math.sin(bb) * Math.cos(a); sp[i * 3 + 1] = r * Math.cos(bb); sp[i * 3 + 2] = r * Math.sin(bb) * Math.sin(a); }
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
    scene.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xfff6e0, size: 0.09, transparent: true, opacity: .85 })));
    pins = ORIGINS.map((o, i) => { const v = toVec(o.lat, o.lon, R * 1.02); const g = new THREE.Group(); g.position.set(v[0], v[1], v[2]);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.045, 20, 20), new THREE.MeshStandardMaterial({ color: 0xfff4cf, emissive: 0xe0a83c, emissiveIntensity: 1.5, roughness: .3 }));
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.065, 0.088, 28), new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: .85, side: THREE.DoubleSide }));
      ring.lookAt(new THREE.Vector3(v[0], v[1], v[2]).multiplyScalar(2)); g.add(head, ring); g.userData = { i, head, sel: i === selected }; globe.add(g); return g; });
    scene.add(new THREE.AmbientLight(0x53617a, 0.6));
    const sun = new THREE.DirectionalLight(0xfff5e8, 2.7); sun.position.set(4, 2, 3); scene.add(sun);
    const bo = new THREE.DirectionalLight(0x5a93d6, 0.5); bo.position.set(-4, -1, -3); scene.add(bo);
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
    canvas.style.cursor = 'grab'; canvas.style.touchAction = 'none';
    canvas.onpointerdown = e => { drag.on = true; drag.x = e.clientX; drag.y = e.clientY; drag.moved = 0; try { canvas.setPointerCapture(e.pointerId); } catch (x) {} canvas.style.cursor = 'grabbing'; };
    canvas.onpointermove = e => { if (!drag.on) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; rot.y += dx * 0.006; rot.x = Math.max(-1.1, Math.min(1.1, rot.x + dy * 0.006)); vel.y = dx * 0.006; vel.x = dy * 0.006; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy); faceTarget = null; };
    const end = e => { if (!drag.on) return; drag.on = false; canvas.style.cursor = 'grab'; if (drag.moved < 6) { const r = canvas.getBoundingClientRect(); ndc.x = ((e.clientX - r.left) / r.width) * 2 - 1; ndc.y = -((e.clientY - r.top) / r.height) * 2 + 1; ray.setFromCamera(ndc, camera); const hit = ray.intersectObjects(pins.map(p => p.userData.head))[0]; if (hit) { const i = pins.findIndex(p => p.userData.head === hit.object); if (i >= 0) select(i, true); } } };
    canvas.onpointerup = end; canvas.onpointercancel = end;
    let lastW = 0;
    const stage = canvas.parentElement;
    function resize() { const b = stage.getBoundingClientRect(); const w = Math.round(b.width) || 480, h = Math.round(b.height) || 480; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); lastW = w; }
    GS.ro = new ResizeObserver(resize); GS.ro.observe(stage); resize();
    let t = 0;
    function loop() {
      GS.raf = requestAnimationFrame(loop); t += 0.016;
      if (stage.clientWidth && stage.clientWidth !== lastW) resize();
      if (!drag.on) { if (faceTarget) { rot.y += (faceTarget.y - rot.y) * 0.07; rot.x += (faceTarget.x - rot.x) * 0.07; if (Math.abs(faceTarget.y - rot.y) < 0.003) faceTarget = null; } else { rot.y += (RMq.matches ? 0 : 0.0013) + vel.y; rot.x += vel.x; vel.y *= 0.94; vel.x *= 0.94; } }
      globe.rotation.y = rot.y; globe.rotation.x = rot.x;
      if (pins) pins.forEach((p, i) => { const pulse = 1 + Math.sin(t * 2 + i) * 0.09; p.scale.setScalar((p.userData.sel ? 1.7 : 1) * pulse); p.userData.head.material.emissiveIntensity = p.userData.sel ? 2.3 : 1.3; });
      renderer.render(scene, camera);
    }
    loop();
  };

  function start() {
    if (typeof injectChrome === 'function') injectChrome();
    if (typeof renderCart === 'function') renderCart();
    if (typeof pulseCart === 'function') pulseCart();
    addEventListener('scroll', () => { const hd = document.getElementById('hd'); if (hd && !hd.classList.contains('light')) hd.classList.toggle('solid', scrollY > 40); }, { passive: true });
    const h = (location.hash || '').replace(/^#\//, '');
    const seg = h.split('/');
    const known = ['home', 'boutique', 'produit', 'apropos', 'faq', 'checkout', 'admin'];
    let name = known.includes(seg[0]) ? seg[0] : 'home', params = {};
    if (name === 'produit' && seg[1]) params.p = seg[1];
    if (name === 'boutique' && seg[1]) params.f = seg[1];
    navigate(name, params);
  }
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', start); else start();
})();
