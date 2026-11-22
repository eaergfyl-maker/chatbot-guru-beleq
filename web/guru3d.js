/* Guru Beleq in real-time 3D for the companion arch on /chat (Three.js r170, loaded from a CDN).

   Everything is built in code: lathed mahogany drum with painted grain, rope lacing, parchment face with
   moving eyes, blinking lids, brows and a talking mouth, tortoiseshell glasses, batik sapuk headcloth,
   jointed arms holding pemantok mallets, and legs that squash when he lands.

   Fallback: if WebGL is missing, Three.js cannot be fetched (offline), building fails, or the page has
   ?guru3d=off, nothing changes and /guru_3d.png keeps its CSS animations. The PNG is only hidden (class
   "has-3d" on #avatar-stage) after the first 3D frame has rendered, and comes back if the GPU context is lost.

   API, available once mounted (index.html guards every call with `if (window.Guru3D)`):
     Guru3D.setReaction(state, speaking)  idle | listening | greeting | teaching | celebrate | thinking | comfort | six_seven
     Guru3D.setTheme(theme)               morning | afternoon | evening (lights fade over 0.6 s)
     Guru3D.setListening(bool)            eyes follow the message box while the user types
     Guru3D.strike()                      one big mallet strike (clicking Guru Beleq)
   A "guru3d:ready" event fires on window when the canvas is live. */

const THREE_URLS = [
  'https://unpkg.com/three@0.170.0/build/three.module.js',
  'https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js',
];

const stage = document.getElementById('avatar-stage');
const wrap = document.getElementById('puppet-wrap');

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch (e) { return false; }
}

function wanted() {
  try { return new URLSearchParams(location.search).get('guru3d') !== 'off'; } catch (e) { return true; }
}

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error('timed out')), ms))]);
}

async function loadThree() {
  let last;
  for (const url of THREE_URLS) {
    try { return await withTimeout(import(url), 10000); } catch (e) { last = e; }
  }
  throw last;
}

// Small deterministic random generator, so the painted textures look the same on every visit.
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = t => t * t * (3 - 2 * t);

// ---------------------------------------------------------------------------------------------------------
// Scene lighting per time-of-day theme
// ---------------------------------------------------------------------------------------------------------
const LIGHTS = {
  morning: {
    hemiSky: '#e0f2fe', hemiGround: '#0f766e', hemi: 0.7,
    key: '#fff1d6', keyI: 2.5, keyPos: [4.5, 5, 2.6],
    fill: '#5eead4', fillI: 0.9, fillPos: [-4, 1, 2.5],
    rim: '#ffffff', rimI: 1.2, rimPos: [-1.5, 3, -4],
    lamp: '#ffb347', lampI: 0,
    env: ['#f0f9ff', '#bae6fd', '#99f6e4', '#0d9488'], envI: 0.5, shadow: 0.34, exposure: 0.95,
  },
  afternoon: {
    hemiSky: '#fed7aa', hemiGround: '#4c1d95', hemi: 0.85,
    key: '#ffc285', keyI: 2.3, keyPos: [-3.5, 2.6, 4],
    fill: '#fb7185', fillI: 0.8, fillPos: [4, 0.5, 2.5],
    rim: '#c084fc', rimI: 1.8, rimPos: [2.5, 2.5, -4],
    lamp: '#ffb347', lampI: 0,
    env: ['#ffedd5', '#fdba74', '#f43f5e', '#4c1d95'], envI: 0.5, shadow: 0.4, exposure: 0.95,
  },
  evening: {
    hemiSky: '#4f46e5', hemiGround: '#0f172a', hemi: 0.5,
    key: '#c7d2fe', keyI: 0.75, keyPos: [2, 4.5, 4],
    fill: '#6366f1', fillI: 0.45, fillPos: [-4, 1, 2.5],
    rim: '#93c5fd', rimI: 1.0, rimPos: [-2, 3, -4],
    lamp: '#ffb347', lampI: 7,
    env: ['#312e81', '#1e1b4b', '#3b2a1a', '#0f172a'], envI: 0.4, shadow: 0.55, exposure: 1.0,
  },
};

// ---------------------------------------------------------------------------------------------------------
// Reaction poses. Each returns a full pose for time t (seconds); switching state cross-fades two poses.
// Arm angles: sz = shoulder swing out (+ out for the right arm), sx = shoulder forward (-), ez = elbow,
// ex = elbow forward, ma = mallet angle in the picture plane (0 = straight up, + leans left), mx = mallet pitch.
// A hanging arm comes forward with sx < 0; a raised arm comes forward with sx > 0.
// ---------------------------------------------------------------------------------------------------------
function basePose() {
  return {
    y: 0, turn: 0, tilt: 0, lean: 0, squash: 1,
    bL: 0, bR: 0, bLr: 0, bRr: 0, lid: 0, low: 0,
    mw: 0.27, mc: 0.06, mo: 0.1, ms: 0, glass: 0,
    R_sz: 0.5, R_sx: -0.3, R_ez: 2.0, R_ex: 0.55, R_ma: -0.12, R_mx: 0.1,
    L_sz: -0.55, L_sx: -0.45, L_ez: -1.6, L_ex: 0.55, L_ma: 0.5, L_mx: 0.2,
  };
}

const pulse = ph => Math.pow(Math.max(0, Math.sin(ph)), 2);

