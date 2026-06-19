(function () {
  const translations = window.growlyTranslations;

  // ---------- LANGUAGE ----------
  function applyLang(lang) {
    document.documentElement.lang = lang;
    const dict = translations[lang] || translations.en;

    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        if (key === 'faq.contact') {
          el.innerHTML = dict[key];
        } else {
          el.textContent = dict[key];
        }
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) el.setAttribute('placeholder', dict[key]);
    });

    document.querySelectorAll('.lang-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });

    localStorage.setItem('growly_lang', lang);
  }

  document.querySelectorAll('.lang-btn').forEach((btn) => {
    btn.addEventListener('click', () => applyLang(btn.getAttribute('data-lang')));
  });

  const stored = localStorage.getItem('growly_lang');
  const browserLang = (navigator.language || 'en').slice(0, 2);
  const initial = stored || (translations[browserLang] ? browserLang : 'en');
  applyLang(initial);

  // ---------- SWIPE CTA ----------
  const swipeCta = document.getElementById('swipeCta');
  const swipeEmailInput = document.getElementById('swipeEmailInput');

  if (swipeCta) {
    swipeCta.addEventListener('mouseenter', () => swipeCta.classList.add('glow'));
    swipeCta.addEventListener('mouseleave', () => {
      if (!swipeCta.classList.contains('expanded')) swipeCta.classList.remove('glow');
    });
    swipeCta.addEventListener('click', (e) => {
      if (!swipeCta.classList.contains('expanded')) {
        swipeCta.classList.add('expanded', 'glow');
        setTimeout(() => swipeEmailInput && swipeEmailInput.focus(), 400);
        return;
      }
      if (e.target.closest('.swipe-arrow-track')) {
        if (swipeEmailInput && swipeEmailInput.value.includes('@')) {
          document.getElementById('waitlist').scrollIntoView({ behavior: 'smooth' });
        } else if (swipeEmailInput) {
          swipeEmailInput.focus();
        }
      }
    });
    if (swipeEmailInput) {
      swipeEmailInput.addEventListener('click', (e) => e.stopPropagation());
      swipeEmailInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && swipeEmailInput.value.includes('@')) {
          document.getElementById('waitlist').scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  }

  // ---------- COUNTDOWN TIMER (7 days from first visit, persisted) ----------
  (function initCountdown() {
    const KEY = 'growly_waitlist_deadline';
    let deadline = localStorage.getItem(KEY);
    if (!deadline) {
      deadline = Date.now() + 7 * 24 * 60 * 60 * 1000;
      localStorage.setItem(KEY, deadline);
    } else {
      deadline = parseInt(deadline, 10);
    }

    const elD = document.getElementById('td');
    const elH = document.getElementById('th');
    const elM = document.getElementById('tm');
    const elS = document.getElementById('ts');
    if (!elD) return;

    function pad(n) { return String(n).padStart(2, '0'); }

    function tick() {
      const now = Date.now();
      let diff = deadline - now;
      if (diff < 0) diff = 0;
      const days = Math.floor(diff / (24 * 60 * 60 * 1000));
      const hours = Math.floor((diff % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
      const mins = Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000));
      const secs = Math.floor((diff % (60 * 1000)) / 1000);
      elD.textContent = pad(days);
      elH.textContent = pad(hours);
      elM.textContent = pad(mins);
      elS.textContent = pad(secs);
    }
    tick();
    setInterval(tick, 1000);
  })();

  // ---------- LOGO LOOP (real colored brand logos, no emoji) ----------
  const logos = [
    { name: 'Telegram', svg: '<svg viewBox="0 0 240 240" width="20" height="20"><circle cx="120" cy="120" r="120" fill="#229ED9"/><path fill="#fff" d="M98 172c-4 0-3.4-1.5-4.8-5.3L82 132l95-57z"/><path fill="#fff" d="M98 172c3 0 4.4-1.4 6.2-3.1l16.8-16.3-21-12.6z"/><path fill="#fff" d="M100 140l50.6 37.4c5.8 3.2 10 1.5 11.4-5.4l20.7-97.6c2-8.4-3.2-12.2-8.8-9.6L52.4 109.2c-8.2 3.3-8.1 7.9-1.5 9.9l30.8 9.6 71.4-45c3.4-2 6.5-1 4 1.2"/></svg>' },
    { name: 'Instagram', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><defs><radialGradient id="igrad" cx="0.3" cy="1.05" r="1.2"><stop offset="0%" stop-color="#FFDD55"/><stop offset="30%" stop-color="#FF543E"/><stop offset="60%" stop-color="#C837AB"/><stop offset="100%" stop-color="#5F1AE4"/></radialGradient></defs><rect x="4" y="4" width="40" height="40" rx="11" fill="url(#igrad)"/><rect x="13" y="13" width="22" height="22" rx="7" fill="none" stroke="#fff" stroke-width="2.6"/><circle cx="24" cy="24" r="6.2" fill="none" stroke="#fff" stroke-width="2.6"/><circle cx="33.2" cy="14.8" r="1.8" fill="#fff"/></svg>' },
    { name: 'LinkedIn', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><rect x="4" y="4" width="40" height="40" rx="5" fill="#0A66C2"/><circle cx="15.5" cy="16.5" r="2.6" fill="#fff"/><rect x="13" y="21" width="5" height="15" fill="#fff"/><path fill="#fff" d="M23 21h5v2.2c1.2-1.8 3-2.6 5.5-2.6 4.8 0 7 2.9 7 8.4V36h-5v-7c0-2.6-1-4.1-3.2-4.1-2.6 0-4.3 1.8-4.3 4.6V36h-5z"/></svg>' },
    { name: 'X', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><rect x="4" y="4" width="40" height="40" rx="9" fill="#000"/><path fill="#fff" d="M14 14l9.2 12.3L14.5 34h3.6l7.4-8.2 6.6 8.2H33L23.3 21l8.2-9h-3.6l-6.8 7.5-6 -7.5z"/></svg>' },
    { name: 'TikTok', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><rect x="4" y="4" width="40" height="40" rx="9" fill="#000"/><path fill="#25F4EE" d="M27 12h4.4c.3 3 2.2 5.4 5.6 5.7v4.5c-2.1 0-4-.6-5.6-1.7v8.6c0 4.7-3.8 8.4-8.5 8.4s-8.5-3.7-8.5-8.4 3.8-8.4 8.5-8.4c.4 0 .9 0 1.3.1v4.6c-.4-.1-.8-.2-1.3-.2-2.2 0-3.9 1.7-3.9 3.9s1.7 3.9 3.9 3.9 4.1-1.6 4.1-3.9z"/><path fill="#FE2C55" d="M27 11h4.4c.3 3 2.2 5.4 5.6 5.7v4.5c-2.1 0-4-.6-5.6-1.7v8.6c0 4.7-3.8 8.4-8.5 8.4s-8.5-3.7-8.5-8.4 3.8-8.4 8.5-8.4c.4 0 .9 0 1.3.1v4.6c-.4-.1-.8-.2-1.3-.2-2.2 0-3.9 1.7-3.9 3.9s1.7 3.9 3.9 3.9 4.1-1.6 4.1-3.9z" opacity="0.7"/></svg>' },
    { name: 'Notion', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><rect x="6" y="6" width="36" height="36" rx="4" fill="#fff" stroke="#000" stroke-width="1.5"/><path fill="#000" d="M15 14h4.5l9 13.5V14H32v20h-4.4l-9.1-13.6V34H15z"/></svg>' },
    { name: 'Google Sheets', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><path fill="#0F9D58" d="M28 4H12a3 3 0 00-3 3v34a3 3 0 003 3h24a3 3 0 003-3V15z"/><path fill="#87CEAC" d="M28 4v8a3 3 0 003 3h8z"/><rect x="14" y="22" width="20" height="14" fill="#fff"/><path stroke="#0F9D58" stroke-width="1.3" d="M14 27h20M14 31.5h20M21 22v14M27 22v14"/></svg>' },
    { name: 'Threads', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><rect x="4" y="4" width="40" height="40" rx="9" fill="#000"/><path fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" d="M24 11c-7 0-11.5 4.6-11.5 13s4.5 13 11.5 13c6.5 0 9.5-3.7 9.5-8.4 0-3.4-2.2-5.4-5.6-5.4-3 0-4.8 1.7-4.8 4 0 1.8 1.2 2.9 3 2.9 1 0 1.8-.3 2.5-.8"/></svg>' },
    { name: 'Google', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><path fill="#4285F4" d="M44 24.5c0-1.6-.1-2.8-.4-4H24v7.6h11.4c-.2 1.9-1.5 4.8-4.4 6.7l-.04.27 6.4 4.96.44.04C41.9 35.9 44 30.7 44 24.5z"/><path fill="#34A853" d="M24 44c5.9 0 10.9-1.9 14.5-5.3l-6.9-5.3c-1.9 1.3-4.5 2.3-7.6 2.3-5.8 0-10.7-3.9-12.5-9.2l-.25.02-6.65 5.16-.09.24C8 39.5 15.4 44 24 44z"/><path fill="#FBBC05" d="M11.5 26.5c-.5-1.4-.7-2.9-.7-4.5s.3-3.1.7-4.5l-.02-.3-6.74-5.24-.22.1A19.9 19.9 0 002 22c0 3.2.8 6.3 2.2 9l7.3-4.5z"/><path fill="#EA4335" d="M24 9.8c4.1 0 6.9 1.8 8.5 3.3l6.2-6C34.9 3.6 29.9 2 24 2 15.4 2 8 6.5 4.2 13l7.3 5.6C13.3 13.7 18.2 9.8 24 9.8z"/></svg>' },
  ];

  const loopInner = document.getElementById('logoLoopInner');
  if (loopInner) {
    const renderSet = () => logos.map(l => `<span class="logo-pill">${l.svg}${l.name}</span>`).join('');
    loopInner.innerHTML = renderSet() + renderSet();
  }

  // ---------- STACK TABS ----------
  const tabs = document.querySelectorAll('.stack-tab');
  const panels = document.querySelectorAll('.stack-panel');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');
      tabs.forEach((t) => t.classList.toggle('active', t === tab));
      panels.forEach((p) => p.classList.toggle('active', p.getAttribute('data-panel') === target));
    });
  });

  // ---------- FAQ ACCORDION ----------
  document.querySelectorAll('.faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-q');
    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach((i) => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // ---------- SCROLL FADE-UP ----------
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll('.fade-up').forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) el.classList.add('visible');
    observer.observe(el);
  });
})();
