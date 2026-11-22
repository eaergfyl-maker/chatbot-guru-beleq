/* Guru Beleq time-of-day studio themes, shared by / and /chat. No dependencies.

   Three looks, set as data-theme on <html> and <body> (the colours live in /theme.css):
     morning    05:00-11:59  Tropical Emerald & Coastal Teal
     afternoon  12:00-17:59  Lombok Sunset Coral & Twilight Plum
     evening    18:00-04:59  Twilight Indigo & Lantern Gold (dark)
   "auto" follows the visitor's own clock and re-checks every minute. GBTheme.toggle(el) adds a pill that
   cycles Auto -> Morning -> Afternoon -> Evening. The choice is kept in localStorage (when the browser
   allows it); ?theme=evening forces a look for one visit without saving it. */
(function () {
  const KEY = 'guru-beleq-theme';
  const THEMES = ['morning', 'afternoon', 'evening'];
  const MODES = ['auto'].concat(THEMES);
  const ICON = { morning: '🌿', afternoon: '🌅', evening: '🏮' };
  const BAR = { morning: '#E0F2FE', afternoon: '#FDBA74', evening: '#0F172A' };  // browser UI colour on phones
  const WORDS = {
    en: {
      auto: 'Auto', morning: 'Morning', afternoon: 'Afternoon', evening: 'Evening',
      'name.morning': 'Tropical Emerald', 'name.afternoon': 'Lombok Sunset', 'name.evening': 'Lantern Night',
      label: 'Theme: {mode}. Click to change.', autoOf: 'Auto ({theme})',
    },
    ms: {
      auto: 'Auto', morning: 'Pagi', afternoon: 'Petang', evening: 'Malam',
      'name.morning': 'Zamrud Tropika', 'name.afternoon': 'Senja Lombok', 'name.evening': 'Malam Tanglung',
      label: 'Tema: {mode}. Klik untuk menukar.', autoOf: 'Auto ({theme})',
    },
  };
  const listeners = [];
  const buttons = [];

  function byClock(date) {
    const h = (date || new Date()).getHours();
    if (h >= 5 && h < 12) return 'morning';
    if (h >= 12 && h < 18) return 'afternoon';
    return 'evening';
  }

  function initialMode() {
    try { const q = new URLSearchParams(location.search).get('theme'); if (MODES.includes(q)) return q; } catch (e) {}
    try { const v = localStorage.getItem(KEY); if (MODES.includes(v)) return v; } catch (e) {}
    return 'auto';
  }

  let mode = initialMode();
  let theme = null;

  function lang() { return (window.GBLang && window.GBLang.lang === 'ms') ? 'ms' : 'en'; }
  function w(key, vars) {
    let s = WORDS[lang()][key] || WORDS.en[key] || key;
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
    return s;
  }

  function label(btn) {
    const name = mode === 'auto' ? w('autoOf', { theme: w(theme) }) : w(mode);
    btn.querySelector('.ico').textContent = ICON[theme];
    btn.querySelector('.lbl').textContent = mode === 'auto' ? w('auto') : w(mode);
    btn.setAttribute('aria-label', w('label', { mode: name }));
    btn.title = w('label', { mode: name }) + ' · ' + w('name.' + theme);
    btn.dataset.mode = mode;
  }

  function paint() {
    const next = mode === 'auto' ? byClock() : mode;
    const changed = next !== theme;
    theme = next;
    document.documentElement.dataset.theme = theme;
    if (document.body) document.body.dataset.theme = theme;
    let bar = document.querySelector('meta[name="theme-color"]');
    if (!bar && document.head) {
      bar = document.createElement('meta');
      bar.name = 'theme-color';
      document.head.appendChild(bar);
    }
    if (bar) bar.content = BAR[theme];
    buttons.forEach(label);
    if (changed) listeners.forEach(fn => { try { fn(theme, mode); } catch (e) { console.error(e); } });
  }

  function set(next) {
    if (!MODES.includes(next)) return;
    mode = next;
    try { localStorage.setItem(KEY, mode); } catch (e) {}
    paint();
    buttons.forEach(label);  // the label changes (Auto -> Morning) even when the colours do not
  }

  function cycle() { set(MODES[(MODES.indexOf(mode) + 1) % MODES.length]); }

  function toggle(container) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'theme-toggle';
    b.innerHTML = '<span class="ico" aria-hidden="true"></span><span class="lbl"></span>';
    b.addEventListener('click', cycle);
    buttons.push(b);
    label(b);
    container.appendChild(b);
    return b;
  }

  paint();  // runs in <head>, before the first paint, so there is no flash of the wrong colours
  if (!document.body) document.addEventListener('DOMContentLoaded', paint);
  const recheck = () => { if (mode === 'auto' && byClock() !== theme) paint(); };
  setInterval(recheck, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) recheck(); });
  if (window.GBLang) window.GBLang.onChange(() => buttons.forEach(label));

  window.GBTheme = {
    get mode() { return mode; },
    get theme() { return theme; },
    icon: t => ICON[t],
    name: t => w('name.' + t),
    word: t => w(t),
    byClock, set, cycle, toggle,
    onChange(fn) { listeners.push(fn); },
  };
})();