const POSES = {
  idle(t) {
    const p = basePose();
    p.y = 0.035 * Math.sin(t * 1.8);
    p.squash = 1 + 0.012 * Math.sin(t * 1.8 + 1.4);
    p.tilt = 0.025 * Math.sin(t * 0.7);
    p.R_ma += 0.07 * Math.sin(t * 1.1);
    p.L_ma += 0.07 * Math.sin(t * 1.3 + 1);
    return p;
  },
  listening(t) {
    const p = basePose();
    p.turn = 0.26;               // ~15 degrees toward the chat column
    p.lean = 0.1;                // a little forward
    p.y = 0.02 * Math.sin(t * 2);
    p.bL = p.bR = 0.04;
    p.mc = 0.06; p.mo = 0.035;
    p.R_ma += 0.05 * Math.sin(t * 1.4);
    return p;
  },
  greeting(t) {
    const p = basePose();
    const b = Math.abs(Math.sin(t * Math.PI / 0.6));
    p.y = 0.12 * b;
    p.squash = 1 + 0.03 * b - 0.04 * (1 - b) * (1 - b);
    p.tilt = 0.06 * Math.sin(t * 3.5);
    p.bL = p.bR = 0.06;
    p.mw = 0.28; p.mc = 0.11; p.mo = 0.18;
    p.R_sz = 2.6 + 0.18 * Math.sin(t * 7); p.R_sx = 0.3; p.R_ez = 0.2; p.R_ex = 0.2; p.R_ma = -0.15 + 0.55 * Math.sin(t * 7); p.R_mx = 0.1;
    return p;
  },
  teaching(t) {
    const p = basePose();
    const ph = t * Math.PI * 2 / 0.5;          // dag-dug: one tap every quarter second, alternating hands
    p.y = 0.03 * Math.abs(Math.sin(ph / 2));
    const r = pulse(ph), l = pulse(ph + Math.PI);
    p.R_ma = -0.12 + 0.75 * r; p.R_ez -= 0.35 * r; p.R_sz -= 0.1 * r;
    p.L_ma = 0.5 - 0.75 * l; p.L_ez += 0.3 * l;
    p.bL = p.bR = 0.02 * Math.sin(t * 2);
    return p;
  },
  celebrate(t) {
    const p = basePose();
    const per = 0.78, ph = (t % per) / per;
    if (ph < 0.15) { p.squash = 1 - 0.13 * Math.sin(Math.PI * ph / 0.15); p.y = 0; }
    else if (ph < 0.82) { const a = (ph - 0.15) / 0.67; p.y = 0.42 * Math.sin(Math.PI * a); p.squash = 1.05; }
    else { p.squash = 1 - 0.1 * Math.sin(Math.PI * (ph - 0.82) / 0.18); p.y = 0; }
    p.lid = 0.42; p.low = 0.55;  // happy squint
    p.bL = p.bR = 0.08;
    p.mw = 0.29; p.mc = 0.13; p.mo = 0.21;
    p.R_sz = 0.85; p.R_ez = 1.75; p.R_ma = 0.15 + 0.4 * Math.sin(t * 42);
    p.L_sz = -0.85; p.L_ez = -1.4; p.L_ma = 0.25 - 0.4 * Math.sin(t * 42 + 1.3);
    return p;
  },
  thinking(t) {
    const p = basePose();
    p.tilt = 0.15 + 0.025 * Math.sin(t * 2);
    p.y = 0.025 * Math.sin(t * 2.6);
    p.bL = 0.09; p.bLr = 0.12; p.bR = -0.02; p.bRr = -0.12;
    p.mw = 0.15; p.mc = 0.0; p.mo = 0.016; p.ms = 0.04;
    p.L_sz = 2.25; p.L_sx = 0.75; p.L_ez = 0.35; p.L_ex = 0.1; p.L_ma = 0.7; p.L_mx = -0.2;   // hand up to the glasses
    p.glass = 0.012 * Math.sin(t * 3);
    p.R_ma += 0.05 * Math.sin(t * 1.2);
    return p;
  },
  comfort(t) {
    const p = basePose();
    p.tilt = 0.11 + 0.04 * Math.sin(t * 1.2);
    p.lean = 0.06 * Math.sin(t * 1.6);         // slow reassuring nod
    p.y = 0.015 * Math.sin(t * 1.6);
    p.bL = p.bR = 0.03; p.bLr = 0.2; p.bRr = -0.2;
    p.mw = 0.19; p.mc = 0.035; p.mo = 0.02;
    p.lid = 0.15;
    return p;
  },
  six_seven(t) {
    const p = basePose();
    const s = Math.sin(t * 11);
    p.y = 0.05 * Math.abs(Math.sin(t * 11));
    p.mw = 0.27; p.mc = 0.11; p.mo = 0.15;
    p.bL = p.bR = 0.05;
    p.R_sz = 0.75 + 0.5 * s; p.R_ez = 1.9; p.R_ma = -0.05;
    p.L_sz = -0.75 + 0.5 * s; p.L_ez = -1.9; p.L_ma = 0.05; p.L_sx = -0.5;
    return p;
  },
};

function mixPose(a, b, t) {
  const out = {};
  for (const k in a) out[k] = lerp(a[k], b[k], t);
  return out;
}

