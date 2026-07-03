/* ════════════════════════════════════════════════════════════════════
   MIELS DU MONDE · Globe 3D des origines (cœur du site)
   Planète "ruche" (texture nid d'abeille procédurale), rotative souris + doigt.
   Clic sur un pays → fiche élégante (photo, description, bienfaits, commander).
   Three.js chargé dynamiquement (CDN) avec repli gracieux : onglets + fiche
   fonctionnent même sans WebGL, donc on peut toujours commander.
   ════════════════════════════════════════════════════════════════════ */
"use strict";
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const RM = matchMedia('(prefers-reduced-motion:reduce)').matches;

  const ORIGINS = [
    { code: 'MG', flag: '🇲🇬', name: 'Madagascar', lat: -18.9, lon: 46.7, img: 'litchi.webp',
      honey: 'Miel de Litchi', href: 'produit.html?p=litchi',
      desc: "Récolté dans les vergers de litchis de la côte est de Madagascar, un miel clair et floral aux notes de fruits rouges.",
      benefits: ['Antioxydant', 'Énergisant', 'Floral & doux'] },
    { code: 'DZ', flag: '🇩🇿', name: 'Algérie', lat: 28.0, lon: 2.6, img: 'jujubier.webp',
      honey: 'Miel de Jujubier', href: 'produit.html?p=jujubier',
      desc: "Le cousin du célèbre Sidr : dense, ambré et résineux, récolté sur l'arbre de jujubier des vallées arides.",
      benefits: ['Immunité', 'Reminéralisant', 'Rare & précieux'] },
    { code: 'FR', flag: '🇫🇷', name: 'France', lat: 46.6, lon: 2.3, img: 'curcuma.webp',
      honey: 'Nos préparations au miel', href: 'boutique.html?f=prep',
      desc: "Curcuma, Nigelle, Hibiscus, Gelée royale… nos préparations bien-être élaborées et conditionnées en France.",
      benefits: ['Bien-être', 'Anti-inflammatoire', 'Élaboré en France'] }
  ];
  const IMG = 'assets/products/';

  const canvas = $('#globe'); if (!canvas) return;
  const wrap = canvas.closest('.globe-stage');
  let selected = 0, pins = null, globe = null, faceTarget = null;

  /* ── onglets ── */
  function renderTabs() {
    const t = $('#originTabs'); if (!t) return;
    t.innerHTML = ORIGINS.map((o, i) => `<button data-i="${i}" class="${i === selected ? 'sel' : ''}"><span>${o.flag}</span>${o.name}</button>`).join('');
    t.onclick = e => { const b = e.target.closest('button'); if (b) select(+b.dataset.i, true); };
  }
  /* ── fiche modale ── */
  function openModal(i) {
    const o = ORIGINS[i], m = $('#originModal'); if (!m) return;
    m.innerHTML = `<div class="om-scrim"></div>
      <div class="om-card" role="dialog" aria-label="${o.name}">
        <button class="om-close" aria-label="Fermer"><svg class="ico" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
        <div class="om-photo"><img src="${IMG}${o.img}" alt="${o.honey} — ${o.name}" loading="lazy"><span class="om-flag">${o.flag} ${o.name}</span></div>
        <div class="om-body">
          <span class="eyebrow">Origine · ${o.code}</span>
          <h3>${o.honey}</h3>
          <p>${o.desc}</p>
          <div class="om-benes">${o.benefits.map(b => `<span>✦ ${b}</span>`).join('')}</div>
          <a class="btn btn-gold btn-lg" href="${o.href}">Découvrir & commander <svg class="ico" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>
        </div>
      </div>`;
    m.classList.add('on'); document.body.classList.add('lock');
    const close = () => { m.classList.remove('on'); document.body.classList.remove('lock'); };
    m.querySelector('.om-close').onclick = close; m.querySelector('.om-scrim').onclick = close;
  }
  function select(i, open) {
    selected = i;
    document.querySelectorAll('#originTabs button').forEach(b => b.classList.toggle('sel', +b.dataset.i === i));
    if (pins) pins.forEach((p, j) => p.userData.sel = j === i);
    if (globe) faceOrigin(i);
    if (open) openModal(i);
  }
  renderTabs();
  addEventListener('keydown', e => { if (e.key === 'Escape') { const m = $('#originModal'); if (m && m.classList.contains('on')) { m.classList.remove('on'); document.body.classList.remove('lock'); } } });

  /* ── 3D ── */
  const R = 1;
  const toVec = (lat, lon, r = R) => { const phi = (90 - lat) * Math.PI / 180, th = (lon + 180) * Math.PI / 180;
    return [-(r * Math.sin(phi) * Math.cos(th)), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th)]; };
  let THREE, renderer, scene, camera;
  const rot = { x: 0.28, y: -1.75 }, vel = { x: 0, y: 0 }, drag = { on: false, x: 0, y: 0, moved: 0 };

  const fallback = () => { wrap && wrap.classList.add('nofx'); canvas.style.display = 'none'; };

  function hiveTexture() {
    const c = document.createElement('canvas'); c.width = 1024; c.height = 512; const x = c.getContext('2d');
    const g = x.createLinearGradient(0, 0, 0, 512);
    g.addColorStop(0, '#f2c766'); g.addColorStop(.5, '#d98a2b'); g.addColorStop(1, '#8a4c12');
    x.fillStyle = g; x.fillRect(0, 0, 1024, 512);
    const r = 15;
    const hex = (cx, cy, rr) => { x.beginPath(); for (let k = 0; k < 6; k++) { const a = Math.PI / 180 * (60 * k - 30); const px = cx + rr * Math.cos(a), py = cy + rr * Math.sin(a); k ? x.lineTo(px, py) : x.moveTo(px, py); } x.closePath(); };
    x.strokeStyle = 'rgba(70,35,6,.42)'; x.lineWidth = 2.2;
    for (let row = 0, y = -r; y < 512 + r; row++, y += r * 1.5) { const off = (row % 2) * (r * Math.sqrt(3) / 2);
      for (let cx = off - r; cx < 1024 + r; cx += r * Math.sqrt(3)) { hex(cx, y, r); x.stroke(); } }
    x.fillStyle = 'rgba(255,224,140,.22)';
    for (let i = 0; i < 70; i++) { hex(Math.random() * 1024, Math.random() * 512, r * .82); x.fill(); }
    return c;
  }

  async function init() {
    if (!window.WebGLRenderingContext) return fallback();
    try { THREE = await import('./vendor/three.module.min.js'); } catch (e) { return fallback(); }
    try { renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' }); } catch (e) { return fallback(); }
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.06;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100); camera.position.set(0, 0, 3.1);
    globe = new THREE.Group(); scene.add(globe);

    // vraie Terre : texture équirectangulaire (continents, océans, frontières)
    const tex = new THREE.TextureLoader().load('assets/textures/earth.jpg');
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    globe.add(new THREE.Mesh(new THREE.SphereGeometry(R, 128, 128),
      new THREE.MeshStandardMaterial({ map: tex, roughness: .9, metalness: .06 })));
    // atmosphère bleue
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.16, 64, 64),
      new THREE.MeshBasicMaterial({ color: 0x6fb0f0, transparent: true, opacity: .18, side: THREE.BackSide })));
    // champ d'étoiles
    const sN = 900, sp = new Float32Array(sN * 3);
    for (let i = 0; i < sN; i++) { const r = 18 + Math.random() * 22, a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1);
      sp[i*3] = r*Math.sin(b)*Math.cos(a); sp[i*3+1] = r*Math.cos(b); sp[i*3+2] = r*Math.sin(b)*Math.sin(a); }
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
    scene.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xfff6e0, size: 0.09, transparent: true, opacity: .85, sizeAttenuation: true })));

    pins = ORIGINS.map((o, i) => {
      const [x, y, z] = toVec(o.lat, o.lon, R * 1.02); const grp = new THREE.Group(); grp.position.set(x, y, z);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.05, 20, 20),
        new THREE.MeshStandardMaterial({ color: 0xfff4cf, emissive: 0xe0a83c, emissiveIntensity: 1.5, roughness: .3 }));
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.07, 0.095, 28),
        new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: .85, side: THREE.DoubleSide }));
      ring.lookAt(new THREE.Vector3(x, y, z).multiplyScalar(2));
      grp.add(head, ring); grp.userData = { i, head, sel: i === selected }; globe.add(grp); return grp;
    });

    scene.add(new THREE.AmbientLight(0x53617a, 0.6));
    const sun = new THREE.DirectionalLight(0xfff5e8, 2.7); sun.position.set(4, 2, 3); scene.add(sun);
    const bounce = new THREE.DirectionalLight(0x5a93d6, 0.5); bounce.position.set(-4, -1, -3); scene.add(bounce);

    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
    canvas.style.cursor = 'grab'; canvas.style.touchAction = 'none';
    canvas.addEventListener('pointerdown', e => { drag.on = true; drag.x = e.clientX; drag.y = e.clientY; drag.moved = 0; try { canvas.setPointerCapture(e.pointerId); } catch (x) {} canvas.style.cursor = 'grabbing'; });
    canvas.addEventListener('pointermove', e => { if (!drag.on) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      rot.y += dx * 0.006; rot.x = Math.max(-1.1, Math.min(1.1, rot.x + dy * 0.006)); vel.y = dx * 0.006; vel.x = dy * 0.006; drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy); faceTarget = null; });
    const end = e => { if (!drag.on) return; drag.on = false; canvas.style.cursor = 'grab';
      if (drag.moved < 6) { const r = canvas.getBoundingClientRect(); ndc.x = ((e.clientX - r.left) / r.width) * 2 - 1; ndc.y = -((e.clientY - r.top) / r.height) * 2 + 1;
        ray.setFromCamera(ndc, camera); const hit = ray.intersectObjects(pins.map(p => p.userData.head))[0];
        if (hit) { const i = pins.findIndex(p => p.userData.head === hit.object); if (i >= 0) select(i, true); } } };
    canvas.addEventListener('pointerup', end); canvas.addEventListener('pointercancel', end);

    resize(); render();
    new ResizeObserver(() => { resize(); render(); }).observe(wrap || canvas);
    loop();
  }
  function faceOrigin(i) {
    const o = ORIGINS[i];
    let ty = -Math.PI / 2 - o.lon * Math.PI / 180;      // amène la longitude du pays face à la caméra
    while (ty - rot.y > Math.PI) ty -= 2 * Math.PI;      // chemin le plus court
    while (ty - rot.y < -Math.PI) ty += 2 * Math.PI;
    faceTarget = { y: ty, x: Math.max(-1, Math.min(1, o.lat * Math.PI / 180)) };
  }
  let lastW = 0;
  function resize() {
    const box = (wrap || canvas).getBoundingClientRect();
    const w = Math.round(box.width) || 480, h = Math.round(box.height) || 480;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); lastW = w;
  }
  function render() { globe.rotation.y = rot.y; globe.rotation.x = rot.x; renderer.render(scene, camera); }
  let t = 0;
  function loop() {
    requestAnimationFrame(loop); t += 0.016;
    if (canvas.clientWidth && canvas.clientWidth !== lastW) resize();
    if (!drag.on) { if (faceTarget) { rot.y += (faceTarget.y - rot.y) * 0.07; rot.x += (faceTarget.x - rot.x) * 0.07; if (Math.abs(faceTarget.y - rot.y) < 0.003) faceTarget = null; }
      else { rot.y += (RM ? 0 : 0.0015) + vel.y; rot.x += vel.x; vel.y *= 0.94; vel.x *= 0.94; } }
    globe.rotation.y = rot.y; globe.rotation.x = rot.x;
    if (pins) pins.forEach((p, i) => { const pulse = 1 + Math.sin(t * 2 + i) * 0.09; p.scale.setScalar((p.userData.sel ? 1.7 : 1) * pulse); p.userData.head.material.emissiveIntensity = p.userData.sel ? 2.3 : 1.3; });
    renderer.render(scene, camera);
  }
  new IntersectionObserver((es, ob) => { if (es[0].isIntersecting) { ob.disconnect(); init(); } }, { threshold: .05 }).observe(canvas);
})();
