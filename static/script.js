// Theme toggle script: syncs checkbox(es), toggles classes on <html> and <body>, and persists selection.

(function () {
  const storageKey = 'dailyMoodTheme'; // 'dark' or 'light'
  const htmlEl = document.documentElement;
  const bodyEl = document.body;

  function applyTheme(theme, persist = false) {
    if (theme === 'dark') {
      htmlEl.classList.add('dark');
      bodyEl.classList.remove('light-mode');
      bodyEl.classList.add('dark-mode');
    } else {
      htmlEl.classList.remove('dark');
      bodyEl.classList.remove('dark-mode');
      bodyEl.classList.add('light-mode');
    }
    if (persist) {
      try { localStorage.setItem(storageKey, theme); } catch (e) { /* ignore */ }
    }
  }

  // Determine initial theme: saved -> system -> default light
  let saved = null;
  try { saved = localStorage.getItem(storageKey); } catch (e) { saved = null; }

  const initialTheme = saved || ((window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light');

  // Apply initial theme immediately (already set on <html> early too, but reapply to ensure body classes)
  applyTheme(initialTheme, false);

  // Find toggles (input elements with id="toggle") and sync + attach listeners
  let toggles = Array.from(document.querySelectorAll('input[id="toggle"]'));

  function attachToggleHandlers() {
    toggles = Array.from(document.querySelectorAll('input[id="toggle"]'));
    toggles.forEach(function (toggle) {
      // ensure checkbox state matches applied theme
      toggle.checked = htmlEl.classList.contains('dark');

      // change event (covers direct checkbox changes)
      toggle.addEventListener('change', function () {
        const newTheme = toggle.checked ? 'dark' : 'light';
        applyTheme(newTheme, true);
        // sync any other toggles on the page
        toggles.forEach(function (other) { if (other !== toggle) other.checked = toggle.checked; });
      });

      // If the checkbox is inside a label (our case), clicks on the SVG or label may not toggle depending on overlay.
      // Also add a click handler on the label to ensure theme toggles when the user clicks the visual control.
  // support header label id, floating label id, and center label id
  const label = toggle.closest('#theme-toggle-button') || toggle.closest('#theme-toggle-float') || toggle.closest('#theme-toggle-center');
      if (label) {
        label.addEventListener('click', function (e) {
          // ignore clicks on actual checkbox to avoid double toggling
          if (e.target === toggle) return;
          // toggle the checkbox state
          const newChecked = !toggle.checked;
          toggle.checked = newChecked;
          const newTheme = newChecked ? 'dark' : 'light';
          applyTheme(newTheme, true);
          toggles.forEach(function (other) { if (other !== toggle) other.checked = newChecked; });
        });

        // keyboard accessibility: toggle on Enter/Space when label focused
        label.tabIndex = label.tabIndex >= 0 ? label.tabIndex : 0;
        label.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            const newChecked = !toggle.checked;
            toggle.checked = newChecked;
            const newTheme = newChecked ? 'dark' : 'light';
            applyTheme(newTheme, true);
            toggles.forEach(function (other) { if (other !== toggle) other.checked = newChecked; });
          }
        });
      }
    });
  }

  attachToggleHandlers();

  // In case JS runs before toggles are in DOM (rare), set a small observer fallback:
  if (toggles.length === 0) {
    // when a toggle is added later, this will handle it once
    const observer = new MutationObserver(function () {
      const found = Array.from(document.querySelectorAll('input[id="toggle"]'));
      if (found.length > 0) {
        observer.disconnect();
        attachToggleHandlers();
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();