// ---------------------------------------------------------------------------------------------------------
// Build and run
// ---------------------------------------------------------------------------------------------------------
function mount(THREE) {
  const rand = mulberry32(20261122);
  const reduceMotion = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);

  const canvas = document.createElement('canvas');
  canvas.id = 'guru3d-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  wrap.insertBefore(canvas, document.getElementById('particles'));

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 60);

  // ---------- painted textures ----------
  function canvasTex(w, h, draw, opts = {}) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    if (opts.srgb !== false) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    if (opts.repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(opts.repeat[0], opts.repeat[1]); }
    return t;
  }
  function speckle(g, w, h, n, color, maxR) {
    g.fillStyle = color;
    for (let i = 0; i < n; i++) { g.beginPath(); g.arc(rand() * w, rand() * h, rand() * maxR, 0, Math.PI * 2); g.fill(); }
  }

  const grainLines = [];
  for (let i = 0; i < 170; i++) grainLines.push({ x: rand(), dark: rand() < 0.62, a: rand(), wgt: rand(), ph: rand() * 6 });
  const woodTex = canvasTex(512, 512, (g, w, h) => {
    const base = g.createLinearGradient(0, 0, w, 0);
    base.addColorStop(0, '#7a3416'); base.addColorStop(0.5, '#9c4a22'); base.addColorStop(1, '#7a3416');
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    grainLines.forEach(l => {
      g.strokeStyle = l.dark ? `rgba(55,18,6,${0.18 + l.a * 0.32})` : `rgba(196,112,58,${0.08 + l.a * 0.16})`;
      g.lineWidth = 0.6 + l.wgt * 2.4;
      g.beginPath();
      let x = l.x * w;
      for (let y = 0; y <= h; y += 12) {
        x += Math.sin(y * 0.018 + l.ph) * 0.9 + (rand() - 0.5) * 1.6;
        if (y === 0) g.moveTo(x, y); else g.lineTo(x, y);
      }
      g.stroke();
    });
    for (let k = 0; k < 3; k++) {               // a few knots
      const kx = rand() * w, ky = rand() * h;
      for (let r = 3; r < 26; r += 3) {
        g.strokeStyle = `rgba(50,16,5,${0.25 - r * 0.007})`; g.lineWidth = 1.2;
        g.beginPath(); g.ellipse(kx, ky, r * 0.55, r * 1.6, 0, 0, Math.PI * 2); g.stroke();
      }
    }
  }, { repeat: [2, 1] });
  const woodRough = canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = '#9a9a9a'; g.fillRect(0, 0, w, h);
    grainLines.forEach(l => {
      g.strokeStyle = l.dark ? 'rgba(210,210,210,0.5)' : 'rgba(80,80,80,0.45)';
      g.lineWidth = 0.5 + l.wgt * 1.4;
      g.beginPath(); g.moveTo(l.x * w, 0); g.lineTo(l.x * w + Math.sin(l.ph) * 6, h); g.stroke();
    });
  }, { srgb: false, repeat: [2, 1] });

  const R = 1, D = 1.1, ZF = D / 2;            // drum radius, depth, front-face z
  const RCAP = 0.955, RS = 2.0;                // drumhead: a shallow spherical cap
  const CAP_T = Math.asin(RCAP / RS), CAP_H = RS * (1 - Math.cos(CAP_T)), ZC = ZF + CAP_H - RS;
  const faceZ = (x, y) => ZC + Math.sqrt(Math.max(0, RS * RS - x * x - y * y));
  const toUV = (x, y) => [x / (2 * RCAP) + 0.5, y / (2 * RCAP) + 0.5];

  const parchTex = canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#e6cc9c'; g.fillRect(0, 0, w, h);
    const v = g.createRadialGradient(w / 2, h / 2, w * 0.1, w / 2, h / 2, w * 0.52);
    v.addColorStop(0, 'rgba(250,234,200,0.6)'); v.addColorStop(0.68, 'rgba(240,220,180,0)'); v.addColorStop(1, 'rgba(150,100,45,0.55)');
    g.fillStyle = v; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 40; i++) {               // soft blotches
      const x = rand() * w, y = rand() * h, r = 10 + rand() * 40;
      const b = g.createRadialGradient(x, y, 0, x, y, r);
      b.addColorStop(0, 'rgba(176,132,80,0.08)'); b.addColorStop(1, 'rgba(176,132,80,0)');
      g.fillStyle = b; g.fillRect(x - r, y - r, r * 2, r * 2);
    }
    for (let i = 0; i < 320; i++) {              // hide fibres
      const x = rand() * w, y = rand() * h, a = rand() * Math.PI;
      g.strokeStyle = `rgba(140,98,52,${0.05 + rand() * 0.07})`; g.lineWidth = 0.7;
      g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a) * 9, y + Math.sin(a) * 4, x + Math.cos(a) * 18, y + Math.sin(a) * 9); g.stroke();
    }
    speckle(g, w, h, 2600, 'rgba(120,84,44,0.07)', 1.1);
    [[-0.56, -0.2], [0.56, -0.2]].forEach(([x, y]) => {   // rosy cheeks
      const [u, vv] = toUV(x, y), cx = u * w, cy = (1 - vv) * h, r = w * 0.11;
      const c = g.createRadialGradient(cx, cy, 0, cx, cy, r);
      c.addColorStop(0, 'rgba(226,96,84,0.7)'); c.addColorStop(1, 'rgba(226,96,84,0)');
      g.fillStyle = c; g.fillRect(cx - r, cy - r, r * 2, r * 2);
    });
  });

  const tortoiseTex = canvasTex(256, 64, (g, w, h) => {
    g.fillStyle = '#6b3410'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 70; i++) {
      const x = rand() * w, y = rand() * h, r = 3 + rand() * 11;
      const col = rand() < 0.5 ? '194,122,44' : rand() < 0.5 ? '42,18,6' : '226,160,72';
      const b = g.createRadialGradient(x, y, 0, x, y, r);
      b.addColorStop(0, `rgba(${col},0.85)`); b.addColorStop(1, `rgba(${col},0)`);
      g.fillStyle = b; g.beginPath(); g.ellipse(x, y, r * 1.6, r, 0, 0, Math.PI * 2); g.fill();
    }
  }, { repeat: [3, 1] });

  const batikTex = canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#8f1d24'; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(92,10,16,0.55)'; g.lineWidth = 9;
    for (let i = -h; i < w; i += 46) { g.beginPath(); g.moveTo(i, h); g.lineTo(i + h, 0); g.stroke(); }
    const cream = 'rgba(244,218,170,0.92)';
    g.strokeStyle = cream; g.fillStyle = cream; g.lineWidth = 2.4; g.lineCap = 'round';
    for (let i = 0; i < 22; i++) {               // spirals (pakis / fern motif)
      const cx = rand() * w, cy = rand() * h, turns = 2 + rand() * 1.5, s = 4 + rand() * 4;
      g.beginPath();
      for (let a = 0; a < turns * Math.PI * 2; a += 0.2) {
        const r = s * a * 0.35, x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
        if (a === 0) g.moveTo(x, y); else g.lineTo(x, y);
      }
      g.stroke();
    }
    for (let i = 0; i < 26; i++) {               // four-petal flowers
      const cx = rand() * w, cy = rand() * h, s = 5 + rand() * 6;
      for (let k = 0; k < 4; k++) {
        const a = k * Math.PI / 2;
        g.beginPath(); g.ellipse(cx + Math.cos(a) * s, cy + Math.sin(a) * s, s * 0.75, s * 0.35, a, 0, Math.PI * 2); g.fill();
      }
      g.fillStyle = '#8f1d24'; g.beginPath(); g.arc(cx, cy, s * 0.35, 0, Math.PI * 2); g.fill(); g.fillStyle = cream;
    }
    for (let row = 0; row < 6; row++) {          // dotted isen lines
      const y = (row + 0.5) * h / 6 + (rand() - 0.5) * 20;
      for (let x = 0; x < w; x += 9) { g.beginPath(); g.arc(x, y + Math.sin(x * 0.05 + row) * 5, 1.4, 0, Math.PI * 2); g.fill(); }
    }
  }, { repeat: [3, 2] });

  const clothTex = canvasTex(128, 128, (g, w, h) => {
    g.fillStyle = '#d8c09a'; g.fillRect(0, 0, w, h);
    speckle(g, w, h, 1400, 'rgba(255,248,230,0.35)', 1.2);
    speckle(g, w, h, 1200, 'rgba(120,90,50,0.22)', 1.1);
  }, { repeat: [2, 2] });

  const irisTex = canvasTex(64, 64, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h);   // top = centre of the iris, bottom = its rim
    gr.addColorStop(0, '#3a1c08'); gr.addColorStop(0.35, '#b8752f'); gr.addColorStop(0.75, '#8a4e1c'); gr.addColorStop(1, '#3d1d08');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 40; i++) {
      g.strokeStyle = `rgba(${rand() < 0.5 ? '230,170,90' : '60,28,8'},0.35)`; g.lineWidth = 1;
      const x = rand() * w; g.beginPath(); g.moveTo(x, h * 0.2); g.lineTo(x + (rand() - 0.5) * 3, h * 0.95); g.stroke();
    }
  });

  // ---------- materials ----------
  const M = {
    wood: new THREE.MeshPhysicalMaterial({ map: woodTex, roughnessMap: woodRough, roughness: 0.55, clearcoat: 0.1, clearcoatRoughness: 0.5, envMapIntensity: 0.35 }),
    woodBack: new THREE.MeshStandardMaterial({ color: '#4a1d0a', roughness: 0.8 }),
    hoop: new THREE.MeshPhysicalMaterial({ color: '#a8683a', roughness: 0.55, clearcoat: 0.2 }),
    rope: new THREE.MeshStandardMaterial({ color: '#e6cf9f', roughness: 0.92 }),
    face: new THREE.MeshPhysicalMaterial({ map: parchTex, roughness: 0.72, sheen: 0.35, sheenRoughness: 0.8, sheenColor: new THREE.Color('#fff1d6') }),
    skin: new THREE.MeshPhysicalMaterial({ color: '#e2c796', roughness: 0.7, sheen: 0.3, sheenRoughness: 0.8, sheenColor: new THREE.Color('#fff1d6') }),
    nose: new THREE.MeshPhysicalMaterial({ color: '#dcae7c', roughness: 0.6, sheen: 0.3, sheenColor: new THREE.Color('#ffe9cc') }),
    eye: new THREE.MeshPhysicalMaterial({ color: '#fbf7ef', roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08 }),
    iris: new THREE.MeshPhysicalMaterial({ map: irisTex, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.05 }),
    pupil: new THREE.MeshPhysicalMaterial({ color: '#140905', roughness: 0.2, clearcoat: 1 }),
    glint: new THREE.MeshBasicMaterial({ color: '#ffffff' }),
    brow: new THREE.MeshStandardMaterial({ color: '#4a240f', roughness: 0.65 }),
    mouth: new THREE.MeshStandardMaterial({ color: '#4c1013', roughness: 0.6, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2 }),
    teeth: new THREE.MeshStandardMaterial({ color: '#fbf5e8', roughness: 0.35, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -4 }),
    tongue: new THREE.MeshStandardMaterial({ color: '#d45c66', roughness: 0.5, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -3 }),
    tortoise: new THREE.MeshPhysicalMaterial({ map: tortoiseTex, roughness: 0.28, clearcoat: 1, clearcoatRoughness: 0.1 }),
    lens: new THREE.MeshPhysicalMaterial({ color: '#eef7ff', roughness: 0.05, metalness: 0, clearcoat: 1, transparent: true, opacity: 0.16, depthWrite: false }),
    batik: new THREE.MeshPhysicalMaterial({ map: batikTex, roughness: 0.82, sheen: 1, sheenRoughness: 0.5, sheenColor: new THREE.Color('#ff9a8a') }),
    limb: new THREE.MeshPhysicalMaterial({ color: '#5a2f18', roughness: 0.55, sheen: 0.25, sheenColor: new THREE.Color('#c78a5c') }),
    shoe: new THREE.MeshPhysicalMaterial({ color: '#3a1f10', roughness: 0.45, clearcoat: 0.4 }),
    shaft: new THREE.MeshPhysicalMaterial({ color: '#c58a4e', roughness: 0.45, clearcoat: 0.4 }),
    cloth: new THREE.MeshStandardMaterial({ map: clothTex, roughness: 1 }),
    cord: new THREE.MeshStandardMaterial({ color: '#b3262d', roughness: 0.7 }),
  };

  const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
  const mesh = (geo, mat, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); return m; };
  function rod(a, b, r, mat) {
    const d = new THREE.Vector3().subVectors(b, a), len = d.length();
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 10), mat);
    m.position.copy(a).addScaledVector(d, 0.5);
    m.quaternion.setFromUnitVectors(V3(0, 1, 0), d.normalize());
    return m;
  }

  // ---------- rig hierarchy ----------
  // char: pivot at the feet (tilts and leans rotate around the ground)
  //   legs (squash) / bodyBase at the drum's bottom (squash and stretch) / body at the drum's centre
  const char = new THREE.Group();
  scene.add(char);
  const LEG_TOP = 0.56;
  const legs = new THREE.Group(); char.add(legs);
  const bodyBase = new THREE.Group(); bodyBase.position.y = LEG_TOP; char.add(bodyBase);
  const body = new THREE.Group(); body.position.y = R; bodyBase.add(body);

  // drum: lathed barrel with a slight bulge, axis along z
  const prof = [];
  for (let i = 0; i <= 18; i++) { const s = i / 18; prof.push(new THREE.Vector2(R * (1 + 0.055 * (1 - Math.pow(2 * s - 1, 2))), -ZF + D * s)); }
  const radiusAt = z => R * (1 + 0.055 * (1 - Math.pow(z / ZF, 2)));
  const barrel = new THREE.LatheGeometry(prof, 72);
  barrel.rotateX(Math.PI / 2);
  body.add(mesh(barrel, M.wood));
  const backCap = new THREE.CircleGeometry(R, 48); backCap.rotateY(Math.PI);
  body.add(mesh(backCap, M.woodBack, 0, 0, -ZF));
  const hoopGeo = new THREE.TorusGeometry(R + 0.02, 0.07, 18, 80);
  body.add(mesh(hoopGeo, M.hoop, 0, 0, ZF));
  body.add(mesh(hoopGeo, M.hoop, 0, 0, -ZF));

  // zig-zag rope lacing between the two hoops, following the bulge
  const N = 9, pts = [], zA = ZF - 0.08, zB = -ZF + 0.08;
  for (let i = 0; i < N; i++) {
    const a0 = (i / N) * Math.PI * 2, a1 = a0 + Math.PI / N, a2 = a0 + 2 * Math.PI / N;
    [[a0, zA, a1, zB], [a1, zB, a2, zA]].forEach(([s0, z0, s1, z1]) => {
      for (let k = 0; k < 8; k++) {
        const t = k / 8, a = lerp(s0, s1, t), z = lerp(z0, z1, t), r = radiusAt(z) + 0.03;
        pts.push(V3(Math.cos(a) * r, Math.sin(a) * r, z));
      }
    });
  }
  body.add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true, 'centripetal'), N * 64, 0.03, 6, true), M.rope));
  const pegGeo = new THREE.SphereGeometry(0.045, 10, 8);
  for (let i = 0; i < N; i++) {
    const a0 = (i / N) * Math.PI * 2, a1 = a0 + Math.PI / N;
    body.add(mesh(pegGeo, M.rope, Math.cos(a0) * (R + 0.06), Math.sin(a0) * (R + 0.06), zA));
    body.add(mesh(pegGeo, M.rope, Math.cos(a1) * (R + 0.06), Math.sin(a1) * (R + 0.06), zB));
  }

  // ---------- face ----------
  const face = new THREE.Group(); body.add(face);
  const capGeo = new THREE.SphereGeometry(RS, 72, 18, 0, Math.PI * 2, 0, CAP_T);
  capGeo.rotateX(Math.PI / 2);
  capGeo.translate(0, 0, ZC);
  { // planar UVs so the painted cheeks land where they should
    const p = capGeo.attributes.position, uv = capGeo.attributes.uv;
    for (let i = 0; i < p.count; i++) { const [u, v] = toUV(p.getX(i), p.getY(i)); uv.setXY(i, u, v); }
    uv.needsUpdate = true;
  }
  face.add(mesh(capGeo, M.face));

  const EYE_R = 0.165, EYE_X = 0.32, EYE_Y = 0.14;
  const eyes = [-1, 1].map(s => {
    const x = s * EYE_X, holder = new THREE.Group();
    holder.position.set(x, EYE_Y, faceZ(x, EYE_Y) - 0.045);
    face.add(holder);
    holder.add(mesh(new THREE.SphereGeometry(EYE_R, 32, 24), M.eye));
    const look = new THREE.Group(); holder.add(look);
    const irisGeo = new THREE.SphereGeometry(EYE_R * 1.004, 32, 10, 0, Math.PI * 2, 0, 0.64); irisGeo.rotateX(Math.PI / 2);
    const pupilGeo = new THREE.SphereGeometry(EYE_R * 1.009, 24, 6, 0, Math.PI * 2, 0, 0.3); pupilGeo.rotateX(Math.PI / 2);
    look.add(mesh(irisGeo, M.iris));
    look.add(mesh(pupilGeo, M.pupil));
    holder.add(mesh(new THREE.SphereGeometry(0.028, 12, 8), M.glint, -0.05, 0.06, EYE_R * 0.93));
    holder.add(mesh(new THREE.SphereGeometry(0.012, 8, 6), M.glint, 0.045, -0.035, EYE_R * 0.96));
    const upper = mesh(new THREE.SphereGeometry(EYE_R * 1.07, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2), M.skin);
    const lower = mesh(new THREE.SphereGeometry(EYE_R * 1.065, 32, 12, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), M.skin);
    holder.add(upper, lower);
    return { look, upper, lower };
  });

  const brows = [-1, 1].map(s => {
    const x = s * 0.34, y = 0.45, g = new THREE.Group();
    g.position.set(x, y, faceZ(x, y) + 0.035);
    const cap = new THREE.CapsuleGeometry(0.043, 0.17, 6, 12); cap.rotateZ(Math.PI / 2);
    const m = mesh(cap, M.brow); m.rotation.z = s * -0.14; m.scale.set(1, 1, 0.8);
    g.add(m); face.add(g);
    return { g, baseY: y, s };
  });

  const noseY = -0.065;
  const nose = mesh(new THREE.SphereGeometry(0.085, 24, 16), M.nose, 0, noseY, faceZ(0, noseY) + 0.02);
  nose.scale.set(1.08, 0.86, 0.85); face.add(nose);

  // mouth: three strips (cavity, upper teeth, tongue) rebuilt from four numbers every frame
  const MN = 22, MOUTH_Y = -0.34;
  function strip(mat) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array((MN + 1) * 6), 3));
    const idx = [];
    for (let i = 0; i < MN; i++) { const a = 2 * i; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    g.setIndex(idx);
    const m = new THREE.Mesh(g, mat); m.frustumCulled = false; face.add(m);
    return m;
  }
  const cavity = strip(M.mouth), teeth = strip(M.teeth), tongue = strip(M.tongue);
  function fill(m, span, top, bot, dz) {
    const arr = m.geometry.attributes.position.array;
    for (let i = 0; i <= MN; i++) {
      const t = -1 + 2 * i / MN, [x, yt] = top(t * span), yb = bot(t * span);
      arr.set([x, yt, faceZ(x, yt) + dz, x, yb, faceZ(x, yb) + dz], i * 6);
    }
    m.geometry.attributes.position.needsUpdate = true;
    m.geometry.computeVertexNormals();
    m.geometry.computeBoundingSphere();
  }
  function setMouth(w, c, o, s) {
    const base = t => MOUTH_Y + c * t * t + s * t;
    const up = t => base(t) + o * 0.22 * (1 - t * t);
    const lo = t => Math.min(base(t) - o * (1 - t * t), up(t) - 0.017 * (1 - 0.6 * t * t));
    const gap = up(0) - lo(0);
    const th = Math.min(0.045, gap * 0.36), tg = Math.min(0.06, gap * 0.42);
    fill(cavity, 1, t => [w * t, up(t)], lo, 0.006);
    fill(teeth, 0.72, t => [w * t, up(t) - 0.004], t => up(t) - 0.004 - th * Math.sqrt(Math.max(0, 1 - (t / 0.72) ** 2)), 0.009);
    fill(tongue, 0.58, t => [w * t, lo(t) + 0.004 + tg * (1 - (t / 0.58) ** 2)], t => lo(t) + 0.004, 0.008);
    teeth.visible = gap > 0.035; tongue.visible = gap > 0.03;
  }

  // tortoiseshell spectacles
  const glasses = new THREE.Group(); face.add(glasses);
  const GZ = faceZ(EYE_X, EYE_Y) + 0.17, RIM = 0.25;
  [-1, 1].forEach(s => {
    const rim = mesh(new THREE.TorusGeometry(RIM, 0.043, 16, 56), M.tortoise, s * EYE_X, EYE_Y, GZ);
    glasses.add(rim);
    glasses.add(mesh(new THREE.CircleGeometry(RIM - 0.01, 40), M.lens, s * EYE_X, EYE_Y, GZ - 0.005));
    glasses.add(rod(V3(s * (EYE_X + RIM), EYE_Y + 0.03, GZ - 0.01), V3(s * 0.99, EYE_Y + 0.12, ZF - 0.32), 0.026, M.tortoise));
  });
  const bridge = mesh(new THREE.TorusGeometry(EYE_X - RIM + 0.005, 0.03, 10, 20, Math.PI), M.tortoise, 0, EYE_Y + 0.02, GZ + 0.005);
  glasses.add(bridge);

  // ---------- batik sapuk headcloth ----------
  const sapuk = new THREE.Group(); body.add(sapuk);
  const dome = mesh(new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.62), M.batik, 0, 0.7, 0.02);
  dome.scale.set(1.0, 0.56, 0.84); sapuk.add(dome);
  const bandGeo = new THREE.TorusGeometry(1, 0.17, 18, 72); bandGeo.rotateX(Math.PI / 2);
  const band = mesh(bandGeo, M.batik, 0, 0.7, 0.05); band.scale.set(0.84, 0.95, 0.8); sapuk.add(band);
  const wrapGeo = new THREE.TorusGeometry(1, 0.1, 14, 64); wrapGeo.rotateX(Math.PI / 2);
  const wrap2 = mesh(wrapGeo, M.batik, 0.02, 0.88, 0.03); wrap2.scale.set(0.82, 1, 0.74); wrap2.rotation.z = 0.22; sapuk.add(wrap2);
  const wrap3 = mesh(wrapGeo, M.batik, -0.03, 1.03, 0.0); wrap3.scale.set(0.66, 1, 0.6); wrap3.rotation.z = -0.28; sapuk.add(wrap3);
  const lobe = new THREE.SphereGeometry(1, 24, 16);
  sapuk.add(mesh(new THREE.SphereGeometry(0.15, 20, 14), M.batik, 0.04, 1.22, 0.32));
  [[-0.23, 1.28, 0.3, 0, 0, 0.95, [0.14, 0.29, 0.08]],
   [0.27, 1.29, 0.3, 0, 0, -1.0, [0.14, 0.29, 0.08]],
   [0.05, 1.45, 0.22, -0.45, 0, -0.1, [0.12, 0.27, 0.07]],
   [0.58, 0.98, -0.3, 0.3, 0.4, -1.25, [0.1, 0.24, 0.06]]].forEach(([x, y, z, rx, ry, rz, sc]) => {
    const m = mesh(lobe, M.batik, x, y, z); m.rotation.set(rx, ry, rz); m.scale.set(...sc); sapuk.add(m);
  });

  // ---------- arms with pemantok mallets ----------
  function makeArm(s) {
    const shoulder = new THREE.Group(); shoulder.position.set(s * 0.82, -0.32, 0.48); body.add(shoulder);
    shoulder.add(mesh(new THREE.CapsuleGeometry(0.075, 0.26, 6, 12), M.limb, 0, -0.17, 0));
    const elbow = new THREE.Group(); elbow.position.y = -0.34; shoulder.add(elbow);
    elbow.add(mesh(new THREE.SphereGeometry(0.078, 14, 10), M.limb));
    elbow.add(mesh(new THREE.CapsuleGeometry(0.07, 0.22, 6, 12), M.limb, 0, -0.15, 0));
    const wrist = new THREE.Group(); wrist.position.y = -0.31; elbow.add(wrist);
    const hand = mesh(new THREE.SphereGeometry(0.105, 18, 14), M.limb); hand.scale.set(1, 0.95, 0.9); wrist.add(hand);
    wrist.add(mesh(new THREE.SphereGeometry(0.045, 12, 10), M.limb, -s * 0.07, 0.03, 0.07));
    const mallet = new THREE.Group(); wrist.add(mallet);
    mallet.add(mesh(new THREE.CylinderGeometry(0.03, 0.034, 0.8, 12), M.shaft, 0, 0.25, 0));
    mallet.add(mesh(new THREE.SphereGeometry(0.036, 10, 8), M.shaft, 0, -0.15, 0));
    const head = mesh(new THREE.SphereGeometry(0.125, 20, 16), M.cloth, 0, 0.72, 0); head.scale.set(1, 1.15, 1); mallet.add(head);
    const cordGeo = new THREE.TorusGeometry(0.075, 0.022, 8, 20); cordGeo.rotateX(Math.PI / 2);
    mallet.add(mesh(cordGeo, M.cord, 0, 0.6, 0));
    return { shoulder, elbow, wrist, mallet, s };
  }
  const armR = makeArm(1), armL = makeArm(-1);

  // ---------- legs and shoes ----------
  [-1, 1].forEach(s => {
    legs.add(mesh(new THREE.CapsuleGeometry(0.105, 0.3, 6, 12), M.limb, s * 0.3, 0.36, 0.06));
    const shoe = mesh(new THREE.SphereGeometry(0.1, 20, 14), M.shoe, s * 0.32, 0.09, 0.13);
    shoe.scale.set(1.75, 0.95, 2.3); legs.add(shoe);
  });

  // ---------- soft contact shadow ----------
  const shadowTex = canvasTex(128, 64, (g, w, h) => {
    g.setTransform(1, 0, 0, h / w, 0, 0);        // squash a circle into a soft ellipse
    const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    r.addColorStop(0, 'rgba(0,0,0,0.9)'); r.addColorStop(0.45, 'rgba(0,0,0,0.45)'); r.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = r; g.fillRect(0, 0, w, w);
  }, { srgb: false });
  const shadowMat = new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false, opacity: 0.35, color: '#000000' });
  const shadowGeo = new THREE.PlaneGeometry(2.3, 1.0); shadowGeo.rotateX(-Math.PI / 2);
  const shadow = mesh(shadowGeo, shadowMat, 0, -1.5, 0.05); scene.add(shadow);
  const GROUND = -1.5;

  // ---------- lights ----------
  const hemi = new THREE.HemisphereLight('#ffffff', '#444444', 1); scene.add(hemi);
  const key = new THREE.DirectionalLight('#ffffff', 2); scene.add(key);
  const fillL = new THREE.DirectionalLight('#ffffff', 1); scene.add(fillL);
  const rim = new THREE.DirectionalLight('#ffffff', 1); scene.add(rim);
  const lamp = new THREE.PointLight('#ffb347', 0, 9, 1.6); lamp.position.set(1.7, 0.9, 2.4); scene.add(lamp);
  const pmrem = new THREE.PMREMGenerator(renderer);
  let envTarget = null;
  function setEnvironment(cols) {
    const tex = canvasTex(256, 128, (g, w, h) => {
      const gr = g.createLinearGradient(0, 0, 0, h);
      cols.forEach((c, i) => gr.addColorStop(i / (cols.length - 1), c));
      g.fillStyle = gr; g.fillRect(0, 0, w, h);
      const sun = g.createRadialGradient(w * 0.62, h * 0.28, 0, w * 0.62, h * 0.28, w * 0.16);
      sun.addColorStop(0, 'rgba(255,255,255,0.9)'); sun.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = sun; g.fillRect(0, 0, w, h);
    });
    tex.mapping = THREE.EquirectangularReflectionMapping;
    const next = pmrem.fromEquirectangular(tex);
    tex.dispose();
    scene.environment = next.texture;
    if (envTarget) envTarget.dispose();
    envTarget = next;
  }

  const lightNow = {};       // current (interpolated) light values
  let lightFrom = null, lightTo = null, lightT0 = 0;
  function snapshotLights() {
    return {
      hemiSky: hemi.color.clone(), hemiGround: hemi.groundColor.clone(), hemi: hemi.intensity,
      key: key.color.clone(), keyI: key.intensity, keyPos: key.position.clone(),
      fill: fillL.color.clone(), fillI: fillL.intensity, fillPos: fillL.position.clone(),
      rim: rim.color.clone(), rimI: rim.intensity, rimPos: rim.position.clone(),
      lamp: lamp.color.clone(), lampI: lightNow.lampI || 0,
      envI: scene.environmentIntensity, shadow: shadowMat.userData.base || 0.35, exposure: renderer.toneMappingExposure,
    };
  }
  function prepared(cfg) {
    return {
      hemiSky: new THREE.Color(cfg.hemiSky), hemiGround: new THREE.Color(cfg.hemiGround), hemi: cfg.hemi,
      key: new THREE.Color(cfg.key), keyI: cfg.keyI, keyPos: V3(...cfg.keyPos),
      fill: new THREE.Color(cfg.fill), fillI: cfg.fillI, fillPos: V3(...cfg.fillPos),
      rim: new THREE.Color(cfg.rim), rimI: cfg.rimI, rimPos: V3(...cfg.rimPos),
      lamp: new THREE.Color(cfg.lamp), lampI: cfg.lampI,
      envI: cfg.envI, shadow: cfg.shadow, exposure: cfg.exposure,
    };
  }
  function applyLights(a, b, t) {
    hemi.color.copy(a.hemiSky).lerp(b.hemiSky, t); hemi.groundColor.copy(a.hemiGround).lerp(b.hemiGround, t);
    hemi.intensity = lerp(a.hemi, b.hemi, t);
    key.color.copy(a.key).lerp(b.key, t); key.intensity = lerp(a.keyI, b.keyI, t); key.position.copy(a.keyPos).lerp(b.keyPos, t);
    fillL.color.copy(a.fill).lerp(b.fill, t); fillL.intensity = lerp(a.fillI, b.fillI, t); fillL.position.copy(a.fillPos).lerp(b.fillPos, t);
    rim.color.copy(a.rim).lerp(b.rim, t); rim.intensity = lerp(a.rimI, b.rimI, t); rim.position.copy(a.rimPos).lerp(b.rimPos, t);
    lamp.color.copy(a.lamp).lerp(b.lamp, t); lightNow.lampI = lerp(a.lampI, b.lampI, t);
    scene.environmentIntensity = lerp(a.envI, b.envI, t);
    shadowMat.userData.base = lerp(a.shadow, b.shadow, t);
    renderer.toneMappingExposure = lerp(a.exposure, b.exposure, t);
  }
  let theme = null;
  function setTheme(next, instant) {
    if (!LIGHTS[next] || next === theme) return;
    theme = next;
    setEnvironment(LIGHTS[next].env);
    lightFrom = instant ? prepared(LIGHTS[next]) : snapshotLights();
    lightTo = prepared(LIGHTS[next]);
    lightT0 = performance.now();
    if (instant) applyLights(lightTo, lightTo, 1);
  }
  setTheme(document.documentElement.dataset.theme || 'morning', true);

  // ---------- framing ----------
  const FRAME_H = 3.5, FRAME_W = 3.6, FRAME_CY = 0.1;
  function resize() {
    const w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const tan = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const dist = Math.max((FRAME_H / 2) / tan, (FRAME_W / 2) / (tan * camera.aspect));
    camera.position.set(0, FRAME_CY + 0.35, dist);
    camera.lookAt(0, FRAME_CY, 0);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  // ---------- state ----------
  const initial = (stage.className.match(/state-(\w+)/) || [])[1];
  let state = POSES[initial] ? initial : 'idle', prevState = state, blendT0 = -10;
  let speakUntil = stage.classList.contains('speaking') ? performance.now() + 2400 : 0;
  let listening = false, strikeAt = -10;
  const BLEND = 0.35;

  // pointer / gaze
  let gazeX = 0, gazeY = 0, gazeTX = 0, gazeTY = 0, lastPointer = performance.now();
  function aimAt(clientX, clientY) {
    const r = canvas.getBoundingClientRect();
    gazeTX = clamp((clientX - (r.left + r.width / 2)) / (window.innerWidth * 0.42), -1, 1);
    gazeTY = clamp(((r.top + r.height * 0.42) - clientY) / (window.innerHeight * 0.5), -1, 1);
  }
  window.addEventListener('pointermove', e => {
    lastPointer = performance.now();
    if (!listening) aimAt(e.clientX, e.clientY);
  }, { passive: true });
  function aimAtBox() {
    const box = document.getElementById('box');
    if (!box) return;
    const r = box.getBoundingClientRect();
    aimAt(r.left + Math.min(r.width * 0.25, 160), r.top + r.height / 2);
  }

  // drag to spin (springs back), and a drag must not count as a click on Guru Beleq
  let dragging = false, dragYaw = 0, dragVel = 0, dragX = 0, dragMoved = 0, dragLastT = 0;
  canvas.addEventListener('pointerdown', e => {
    dragging = true; dragX = e.clientX; dragMoved = 0; dragLastT = performance.now();
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add('dragging');
  });
  canvas.addEventListener('pointermove', e => {
    if (!dragging) return;
    const dx = e.clientX - dragX, now = performance.now();
    dragX = e.clientX; dragMoved += Math.abs(dx);
    dragYaw = clamp(dragYaw + dx * 0.012, -Math.PI * 1.2, Math.PI * 1.2);
    dragVel = dx * 0.012 / Math.max(0.008, (now - dragLastT) / 1000);
    dragLastT = now;
  });
  const endDrag = () => { dragging = false; canvas.classList.remove('dragging'); };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('click', e => {
    if (dragMoved > 6) { e.stopPropagation(); e.preventDefault(); }
    dragMoved = 0;
  });

  // blinking
  let nextBlink = performance.now() + 2500, blinkStart = -1, doubleBlink = false;
  function blinkAmount(now) {
    if (blinkStart < 0 && now > nextBlink) { blinkStart = now; doubleBlink = Math.random() < 0.18; }
    if (blinkStart < 0) return 0;
    const dur = doubleBlink ? 360 : 160, k = (now - blinkStart) / dur;
    if (k >= 1) { blinkStart = -1; nextBlink = now + 3000 + Math.random() * 2000; return 0; }
    return doubleBlink ? Math.abs(Math.sin(k * Math.PI * 2)) : Math.sin(k * Math.PI);
  }

  function applyArm(arm, sz, sx, ez, ex, ma, mx) {
    arm.shoulder.rotation.set(sx, 0, sz);
    arm.elbow.rotation.set(ex, 0, ez);
    arm.wrist.rotation.set(0, 0, 0);
    // aim the mallet in body space, whatever the shoulder and elbow are doing
    qa.setFromEuler(arm.shoulder.rotation).multiply(qb.setFromEuler(arm.elbow.rotation));
    dirV.set(-Math.sin(ma) * Math.cos(mx), Math.cos(ma) * Math.cos(mx), Math.sin(mx)).normalize();
    qc.setFromUnitVectors(UP, dirV);
    arm.mallet.quaternion.copy(qa.invert().multiply(qc));
  }
  const qa = new THREE.Quaternion(), qb = new THREE.Quaternion(), qc = new THREE.Quaternion();
  const dirV = new THREE.Vector3(), UP = new THREE.Vector3(0, 1, 0);

  // ---------- loop ----------
  const BASE_YAW = 0.5;     // three-quarter view, turned toward the chat
  let running = true, last = performance.now();
  const t0 = performance.now();

  function frame(now) {
    if (!running) return;
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    const tScale = reduceMotion ? 0.45 : 1;
    const t = (now - t0) / 1000 * tScale;

    // pose: cross-fade from the previous reaction
    const k = smooth(clamp((now - blendT0) / 1000 / BLEND, 0, 1));
    let P = k >= 1 ? POSES[state](t) : mixPose(POSES[prevState](t), POSES[state](t), k);
    if (reduceMotion) { P.y *= 0.3; P.squash = lerp(1, P.squash, 0.3); }

    // talking mouth for ~2.4 s after a reply
    if (now < speakUntil) {
      const talk = Math.abs(Math.sin(t * 13)) * (0.6 + 0.4 * Math.sin(t * 3.1));
      const fadeOut = clamp((speakUntil - now) / 250, 0, 1);
      P.mo = lerp(P.mo, 0.04 + 0.14 * talk, fadeOut);
      P.mw = lerp(P.mw, 0.22, fadeOut * 0.6);
    }
    // click strike: a big overhead hit with the right mallet
    const st = (now - strikeAt) / 380;
    if (st >= 0 && st < 1) {
      const env = Math.sin(Math.PI * st);
      P.R_sz += 0.5 * env; P.R_ez -= 0.6 * env; P.R_ma += 1.1 * env; P.squash -= 0.06 * env;
    }

    // gaze: pointer, the message box while typing, or a slow wander when nobody moves the mouse
    if (listening) aimAtBox();
    else if (now - lastPointer > 5000) { gazeTX = 0.25 * Math.sin(t * 0.37); gazeTY = 0.12 * Math.sin(t * 0.53); }
    const g = 1 - Math.exp(-dt * 6);
    gazeX += (gazeTX - gazeX) * g; gazeY += (gazeTY - gazeY) * g;

    // drag spring
    if (!dragging) {
      dragVel += (-38 * dragYaw - 8.5 * dragVel) * dt;
      dragYaw += dragVel * dt;
    }

    // rig
    char.position.y = GROUND + P.y - (1 - P.squash) * 0.25;
    char.rotation.set(P.lean - gazeY * 0.06, BASE_YAW + P.turn + gazeX * 0.28 + dragYaw, -P.tilt);
    const sq = P.squash;
    bodyBase.scale.set(1 + (1 - sq) * 0.55, sq, 1 + (1 - sq) * 0.55);
    legs.scale.y = Math.pow(sq, 1.6);
    bodyBase.position.y = LEG_TOP * legs.scale.y;

    eyes.forEach(e => {
      e.look.rotation.set(-gazeY * 0.32, gazeX * 0.45, 0);
      e.upper.rotation.x = lerp(-1.15, 1.62, clamp(Math.max(P.lid, blinkAmount(now)), 0, 1));
      e.lower.rotation.x = lerp(1.2, 0.3, clamp(P.low, 0, 1));
    });
    brows[0].g.position.y = brows[0].baseY + P.bL; brows[0].g.rotation.z = P.bLr;
    brows[1].g.position.y = brows[1].baseY + P.bR; brows[1].g.rotation.z = P.bRr;
    glasses.position.y = P.glass;
    setMouth(P.mw, P.mc, P.mo, P.ms);
    applyArm(armR, P.R_sz, P.R_sx, P.R_ez, P.R_ex, P.R_ma, P.R_mx);
    applyArm(armL, P.L_sz, P.L_sx, P.L_ez, P.L_ex, P.L_ma, P.L_mx);

    // contact shadow shrinks and fades as he leaves the ground
    const air = Math.max(0, P.y);
    shadow.scale.setScalar(1 - air * 0.7);
    shadowMat.opacity = (shadowMat.userData.base || 0.35) * (1 - air * 1.3);

    // theme light fade + lantern flicker
    if (lightTo) {
      const lt = clamp((now - lightT0) / 600, 0, 1);
      applyLights(lightFrom, lightTo, smooth(lt));
      if (lt >= 1) lightFrom = lightTo;
    }
    const flicker = 0.86 + 0.08 * Math.sin(now * 0.0073) + 0.05 * Math.sin(now * 0.0131 + 1) + 0.04 * Math.sin(now * 0.029);
    lamp.intensity = (lightNow.lampI || 0) * flicker;

    renderer.render(scene, camera);
  }

  // first frame, then swap the PNG for the canvas
  requestAnimationFrame(now => {
    last = now;
    frame(now);
    stage.classList.add('has-3d');
    window.Guru3D = api;
    window.dispatchEvent(new CustomEvent('guru3d:ready'));
  });

  canvas.addEventListener('webglcontextlost', e => {
    e.preventDefault();
    running = false;
    stage.classList.remove('has-3d');   // the PNG and its CSS animations take over again
    canvas.style.display = 'none';
  });

  const api = {
    get state() { return state; },
    setReaction(next, speaking) {
      const s = POSES[next] ? next : 'idle';
      if (s !== state) {
        // freeze the current blend as the new starting point
        prevState = state; state = s; blendT0 = performance.now();
      }
      if (speaking) speakUntil = performance.now() + 2400;
    },
    setTheme(next) { setTheme(next, false); },
    setListening(on) { listening = !!on; if (!on) lastPointer = performance.now(); },
    strike() { strikeAt = performance.now(); },
  };
}

(async function main() {
  if (!stage || !wrap || !wanted() || !webglAvailable()) return;
  let THREE;
  try {
    THREE = await loadThree();
  } catch (e) {
    console.info('[Guru3D] Three.js could not be loaded, keeping the 2D Guru Beleq.', e && e.message);
    return;
  }
  try {
    mount(THREE);
  } catch (e) {
    console.warn('[Guru3D] Could not build the 3D Guru Beleq, keeping the 2D one.', e);
    document.getElementById('guru3d-canvas')?.remove();
    stage.classList.remove('has-3d');
  }
})();
