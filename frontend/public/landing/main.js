(function () {
  const translations = window.growlyTranslations || {};
  const checkoutMessage = document.getElementById("checkoutMessage");
  let currentLang = "en";

  function t(key) {
    return translations[currentLang]?.[key] || translations.en?.[key] || key;
  }

  function applyLang(lang) {
    currentLang = translations[lang] ? lang : "en";
    document.documentElement.lang = currentLang;

    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.getAttribute("data-i18n");
      const value = key ? t(key) : "";
      if (value) element.textContent = value;
    });

    document.querySelectorAll(".lang-btn").forEach((button) => {
      button.classList.toggle(
        "active",
        button.getAttribute("data-lang") === currentLang,
      );
    });

    localStorage.setItem("growly_lang", currentLang);
  }

  document.querySelectorAll(".lang-btn").forEach((button) => {
    button.addEventListener("click", () => {
      applyLang(button.getAttribute("data-lang") || "en");
    });
  });

  const storedLang = localStorage.getItem("growly_lang");
  const browserLang = (navigator.language || "en").slice(0, 2);
  applyLang(storedLang || (translations[browserLang] ? browserLang : "en"));

  document.querySelectorAll(".capability-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-tab");
      document.querySelectorAll(".capability-tab").forEach((item) => {
        item.classList.toggle("active", item === tab);
      });
      document.querySelectorAll(".capability-panel").forEach((panel) => {
        panel.classList.toggle(
          "active",
          panel.getAttribute("data-panel") === target,
        );
      });
    });
  });

  function setCheckoutMessage(message) {
    if (checkoutMessage) checkoutMessage.textContent = message;
  }

  document.querySelectorAll("[data-checkout-plan]").forEach((button) => {
    button.addEventListener("click", async () => {
      const plan = button.getAttribute("data-checkout-plan");
      if (!plan) return;

      button.disabled = true;
      const originalText = button.textContent || "";
      button.textContent = t("checkout.loading");
      setCheckoutMessage("");

      try {
        const response = await fetch("/api/billing/checkout", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plan }),
        });
        const body = await response.json().catch(() => ({}));

        if (response.status === 401) {
          setCheckoutMessage(t("checkout.auth"));
          window.location.assign(`/register?plan=${encodeURIComponent(plan)}`);
          return;
        }

        if (!response.ok || !body.url) {
          setCheckoutMessage(body.detail || t("checkout.notConfigured"));
          return;
        }

        window.location.assign(body.url);
      } catch {
        setCheckoutMessage(t("checkout.error"));
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    });
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add("visible");
      });
    },
    { threshold: 0.12 },
  );

  document.querySelectorAll(".fade-up").forEach((element) => {
    const rect = element.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      element.classList.add("visible");
    }
    observer.observe(element);
  });
})();
