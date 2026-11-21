/* Guru Beleq language switch: English (en) / Bahasa Malaysia (ms). Shared by every page, no dependencies.

   Pages register their words with GBLang.add({en: {...}, ms: {...}}) and mark static text with
     data-i18n="key"              -> textContent
     data-i18n-html="key"         -> innerHTML (only for the page's own trusted strings)
     data-i18n-placeholder="key", data-i18n-title="key", data-i18n-aria="key"
     data-lang-link               -> on <a>: keeps ?lang=ms on links to the other pages
   GBLang.toggle(el) adds the EN | BM switch; GBLang.onChange(fn) runs after every switch.
   The choice is remembered in localStorage (when the browser allows it) and can be forced with ?lang=ms. */
(function () {
  const KEY = 'guru-beleq-lang';
  const LANGS = ['en', 'ms'];
  const dict = { en: {}, ms: {} };
  const listeners = [];

  function initial() {
    try { const q = new URLSearchParams(location.search).get('lang'); if (LANGS.includes(q)) return q; } catch (e) {}
    try { const v = localStorage.getItem(KEY); if (LANGS.includes(v)) return v; } catch (e) {}
    return 'en';
  }
  let lang = initial();

  // The pages translate themselves, so stop the browser's own translator from turning the Malay back into
  // (machine) English: Chrome set to "always translate Malay" would otherwise make the BM switch look broken.
  document.documentElement.setAttribute('translate', 'no');
  if (!document.querySelector('meta[name="google"]')) {
    const m = document.createElement('meta');
    m.name = 'google';
    m.content = 'notranslate';
    document.head.appendChild(m);
  }

  function t(key, vars) {
    let s = key in dict[lang] ? dict[lang][key] : key in dict.en ? dict.en[key] : key;
    if (vars) s = String(s).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
    return s;
  }

  function apply(root) {
    root = root || document;
    document.documentElement.lang = lang;
    root.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll('[data-i18n-html]').forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
    [['data-i18n-placeholder', 'placeholder'], ['data-i18n-title', 'title'], ['data-i18n-aria', 'aria-label']].forEach(([attr, prop]) => {
      root.querySelectorAll('[' + attr + ']').forEach(el => el.setAttribute(prop, t(el.getAttribute(attr))));
    });
    root.querySelectorAll('a[data-lang-link]').forEach(a => {
      const path = a.getAttribute('href').split('?')[0];
      a.setAttribute('href', lang === 'en' ? path : path + '?lang=' + lang);
    });
    if ('page.title' in dict[lang]) document.title = t('page.title');
    document.querySelectorAll('.lang-toggle button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
  }

  function set(next) {
    if (!LANGS.includes(next) || next === lang) return;
    lang = next;
    try { localStorage.setItem(KEY, lang); } catch (e) {}
    try {
      const u = new URL(location.href);
      if (u.searchParams.has('lang')) { u.searchParams.set('lang', lang); history.replaceState(null, '', u); }
    } catch (e) {}
    apply();
    listeners.forEach(fn => { try { fn(lang); } catch (e) { console.error(e); } });
  }

  function injectStyle() {
    if (document.getElementById('lang-toggle-style')) return;
    const st = document.createElement('style');
    st.id = 'lang-toggle-style';
    st.textContent =
      '.lang-toggle{display:inline-flex;align-items:center;gap:2px;padding:3px;border-radius:999px;flex:none;' +
      'background:rgba(91,58,36,.82);border:1px solid rgba(255,255,255,.28);box-shadow:0 4px 14px rgba(43,29,18,.16)}' +
      '.lang-toggle button{border:0;background:transparent;color:#fff;font:700 .76rem/1 system-ui,-apple-system,"Segoe UI",sans-serif;' +
      'letter-spacing:.05em;padding:6px 10px;border-radius:999px;cursor:pointer;min-width:36px}' +
      '.lang-toggle button:hover{background:rgba(255,255,255,.16)}' +
      '.lang-toggle button[aria-pressed="true"]{background:#fff8ec;color:#3e2515}' +
      '.lang-toggle button:focus-visible{outline:2px solid #fff;outline-offset:1px}';
    document.head.appendChild(st);
  }

  function toggle(container) {
    injectStyle();
    const wrap = document.createElement('div');
    wrap.className = 'lang-toggle';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', 'Language / Bahasa');
    [['en', 'EN', 'English'], ['ms', 'BM', 'Bahasa Malaysia']].forEach(([code, short, full]) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.dataset.lang = code;
      b.lang = code;
      b.textContent = short;
      b.title = full;
      b.setAttribute('aria-label', full);
      b.setAttribute('aria-pressed', String(code === lang));
      b.addEventListener('click', () => set(code));
      wrap.appendChild(b);
    });
    container.appendChild(wrap);
    return wrap;
  }

  window.GBLang = {
    get lang() { return lang; },
    add(words) { LANGS.forEach(l => Object.assign(dict[l], (words && words[l]) || {})); },
    t, apply, set, toggle,
    onChange(fn) { listeners.push(fn); },
  };
})();
