(function () {
  const CONSENT_KEY = "medroute_cookie_consent_v1";
  const CONSENT_DURATION_DAYS = 180; // Expire after 6 months to ensure re-consent

  function getSavedConsent() {
    try {
      const record = JSON.parse(localStorage.getItem(CONSENT_KEY));
      if (!record) return null;

      const now = new Date().getTime();
      if (now > record.expiry) {
        localStorage.removeItem(CONSENT_KEY);
        return null;
      }
      return record.value; // 'all' or 'essential'
    } catch (e) {
      return null;
    }
  }

  function saveConsent(level) {
    const now = new Date().getTime();
    const expiry = now + (CONSENT_DURATION_DAYS * 24 * 60 * 60 * 1000);
    const record = { value: level, expiry: expiry };
    localStorage.setItem(CONSENT_KEY, JSON.stringify(record));
  }

  function activateGatedScripts() {
    const scripts = document.querySelectorAll('script[type="text/plain"][data-cookie-category="analytics"]');
    
    scripts.forEach((stalledScript) => {
      const activeScript = document.createElement("script");
      activeScript.type = "text/javascript";
      
      // Transfer external source if defined
      if (stalledScript.dataset.src) {
        activeScript.src = stalledScript.dataset.src;
      }
      
      // Transfer inline script content
      if (stalledScript.innerHTML) {
        activeScript.innerHTML = stalledScript.innerHTML;
      }

      // Preserve attributes for reference
      activeScript.setAttribute("data-activated", "true");

      // Append to the DOM to trigger download and execution
      document.head.appendChild(activeScript);
      stalledScript.remove();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const banner = document.getElementById("consent-banner-wrapper");
    const acceptBtn = document.getElementById("cookie-accept-btn");
    const rejectBtn = document.getElementById("cookie-reject-btn");
    
    const existingConsent = getSavedConsent();

    if (!existingConsent) {
      if (banner) banner.style.display = "block";
    } else if (existingConsent === "all") {
      activateGatedScripts();
    }

    if (acceptBtn) {
      acceptBtn.addEventListener("click", () => {
        saveConsent("all");
        if (banner) banner.style.display = "none";
        activateGatedScripts();
      });
    }

    if (rejectBtn) {
      rejectBtn.addEventListener("click", () => {
        saveConsent("essential");
        if (banner) banner.style.display = "none";
        // Do not activate gated scripts; strictly necessary Django session/CSRF cookies remain
      });
    }
  });

  // Global helper allowing users to re-open consent anytime from the footer
  window.reopenCookiePreferences = function () {
    const banner = document.getElementById("consent-banner-wrapper");
    if (banner) banner.style.display = "block";
  };
})();