(function () {
  const translations = window.growlyTranslations || {};
  const fallbackTranslations = {
    en: {
      'nav.login': 'Log in',
      'footer.login': 'Login',
      'footer.register': 'Create account',
      'checkout.loading': 'Opening checkout...',
      'checkout.auth': 'Redirecting to account creation...',
      'checkout.notConfigured': 'Payment is not configured yet.',
      'checkout.error': 'Could not open checkout. Try again later.',
    },
    ru: {
      'nav.login': 'Войти',
      'footer.login': 'Войти',
      'footer.register': 'Создать аккаунт',
      'checkout.loading': 'Открываем оплату...',
      'checkout.auth': 'Переходим к созданию аккаунта...',
      'checkout.notConfigured': 'Оплата пока не настроена.',
      'checkout.error': 'Не удалось открыть оплату. Попробуйте позже.',
    },
    kk: {
      'nav.login': 'Кіру',
      'footer.login': 'Кіру',
      'footer.register': 'Аккаунт жасау',
      'checkout.loading': 'Checkout ашылып жатыр...',
      'checkout.auth': 'Аккаунт жасауға өтіп жатырмыз...',
      'checkout.notConfigured': 'Төлем әлі бапталмаған.',
      'checkout.error': 'Checkout ашылмады. Кейінірек қайталап көріңіз.',
    },
  };
  let currentLang = 'en';

  function t(key) {
    return (
      translations[currentLang]?.[key] ||
      fallbackTranslations[currentLang]?.[key] ||
      translations.en?.[key] ||
      fallbackTranslations.en[key] ||
      key
    );
  }

  // ---------- LANGUAGE ----------
  function applyLang(lang) {
    currentLang = translations[lang] ? lang : 'en';
    document.documentElement.lang = currentLang;
    const dict = translations[currentLang] || translations.en || {};

    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const value = key ? (dict[key] || t(key)) : '';
      if (value) {
        if (key === 'faq.contact') {
          el.innerHTML = value;
        } else {
          el.textContent = value;
        }
      }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) el.setAttribute('placeholder', dict[key]);
    });

    document.querySelectorAll('.lang-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-lang') === currentLang);
    });

    localStorage.setItem('growly_lang', currentLang);
  }

  function switchLang(lang) {
    if (!lang || lang === currentLang) return;
    // Cross-fade the language change when the browser supports it.
    if (typeof document.startViewTransition === 'function') {
      document.startViewTransition(() => applyLang(lang));
    } else {
      applyLang(lang);
    }
  }

  document.querySelectorAll('.lang-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchLang(btn.getAttribute('data-lang')));
  });

  const stored = localStorage.getItem('growly_lang');
  const browserLang = (navigator.language || 'en').slice(0, 2);
  const initial = stored || (translations[browserLang] ? browserLang : 'en');
  applyLang(initial);

  // ---------- APP ROUTES + CHECKOUT ----------
  const checkoutMessage = document.getElementById('checkoutMessage');

  function setCheckoutMessage(message) {
    if (checkoutMessage) checkoutMessage.textContent = message;
  }

  function openRegister(plan) {
    const query = plan ? `?plan=${encodeURIComponent(plan)}` : '';
    window.location.assign(`/register${query}`);
  }

  document.querySelectorAll('[data-register-target]').forEach((element) => {
    element.addEventListener('click', (event) => {
      if (event.target.closest('input')) return;
      window.location.assign('/register');
    });
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openRegister();
      }
    });
  });

  document.querySelectorAll('[data-checkout-plan]').forEach((button) => {
    button.addEventListener('click', async () => {
      const plan = button.getAttribute('data-checkout-plan');
      if (!plan) return;

      button.disabled = true;
      const originalText = button.textContent || '';
      button.textContent = t('checkout.loading');
      setCheckoutMessage('');

      try {
        const response = await fetch('/api/billing/checkout', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan }),
        });
        const body = await response.json().catch(() => ({}));

        if (response.status === 401) {
          setCheckoutMessage(t('checkout.auth'));
          openRegister(plan);
          return;
        }

        if (!response.ok || !body.url) {
          setCheckoutMessage(body.detail || t('checkout.notConfigured'));
          return;
        }

        window.location.assign(body.url);
      } catch {
        setCheckoutMessage(t('checkout.error'));
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    });
  });

  // ---------- SWIPE CTA ----------
  const swipeCta = document.getElementById('swipeCta');

  if (swipeCta) {
    swipeCta.addEventListener('mouseenter', () => swipeCta.classList.add('glow'));
    swipeCta.addEventListener('mouseleave', () => {
      if (!swipeCta.classList.contains('expanded')) swipeCta.classList.remove('glow');
    });
    swipeCta.addEventListener('click', () => {
      openRegister();
    });
  }

  // ---------- LOGO LOOP (official brand marks, Simple Icons paths) ----------
  const logos = [
    { name: 'Telegram', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#26A5E4" d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>' },
    { name: 'Instagram', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><defs><radialGradient id="growly-ig-grad" cx="0.3" cy="1.05" r="1.25"><stop offset="0%" stop-color="#FFDD55"/><stop offset="30%" stop-color="#FF543E"/><stop offset="60%" stop-color="#C837AB"/><stop offset="100%" stop-color="#5F1AE4"/></radialGradient></defs><path fill="url(#growly-ig-grad)" d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"/></svg>' },
    { name: 'LinkedIn', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.225 0z"/></svg>' },
    { name: 'X', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#000" d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/></svg>' },
    { name: 'TikTok', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#000" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>' },
    { name: 'Notion', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#000" d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"/></svg>' },
    { name: 'Google Sheets', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#34A853" d="M11.318 12.545H7.91v-1.909h3.41v1.91zM14.728 0v6h6l-6-6zm1.363 10.636h-3.41v1.91h3.41v-1.91zm0 3.273h-3.41v1.91h3.41v-1.91zM20.727 6.5v15.864c0 .904-.732 1.636-1.636 1.636H4.909a1.636 1.636 0 0 1-1.636-1.636V1.636C3.273.732 4.005 0 4.909 0h9.318v6.5h6.5zm-3.273 2.773H6.545v7.909h10.91v-7.91zm-6.136 4.636H7.91v1.91h3.41v-1.91z"/></svg>' },
    { name: 'Threads', svg: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#000" d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 0 1 3.02.142c-.126-.742-.375-1.332-.75-1.757-.513-.586-1.308-.883-2.359-.89h-.029c-.844 0-1.992.232-2.721 1.32L7.734 7.847c.98-1.454 2.568-2.256 4.478-2.256h.044c3.194.02 5.097 1.975 5.287 5.388.108.046.216.094.321.142 1.49.7 2.58 1.761 3.154 3.07.797 1.82.871 4.79-1.548 7.158-1.85 1.81-4.094 2.628-7.277 2.65Zm1.003-11.69c-.242 0-.487.007-.739.021-1.836.103-2.98.946-2.916 2.143.067 1.256 1.452 1.839 2.784 1.767 1.224-.065 2.818-.543 3.086-3.71a10.5 10.5 0 0 0-2.215-.221z"/></svg>' },
    { name: 'Google', svg: '<svg viewBox="0 0 48 48" width="20" height="20"><path fill="#4285F4" d="M44 24.5c0-1.6-.1-2.8-.4-4H24v7.6h11.4c-.2 1.9-1.5 4.8-4.4 6.7l-.04.27 6.4 4.96.44.04C41.9 35.9 44 30.7 44 24.5z"/><path fill="#34A853" d="M24 44c5.9 0 10.9-1.9 14.5-5.3l-6.9-5.3c-1.9 1.3-4.5 2.3-7.6 2.3-5.8 0-10.7-3.9-12.5-9.2l-.25.02-6.65 5.16-.09.24C8 39.5 15.4 44 24 44z"/><path fill="#FBBC05" d="M11.5 26.5c-.5-1.4-.7-2.9-.7-4.5s.3-3.1.7-4.5l-.02-.3-6.74-5.24-.22.1A19.9 19.9 0 002 22c0 3.2.8 6.3 2.2 9l7.3-4.5z"/><path fill="#EA4335" d="M24 9.8c4.1 0 6.9 1.8 8.5 3.3l6.2-6C34.9 3.6 29.9 2 24 2 15.4 2 8 6.5 4.2 13l7.3 5.6C13.3 13.7 18.2 9.8 24 9.8z"/></svg>' },
  ];

  const loopInner = document.getElementById('logoLoopInner');
  if (loopInner) {
    const renderSet = () => logos.map(l => `<span class="logo-pill">${l.svg}${l.name}</span>`).join('');
    loopInner.innerHTML = renderSet() + renderSet();
  }

  // ---------- STACK TABS ----------
  const tabs = document.querySelectorAll('.stack-tab');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.classList.contains('active')) return;
      const target = tab.getAttribute('data-tab');
      tabs.forEach((t) => t.classList.toggle('active', t === tab));

      const currentPanel = document.querySelector('.stack-panel.active');
      const nextPanel = document.querySelector(`.stack-panel[data-panel="${target}"]`);
      if (currentPanel === nextPanel) return;

      if (currentPanel) currentPanel.classList.remove('active');
      if (nextPanel) {
        const staggerEl = nextPanel.querySelector('.stack-side');
        if (staggerEl) staggerEl.classList.remove('visible');
        // allow the browser to register display:none -> grid before animating opacity in
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            nextPanel.classList.add('active');
            if (staggerEl) staggerEl.classList.add('visible');
          });
        });
      }
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

  // ---------- SCROLL FADE-UP + STAGGER ----------
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll('.fade-up, .stagger-parent, .scale-in').forEach((el) => revealObserver.observe(el));

  // ---------- COUNT-UP NUMBERS ----------
  const countEls = document.querySelectorAll('[data-count]');
  if (countEls.length) {
    const countObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          countObserver.unobserve(el);
          const target = parseFloat(el.getAttribute('data-count'));
          const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
          const duration = 1100;
          const start = performance.now();
          function tick(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = target * eased;
            el.textContent = decimals > 0 ? current.toFixed(decimals) : Math.round(current).toString();
            if (progress < 1) {
              requestAnimationFrame(tick);
            } else {
              el.textContent = decimals > 0 ? target.toFixed(decimals) : target.toString();
            }
          }
          requestAnimationFrame(tick);
        });
      },
      { threshold: 0.4 }
    );
    countEls.forEach((el) => countObserver.observe(el));
  }

  // ---------- HERO DEVICE MOUSE TILT ----------
  const deviceTilt = document.getElementById('deviceTilt');
  if (deviceTilt && window.matchMedia('(hover: hover)').matches) {
    const heroRight = deviceTilt.closest('.hero-right');
    heroRight.addEventListener('mousemove', (e) => {
      const rect = deviceTilt.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5;
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      deviceTilt.style.setProperty('--ry', (px * 10).toFixed(2) + 'deg');
      deviceTilt.style.setProperty('--rx', (-py * 8).toFixed(2) + 'deg');
    });
    heroRight.addEventListener('mouseleave', () => {
      deviceTilt.style.setProperty('--ry', '0deg');
      deviceTilt.style.setProperty('--rx', '0deg');
    });
  }

  // ---------- GLOW-SPOT CURSOR TRACKING ----------
  document.querySelectorAll('.glow-spot').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--gx', x + '%');
      card.style.setProperty('--gy', y + '%');
    });
  });
})();
