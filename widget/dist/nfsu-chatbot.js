/*!
 * NFSU Library Chatbot Widget v1.0.0
 * Self-contained, zero-dependency, Shadow-DOM isolated.
 * Embed: <script src="nfsu-chatbot.js" data-api-base="https://chatbot.nfsu.ac.in"></script>
 */
(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Configuration
  // -------------------------------------------------------------------------

  var scriptEl = document.currentScript;
  var cfg = {
    apiBase: (scriptEl && scriptEl.getAttribute("data-api-base")) || window.NFSU_CHAT_CONFIG?.apiBase || "",
    opacBase: (scriptEl && scriptEl.getAttribute("data-opac-base")) || window.NFSU_CHAT_CONFIG?.opacBase || "https://catalog.nfsu.ac.in",
    locale: (scriptEl && scriptEl.getAttribute("data-locale")) || window.NFSU_CHAT_CONFIG?.locale || "en",
    theme: (scriptEl && scriptEl.getAttribute("data-theme")) || window.NFSU_CHAT_CONFIG?.theme || "system",
    themeStorageKey: "nfsu-library-chat-theme",
    enabled: true
  };

  // -------------------------------------------------------------------------
  // i18n strings (widget chrome)
  // -------------------------------------------------------------------------

  var STR = {
    en: {
      title: "Library Assistant",
      subtitle: "NFSU Library",
      close: "Close chat",
      minimize: "Minimize chat",
      open: "Open library chat",
      send: "Send",
      inputPlaceholder: "Ask about books, theses, or library services…",
      typing: "Assistant is typing",
      themeLight: "Switch to light mode",
      themeDark: "Switch to dark mode",
      langToggle: "हिंदी",
      fallbackLink: "Open KOHA advanced search",
      available: "Available on shelf",
      checkedOut: "Checked out",
      unknownAvail: "Availability at desk",
      openRecord: "Open KOHA record",
      openResults: "Open all results in KOHA",
      emptyTitle: "Start with a question",
      emptyBody: "Try a suggestion, or type anything — a title, an author, a subject like forensic toxicology.",
      unavailable: "The library assistant is temporarily unavailable. You can still search the KOHA catalogue directly.",
      retry: "Try again"
    },
    hi: {
      title: "पुस्तकालय सहायक",
      subtitle: "NFSU पुस्तकालय",
      close: "चैट बंद करें",
      minimize: "चैट छोटा करें",
      open: "पुस्तकालय चैट खोलें",
      send: "भेजें",
      inputPlaceholder: "पुस्तकों, शोध प्रबंधों या पुस्तकालय सेवाओं के बारे में पूछें…",
      typing: "सहायक लिख रहा है",
      themeLight: "लाइट मोड में बदलें",
      themeDark: "डार्क मोड में बदलें",
      langToggle: "English",
      fallbackLink: "KOHA उन्नत खोज खोलें",
      available: "शेल्फ पर उपलब्ध",
      checkedOut: "जारी किया गया",
      unknownAvail: "डेस्क पर उपलब्धता देखें",
      openRecord: "KOHA रिकॉर्ड खोलें",
      openResults: "सभी परिणाम KOHA में खोलें",
      emptyTitle: "एक प्रश्न से शुरू करें",
      emptyBody: "किसी सुझाव पर टैप करें, या कुछ भी लिखें — शीर्षक, लेखक, या विषय जैसे फोरेंसिक टॉक्सिकोलॉजी।",
      unavailable: "पुस्तकालय सहायक अस्थायी रूप से अनुपलब्ध है। आप KOHA कैटलॉग में सीधे खोज जारी रख सकते हैं।",
      retry: "पुनः प्रयास करें"
    }
  };

  function t(key) {
    var table = STR[cfg.locale] || STR.en;
    return table[key] || STR.en[key] || key;
  }

  // -------------------------------------------------------------------------
  // Small utilities
  // -------------------------------------------------------------------------

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "class") node.className = attrs[k];
        else if (k === "text") node.textContent = attrs[k];
        else if (k === "html") node.innerHTML = attrs[k];
        else if (k.indexOf("on") === 0 && typeof attrs[k] === "function") {
          node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        } else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) {
          node.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
        }
      });
    }
    (children || []).forEach(function (c) {
      if (c == null) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function svg(pathMarkup, size) {
    var s = size || 20;
    return (
      '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" ' +
      'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true" focusable="false">' + pathMarkup + "</svg>"
    );
  }

  var ICONS = {
    book: svg('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M9 7h7"/>'),
    send: svg('<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>', 18),
    close: svg('<path d="M18 6L6 18"/><path d="M6 6l12 12"/>', 18),
    minus: svg('<path d="M5 12h14"/>', 18),
    sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/><path d="M17.66 17.66l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M6.34 17.66l-1.41 1.41"/><path d="M19.07 4.93l-1.41 1.41"/>', 17),
    moon: svg('<path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/>', 17),
    arrow: svg('<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>', 15),
    search: svg('<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>', 15),
    globe: svg('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>', 16),
    scan: svg('<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>', 24)
  };

  // -------------------------------------------------------------------------
  // Theme
  // -------------------------------------------------------------------------

  function readStoredTheme() {
    try { return localStorage.getItem(cfg.themeStorageKey); } catch (e) { return null; }
  }

  function storeTheme(mode) {
    try { localStorage.setItem(cfg.themeStorageKey, mode); } catch (e) { /* private mode */ }
  }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  var currentTheme = "light";
  function resolveTheme() {
    if (cfg.theme === "light" || cfg.theme === "dark") return cfg.theme;
    var stored = readStoredTheme();
    if (stored === "light" || stored === "dark") return stored;
    return systemPrefersDark() ? "dark" : "light";
  }

  // -------------------------------------------------------------------------
  // Widget state
  // -------------------------------------------------------------------------

  var state = {
    open: false,
    minimized: false,
    loading: false,
    unread: 0,
    sessionId: null,
    history: [],
    serverConfig: null,
    locale: cfg.locale,
    lastFocus: null
  };

  var host = null;
  var shadow = null;
  var els = {};

  // -------------------------------------------------------------------------
  // Styles (injected into shadow root — immune to KOHA CSS)
  // -------------------------------------------------------------------------

  var CSS = [
    "@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');",

    ":host { all: initial; }",

    ".nfsu-scope {",
    "  --font-display: 'Space Grotesk', 'Segoe UI', system-ui, sans-serif;",
    "  --font-body: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;",
    "  --font-mono: 'IBM Plex Mono', 'Cascadia Mono', monospace;",
    "  --r-sm: 6px; --r-md: 10px; --r-lg: 14px; --r-xl: 18px;",
    "  --z: 2147483000;",
    "  font-family: var(--font-body);",
    "  font-size: 15px;",
    "  line-height: 1.5;",
    "  color: var(--ink);",
    "  -webkit-font-smoothing: antialiased;",
    "}",

    ".nfsu-scope[data-theme='light'] {",
    "  --bg: #F4F6F9;",
    "  --surface: #FFFFFF;",
    "  --surface-2: #F8FAFC;",
    "  --surface-3: #EEF2F7;",
    "  --ink: #0F172A;",
    "  --ink-2: #475569;",
    "  --ink-3: #64748B;",
    "  --accent: #991B1B;",
    "  --accent-hover: #7F1D1D;",
    "  --accent-ink: #FFFFFF;",
    "  --accent-soft: #FEF2F2;",
    "  --signal: #0E7490;",
    "  --signal-soft: #E0F2FE;",
    "  --warn: #B45309;",
    "  --warn-soft: #FEF3C7;",
    "  --line: #E2E8F0;",
    "  --line-strong: #CBD5E1;",
    "  --user-bubble: #0F172A;",
    "  --user-ink: #F8FAFC;",
    "  --shadow: 0 18px 50px -12px rgba(15, 23, 42, 0.28), 0 4px 14px -4px rgba(15, 23, 42, 0.12);",
    "  --shadow-sm: 0 2px 8px -2px rgba(15, 23, 42, 0.1);",
    "  --focus: #0E7490;",
    "}",

    ".nfsu-scope[data-theme='dark'] {",
    "  --bg: #0B0F19;",
    "  --surface: #141B2A;",
    "  --surface-2: #1A2333;",
    "  --surface-3: #1E293B;",
    "  --ink: #F1F5F9;",
    "  --ink-2: #CBD5E1;",
    "  --ink-3: #94A3B8;",
    "  --accent: #E11D48;",
    "  --accent-hover: #F43F5E;",
    "  --accent-ink: #FFFFFF;",
    "  --accent-soft: rgba(225, 29, 72, 0.12);",
    "  --signal: #22D3EE;",
    "  --signal-soft: rgba(34, 211, 238, 0.12);",
    "  --warn: #FBBF24;",
    "  --warn-soft: rgba(251, 191, 36, 0.12);",
    "  --line: #283247;",
    "  --line-strong: #334155;",
    "  --user-bubble: #E11D48;",
    "  --user-ink: #FFFFFF;",
    "  --shadow: 0 22px 60px -12px rgba(0, 0, 0, 0.65), 0 4px 16px -4px rgba(0, 0, 0, 0.4);",
    "  --shadow-sm: 0 2px 8px -2px rgba(0, 0, 0, 0.35);",
    "  --focus: #22D3EE;",
    "}",

    /* ---- Trigger ---- */
    ".trigger {",
    "  position: fixed;",
    "  right: 22px;",
    "  bottom: 22px;",
    "  width: 58px;",
    "  height: 58px;",
    "  border-radius: 50%;",
    "  border: none;",
    "  background: var(--accent);",
    "  color: var(--accent-ink);",
    "  cursor: pointer;",
    "  display: grid;",
    "  place-items: center;",
    "  box-shadow: var(--shadow);",
    "  z-index: var(--z);",
    "  transition: transform 0.2s ease, background 0.2s ease;",
    "  outline: none;",
    "}",
    ".trigger:hover { transform: translateY(-2px) scale(1.04); background: var(--accent-hover); }",
    ".trigger:focus-visible { box-shadow: 0 0 0 3px var(--surface), 0 0 0 6px var(--focus); }",
    ".trigger .pulse {",
    "  position: absolute;",
    "  inset: -6px;",
    "  border-radius: 50%;",
    "  border: 2px solid var(--accent);",
    "  opacity: 0;",
    "  animation: nfsu-pulse 2.8s cubic-bezier(0.22, 1, 0.36, 1) infinite;",
    "  pointer-events: none;",
    "}",
    "@keyframes nfsu-pulse {",
    "  0% { transform: scale(0.85); opacity: 0.55; }",
    "  70% { transform: scale(1.35); opacity: 0; }",
    "  100% { transform: scale(1.35); opacity: 0; }",
    "}",
    ".badge {",
    "  position: absolute;",
    "  top: -4px;",
    "  right: -4px;",
    "  min-width: 20px;",
    "  height: 20px;",
    "  padding: 0 5px;",
    "  border-radius: 10px;",
    "  background: var(--ink);",
    "  color: var(--surface);",
    "  font-family: var(--font-mono);",
    "  font-size: 11px;",
    "  font-weight: 500;",
    "  display: grid;",
    "  place-items: center;",
    "  border: 2px solid var(--surface);",
    "}",
    ".badge[hidden], .drawer[hidden] { display: none !important; }",

    /* ---- Drawer ---- */
    ".drawer {",
    "  position: fixed;",
    "  right: 22px;",
    "  bottom: 92px;",
    "  width: 380px;",
    "  height: min(600px, calc(100vh - 120px));",
    "  background: var(--bg);",
    "  border-radius: var(--r-xl);",
    "  box-shadow: var(--shadow);",
    "  border: 1px solid var(--line);",
    "  display: flex;",
    "  flex-direction: column;",
    "  overflow: hidden;",
    "  z-index: var(--z);",
    "  transform-origin: bottom right;",
    "  opacity: 0;",
    "  transform: translateY(12px) scale(0.96);",
    "  pointer-events: none;",
    "  transition: opacity 0.22s ease, transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);",
    "}",
    ".drawer.open { opacity: 1; transform: none; pointer-events: auto; }",

    /* ---- Header ---- */
    ".header {",
    "  display: flex;",
    "  align-items: center;",
    "  gap: 10px;",
    "  padding: 12px 12px 12px 14px;",
    "  background: var(--surface);",
    "  border-bottom: 1px solid var(--line);",
    "  flex-shrink: 0;",
    "}",
    ".mark {",
    "  width: 36px; height: 36px;",
    "  border-radius: 9px;",
    "  background: var(--accent);",
    "  color: var(--accent-ink);",
    "  display: grid; place-items: center;",
    "  flex-shrink: 0;",
    "}",
    ".headings { flex: 1; min-width: 0; }",
    ".title {",
    "  font-family: var(--font-display);",
    "  font-weight: 600;",
    "  font-size: 15px;",
    "  letter-spacing: -0.01em;",
    "  line-height: 1.2;",
    "  margin: 0;",
    "}",
    ".subtitle {",
    "  font-family: var(--font-mono);",
    "  font-size: 10.5px;",
    "  font-weight: 500;",
    "  letter-spacing: 0.09em;",
    "  text-transform: uppercase;",
    "  color: var(--ink-3);",
    "  margin: 2px 0 0;",
    "}",
    ".head-actions { display: flex; gap: 2px; }",
    ".icon-btn {",
    "  width: 32px; height: 32px;",
    "  border: none;",
    "  background: transparent;",
    "  color: var(--ink-2);",
    "  border-radius: var(--r-sm);",
    "  cursor: pointer;",
    "  display: grid; place-items: center;",
    "  transition: background 0.15s, color 0.15s;",
    "}",
    ".icon-btn:hover { background: var(--surface-3); color: var(--ink); }",
    ".icon-btn:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }",

    /* ---- Thread ---- */
    ".thread {",
    "  flex: 1;",
    "  overflow-y: auto;",
    "  padding: 16px 14px 8px;",
    "  display: flex;",
    "  flex-direction: column;",
    "  gap: 14px;",
    "  scroll-behavior: smooth;",
    "}",
    ".thread:focus-visible { outline: 2px solid var(--focus); outline-offset: -2px; }",

    ".row { display: flex; flex-direction: column; animation: nfsu-in 0.28s ease both; }",
    ".row.user { align-items: flex-end; }",
    ".row.bot { align-items: flex-start; }",
    "@keyframes nfsu-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }",

    ".bubble {",
    "  max-width: 88%;",
    "  padding: 10px 13px;",
    "  border-radius: var(--r-lg);",
    "  font-size: 14.5px;",
    "  line-height: 1.55;",
    "  white-space: pre-wrap;",
    "  word-break: break-word;",
    "}",
    ".row.bot .bubble {",
    "  background: var(--surface);",
    "  border: 1px solid var(--line);",
    "  border-bottom-left-radius: 4px;",
    "  color: var(--ink);",
    "}",
    ".row.user .bubble {",
    "  background: var(--user-bubble);",
    "  color: var(--user-ink);",
    "  border-bottom-right-radius: 4px;",
    "}",

    /* ---- Facet strip (signature: lab-readout metadata) ---- */
    ".facets {",
    "  display: flex;",
    "  flex-wrap: wrap;",
    "  gap: 5px;",
    "  margin-top: 7px;",
    "}",
    ".facet {",
    "  font-family: var(--font-mono);",
    "  font-size: 10px;",
    "  font-weight: 500;",
    "  letter-spacing: 0.06em;",
    "  text-transform: uppercase;",
    "  color: var(--ink-2);",
    "  background: var(--surface-3);",
    "  border: 1px solid var(--line);",
    "  border-radius: 4px;",
    "  padding: 2px 7px;",
    "}",

    /* ---- Bibliographic catalogue cards ---- */
    ".cards {",
    "  display: flex;",
    "  flex-direction: column;",
    "  gap: 8px;",
    "  margin-top: 9px;",
    "  width: 100%;",
    "  max-width: 100%;",
    "}",
    ".card {",
    "  background: var(--surface);",
    "  border: 1px solid var(--line);",
    "  border-radius: var(--r-md);",
    "  padding: 11px 12px 10px;",
    "  transition: border-color 0.15s, box-shadow 0.15s;",
    "}",
    ".card:hover { border-color: var(--line-strong); box-shadow: var(--shadow-sm); }",
    ".card-title {",
    "  font-family: var(--font-display);",
    "  font-weight: 600;",
    "  font-size: 14px;",
    "  line-height: 1.3;",
    "  letter-spacing: -0.01em;",
    "  color: var(--ink);",
    "  margin: 0 0 2px;",
    "}",
    ".card-author { font-size: 13px; color: var(--ink-2); margin: 0 0 8px; }",
    ".meta-strip {",
    "  display: flex;",
    "  flex-wrap: wrap;",
    "  align-items: center;",
    "  gap: 6px 10px;",
    "  padding-top: 8px;",
    "  border-top: 1px dashed var(--line);",
    "  font-family: var(--font-mono);",
    "  font-size: 10.5px;",
    "  font-weight: 500;",
    "  letter-spacing: 0.05em;",
    "  text-transform: uppercase;",
    "  color: var(--ink-3);",
    "}",
    ".avail {",
    "  display: inline-flex;",
    "  align-items: center;",
    "  gap: 5px;",
    "  padding: 2px 8px;",
    "  border-radius: 99px;",
    "  font-size: 10px;",
    "  letter-spacing: 0.05em;",
    "}",
    ".avail::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }",
    ".avail.ok { color: var(--signal); background: var(--signal-soft); }",
    ".avail.out { color: var(--warn); background: var(--warn-soft); }",
    ".avail.unk { color: var(--ink-3); background: var(--surface-3); }",
    ".card-link {",
    "  display: inline-flex;",
    "  align-items: center;",
    "  gap: 4px;",
    "  margin-top: 9px;",
    "  font-size: 12.5px;",
    "  font-weight: 600;",
    "  color: var(--accent);",
    "  text-decoration: none;",
    "  border-bottom: 1px solid transparent;",
    "  transition: border-color 0.15s;",
    "}",
    ".card-link:hover { border-bottom-color: currentColor; }",
    ".card-link:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 2px; }",
    ".shelf-line {",
    "  margin-top: 6px;",
    "  font-family: var(--font-mono);",
    "  font-size: 10.5px;",
    "  font-weight: 500;",
    "  letter-spacing: 0.04em;",
    "  color: var(--ink-3);",
    "  word-break: break-word;",
    "}",

    /* ---- Links row ---- */
    ".links { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }",
    ".inline-link {",
    "  font-size: 13px;",
    "  font-weight: 500;",
    "  color: var(--signal);",
    "  text-decoration: none;",
    "  display: inline-flex;",
    "  align-items: center;",
    "  gap: 4px;",
    "  width: fit-content;",
    "}",
    ".inline-link:hover { text-decoration: underline; }",
    ".inline-link:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 2px; }",

    /* ---- Search CTA ---- */
    ".cta-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }",
    ".cta {",
    "  display: inline-flex;",
    "  align-items: center;",
    "  gap: 5px;",
    "  padding: 7px 12px;",
    "  border-radius: var(--r-sm);",
    "  border: 1px solid var(--line-strong);",
    "  background: var(--surface);",
    "  color: var(--ink);",
    "  font-size: 12.5px;",
    "  font-weight: 600;",
    "  text-decoration: none;",
    "  cursor: pointer;",
    "  font-family: var(--font-body);",
    "  transition: background 0.15s, border-color 0.15s;",
    "}",
    ".cta:hover { background: var(--surface-3); }",
    ".cta:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }",
    ".cta.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }",
    ".cta.primary:hover { background: var(--accent-hover); }",

    /* ---- Typing ---- */
    ".typing { display: inline-flex; gap: 4px; padding: 12px 14px; }",
    ".typing i {",
    "  width: 6px; height: 6px; border-radius: 50%;",
    "  background: var(--ink-3);",
    "  animation: nfsu-blink 1.2s infinite;",
    "}",
    ".typing i:nth-child(2) { animation-delay: 0.15s; }",
    ".typing i:nth-child(3) { animation-delay: 0.3s; }",
    "@keyframes nfsu-blink { 0%, 80%, 100% { opacity: 0.25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-2px); } }",

    /* ---- Suggestions ---- */
    ".chips {",
    "  display: flex;",
    "  flex-wrap: wrap;",
    "  gap: 6px;",
    "  padding: 2px 0 4px;",
    "}",
    ".chip {",
    "  border: 1px solid var(--line-strong);",
    "  background: var(--surface);",
    "  color: var(--ink-2);",
    "  border-radius: 99px;",
    "  padding: 6px 12px;",
    "  font-size: 12.5px;",
    "  font-weight: 500;",
    "  cursor: pointer;",
    "  font-family: var(--font-body);",
    "  transition: border-color 0.15s, color 0.15s, background 0.15s;",
    "  text-align: left;",
    "}",
    ".chip:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }",
    ".chip:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }",

    /* ---- Composer ---- */
    ".composer {",
    "  display: flex;",
    "  align-items: flex-end;",
    "  gap: 8px;",
    "  padding: 10px 12px;",
    "  border-top: 1px solid var(--line);",
    "  background: var(--surface);",
    "  flex-shrink: 0;",
    "}",
    ".composer input {",
    "  flex: 1;",
    "  border: 1px solid var(--line-strong);",
    "  background: var(--surface-2);",
    "  color: var(--ink);",
    "  border-radius: var(--r-md);",
    "  padding: 10px 12px;",
    "  font-size: 14px;",
    "  font-family: var(--font-body);",
    "  outline: none;",
    "  min-width: 0;",
    "  transition: border-color 0.15s, box-shadow 0.15s;",
    "}",
    ".composer input::placeholder { color: var(--ink-3); }",
    ".composer input:focus { border-color: var(--focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--focus) 18%, transparent); }",
    ".send-btn {",
    "  width: 40px; height: 40px;",
    "  border: none;",
    "  border-radius: var(--r-md);",
    "  background: var(--accent);",
    "  color: var(--accent-ink);",
    "  cursor: pointer;",
    "  display: grid; place-items: center;",
    "  flex-shrink: 0;",
    "  transition: background 0.15s, opacity 0.15s;",
    "}",
    ".send-btn:hover:not(:disabled) { background: var(--accent-hover); }",
    ".send-btn:disabled { opacity: 0.45; cursor: not-allowed; }",
    ".send-btn:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }",

    /* ---- Footer ---- */
    ".footer {",
    "  padding: 6px 14px 9px;",
    "  background: var(--surface);",
    "  border-top: 1px solid var(--line);",
    "  flex-shrink: 0;",
    "  text-align: center;",
    "}",
    ".footer a {",
    "  font-size: 11.5px;",
    "  color: var(--ink-3);",
    "  text-decoration: none;",
    "  font-weight: 500;",
    "}",
    ".footer a:hover { color: var(--accent); text-decoration: underline; }",
    ".footer a:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 2px; }",

    /* ---- Empty ---- */
    ".empty-note {",
    "  text-align: center;",
    "  padding: 26px 18px 8px;",
    "  color: var(--ink-3);",
    "}",
    ".empty-note strong {",
    "  display: block;",
    "  font-family: var(--font-display);",
    "  font-size: 15px;",
    "  color: var(--ink-2);",
    "  margin-bottom: 4px;",
    "}",
    ".empty-note span { font-size: 13px; line-height: 1.5; }",

    /* ---- Screen-reader only ---- */
    ".sr-only {",
    "  position: absolute;",
    "  width: 1px; height: 1px;",
    "  padding: 0; margin: -1px;",
    "  overflow: hidden;",
    "  clip: rect(0 0 0 0);",
    "  white-space: nowrap;",
    "  border: 0;",
    "}",

    /* ---- Mobile ---- */
    "@media (max-width: 480px) {",
    "  .drawer {",
    "    right: 0; left: 0; bottom: 0;",
    "    width: 100%;",
    "    height: 100%;",
    "    max-height: 100%;",
    "    border-radius: 0;",
    "    border: none;",
    "  }",
    "  .trigger { right: 16px; bottom: 16px; }",
    "  .bubble { max-width: 92%; }",
    "}",

    "@media (prefers-reduced-motion: reduce) {",
    "  .drawer, .row, .trigger { transition: none !important; animation: none !important; }",
    "  .trigger .pulse { animation: none; opacity: 0; }",
    "  .typing i { animation: none; opacity: 0.6; }",
    "  .thread { scroll-behavior: auto; }",
    "}"
  ].join("\n");

  // -------------------------------------------------------------------------
  // DOM construction
  // -------------------------------------------------------------------------

  function buildDom() {
    host = document.createElement("div");
    host.setAttribute("data-nfsu-chatbot", "true");
    document.body.appendChild(host);
    shadow = host.attachShadow({ mode: "open" });

    var style = document.createElement("style");
    style.textContent = CSS;
    shadow.appendChild(style);

    var scope = el("div", { class: "nfsu-scope", "data-theme": currentTheme });
    shadow.appendChild(scope);
    els.scope = scope;

    // ---- Trigger ----
    var trigger = el("button", {
      class: "trigger",
      type: "button",
      "aria-label": t("open"),
      "aria-haspopup": "dialog",
      "aria-expanded": "false",
      html: '<span class="pulse" aria-hidden="true"></span>' + ICONS.scan
    });
    trigger.addEventListener("click", function () {
      if (state.open && !state.minimized) closeDrawer();
      else openDrawer();
    });
    els.trigger = trigger;
    els.badge = el("span", { class: "badge", hidden: true, "aria-hidden": "true" });
    trigger.appendChild(els.badge);
    scope.appendChild(trigger);

    // ---- Drawer ----
    var drawer = el("div", {
      class: "drawer",
      role: "dialog",
      "aria-modal": "true",
      "aria-label": t("title"),
      hidden: true
    });
    els.drawer = drawer;
    scope.appendChild(drawer);

    // Header
    var header = el("div", { class: "header" });
    header.appendChild(el("div", { class: "mark", "aria-hidden": "true", html: ICONS.book }));
    header.appendChild(
      el("div", { class: "headings" }, [
        el("h2", { class: "title", text: t("title") }),
        el("p", { class: "subtitle", text: t("subtitle") })
      ])
    );

    var headActions = el("div", { class: "head-actions" });

    var langBtn = el("button", {
      class: "icon-btn",
      type: "button",
      title: "Switch language",
      "aria-label": "Switch language",
      style: "width:auto;padding:0 8px;font-size:11.5px;font-weight:600;font-family:var(--font-body)",
      text: t("langToggle")
    });
    langBtn.addEventListener("click", function () {
      state.locale = state.locale === "en" ? "hi" : "en";
      cfg.locale = state.locale;
      langBtn.textContent = t("langToggle");
      els.input.placeholder = t("inputPlaceholder");
      els.trigger.setAttribute("aria-label", t("open"));
      els.drawer.setAttribute("aria-label", t("title"));
      els.titleNode.textContent = t("title");
      els.subtitleNode.textContent = t("subtitle");
      els.fallbackLink.textContent = t("fallbackLink");
      refreshSuggestions();
    });
    headActions.appendChild(langBtn);

    var themeBtn = el("button", {
      class: "icon-btn",
      type: "button",
      "aria-label": currentTheme === "dark" ? t("themeLight") : t("themeDark"),
      html: currentTheme === "dark" ? ICONS.sun : ICONS.moon
    });
    themeBtn.addEventListener("click", function () {
      currentTheme = currentTheme === "dark" ? "light" : "dark";
      storeTheme(currentTheme);
      applyTheme();
      themeBtn.innerHTML = currentTheme === "dark" ? ICONS.sun : ICONS.moon;
      themeBtn.setAttribute("aria-label", currentTheme === "dark" ? t("themeLight") : t("themeDark"));
    });
    els.themeBtn = themeBtn;
    headActions.appendChild(themeBtn);

    var minBtn = el("button", {
      class: "icon-btn", type: "button", "aria-label": t("minimize"), html: ICONS.minus
    });
    minBtn.addEventListener("click", minimizeDrawer);
    headActions.appendChild(minBtn);

    var closeBtn = el("button", {
      class: "icon-btn", type: "button", "aria-label": t("close"), html: ICONS.close
    });
    closeBtn.addEventListener("click", closeDrawer);
    headActions.appendChild(closeBtn);

    header.appendChild(headActions);
    drawer.appendChild(header);

    // keep references for lang switch
    els.titleNode = header.querySelector(".title");
    els.subtitleNode = header.querySelector(".subtitle");

    // Thread
    var thread = el("div", {
      class: "thread",
      role: "log",
      "aria-live": "polite",
      "aria-relevant": "additions text",
      tabindex: "0"
    });
    els.thread = thread;
    drawer.appendChild(thread);

    // Composer
    var composer = el("form", { class: "composer", autocomplete: "off" });
    var input = el("input", {
      type: "text",
      placeholder: t("inputPlaceholder"),
      "aria-label": t("inputPlaceholder"),
      maxlength: "2000",
      enterkeyhint: "send"
    });
    els.input = input;
    var sendBtn = el("button", {
      class: "send-btn", type: "submit", "aria-label": t("send"), html: ICONS.send
    });
    els.sendBtn = sendBtn;
    composer.appendChild(input);
    composer.appendChild(sendBtn);
    composer.addEventListener("submit", function (e) {
      e.preventDefault();
      sendMessage(input.value);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input.value);
      }
    });
    drawer.appendChild(composer);

    // Footer fallback link
    var footer = el("div", { class: "footer" });
    var fallbackLink = el("a", {
      href: cfg.opacBase + "/opac-search.pl",
      target: "_blank",
      rel: "noopener noreferrer",
      text: t("fallbackLink")
    });
    els.fallbackLink = fallbackLink;
    footer.appendChild(fallbackLink);
    drawer.appendChild(footer);

    // Focus trap
    drawer.addEventListener("keydown", onDrawerKeydown);
  }

  // -------------------------------------------------------------------------
  // Theme application
  // -------------------------------------------------------------------------

  function applyTheme() {
    if (els.scope) els.scope.setAttribute("data-theme", currentTheme);
  }

  // -------------------------------------------------------------------------
  // Open / close / minimize
  // -------------------------------------------------------------------------

  function openDrawer() {
    if (!cfg.enabled) return;
    state.lastFocus = document.activeElement;
    els.drawer.hidden = false;
    // force reflow so transition runs
    void els.drawer.offsetHeight;
    els.drawer.classList.add("open");
    state.open = true;
    state.minimized = false;
    state.unread = 0;
    updateBadge();
    els.trigger.setAttribute("aria-expanded", "true");
    els.trigger.setAttribute("aria-label", t("close"));

    if (!state.history.length) seedWelcome();

    window.setTimeout(function () {
      els.input.focus();
    }, 60);

    document.addEventListener("keydown", onGlobalKeydown);
  }

  function closeDrawer() {
    els.drawer.classList.remove("open");
    state.open = false;
    els.trigger.setAttribute("aria-expanded", "false");
    els.trigger.setAttribute("aria-label", t("open"));
    window.setTimeout(function () {
      if (!state.open) els.drawer.hidden = true;
    }, 220);
    document.removeEventListener("keydown", onGlobalKeydown);
    // Always return focus to the trigger (the shadow host itself is not focusable).
    els.trigger.focus();
  }

  function minimizeDrawer() {
    closeDrawer();
  }

  function onGlobalKeydown(e) {
    if (e.key === "Escape" && state.open) {
      e.stopPropagation();
      closeDrawer();
    }
  }

  function onDrawerKeydown(e) {
    if (e.key !== "Tab") return;
    var focusables = els.drawer.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    var list = Array.prototype.filter.call(focusables, function (n) {
      return !n.disabled && n.offsetParent !== null;
    });
    if (!list.length) return;
    var first = list[0];
    var last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function updateBadge() {
    if (state.unread > 0 && !state.open) {
      els.badge.hidden = false;
      els.badge.textContent = state.unread > 9 ? "9+" : String(state.unread);
      els.badge.removeAttribute("aria-hidden");
      els.trigger.setAttribute("aria-label", t("open") + ", " + state.unread + " unread messages");
    } else {
      els.badge.hidden = true;
      els.badge.textContent = "";
    }
  }

  // -------------------------------------------------------------------------
  // Message rendering
  // -------------------------------------------------------------------------

  function scrollThread() {
    els.thread.scrollTop = els.thread.scrollHeight;
  }

  function appendUserBubble(text) {
    var row = el("div", { class: "row user" });
    row.appendChild(el("div", { class: "bubble", text: text }));
    els.thread.appendChild(row);
    scrollThread();
  }

  function appendTyping() {
    var row = el("div", { class: "row bot", "data-typing": "true" });
    var bubble = el("div", { class: "bubble typing", "aria-label": t("typing") }, [
      el("i"), el("i"), el("i")
    ]);
    row.appendChild(bubble);
    els.thread.appendChild(row);
    scrollThread();
    return row;
  }

  function removeTyping() {
    var node = els.thread.querySelector('[data-typing="true"]');
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  function availabilityChip(record) {
    var status = record.availability || "unknown";
    var cls = "unk";
    var label = t("unknownAvail");
    if (status === "available") { cls = "ok"; label = t("available"); }
    else if (status === "checked_out" || status === "checkedout") { cls = "out"; label = t("checkedOut"); }
    return el("span", { class: "avail " + cls, text: label });
  }

  function appendBotResponse(payload) {
    removeTyping();
    var row = el("div", { class: "row bot" });
    var bubble = el("div", { class: "bubble" });

    // Text
    if (payload.message) {
      bubble.appendChild(document.createTextNode(payload.message));
    }

    // Facets — mono lab-readout strip
    var facets = payload.facets || {};
    var facetKeys = Object.keys(facets);
    if (facetKeys.length) {
      var facetWrap = el("div", { class: "facets", "aria-label": "Active search filters" });
      facetKeys.forEach(function (k) {
        facetWrap.appendChild(
          el("span", { class: "facet", text: k + ": " + facets[k] })
        );
      });
      bubble.appendChild(facetWrap);
    }

    // Bibliographic cards
    if (payload.cards && payload.cards.length) {
      var cards = el("div", { class: "cards" });
      payload.cards.forEach(function (record) {
        cards.appendChild(buildCard(record));
      });
      bubble.appendChild(cards);
    }

    // Links
    if (payload.links && payload.links.length) {
      var links = el("div", { class: "links" });
      payload.links.forEach(function (link) {
        if (!link.url) return;
        links.appendChild(
          el("a", {
            class: "inline-link",
            href: link.url,
            target: "_blank",
            rel: "noopener noreferrer",
            text: link.label || link.url
          })
        );
      });
      bubble.appendChild(links);
    }

    // CTAs
    var ctaRow = el("div", { class: "cta-row" });
    if (payload.search_url) {
      ctaRow.appendChild(
        el("a", {
          class: "cta primary",
          href: payload.search_url,
          target: "_blank",
          rel: "noopener noreferrer"
        }, [
          el("span", { html: ICONS.search }),
          document.createTextNode(t("openResults"))
        ])
      );
    }
    if (payload.advanced_search_url) {
      ctaRow.appendChild(
        el("a", {
          class: "cta",
          href: payload.advanced_search_url,
          target: "_blank",
          rel: "noopener noreferrer",
          text: t("fallbackLink")
        })
      );
    }
    if (ctaRow.childNodes.length) bubble.appendChild(ctaRow);

    row.appendChild(bubble);
    els.thread.appendChild(row);

    // Follow-up suggestion chips
    if (payload.suggestions && payload.suggestions.length) {
      els.thread.appendChild(buildChipRow(payload.suggestions));
    }

    scrollThread();
  }

  function buildCard(record) {
    var card = el("article", { class: "card" });
    card.appendChild(el("h3", { class: "card-title", text: record.title || "Untitled" }));
    if (record.author) {
      card.appendChild(el("p", { class: "card-author", text: record.author }));
    }

    var strip = el("div", { class: "meta-strip" });
    strip.appendChild(availabilityChip(record));
    var bits = [];
    if (record.year) bits.push(record.year);
    if (record.publisher) bits.push(record.publisher);
    if (record.isbn) bits.push("ISBN " + record.isbn);
    if (record.edition) bits.push(record.edition);
    if (bits.length) {
      strip.appendChild(el("span", { text: bits.join(" · ") }));
    }
    card.appendChild(strip);

    // Call number + branch — the details a user needs to find the book on the shelf
    var shelf = [];
    if (record.call_number) shelf.push(record.call_number);
    if (record.branch) shelf.push(record.branch);
    if (record.material_type && !record.call_number && !record.branch) {
      shelf.push(record.material_type);
    }
    if (shelf.length) {
      card.appendChild(
        el("div", { class: "shelf-line", text: shelf.join("  ·  ") })
      );
    }

    if (record.url) {
      card.appendChild(
        el("a", {
          class: "card-link",
          href: record.url,
          target: "_blank",
          rel: "noopener noreferrer"
        }, [
          el("span", { html: ICONS.arrow }),
          document.createTextNode(t("openRecord"))
        ])
      );
    }
    return card;
  }

  function buildChipRow(suggestions) {
    var wrap = el("div", { class: "row bot" });
    var chips = el("div", { class: "chips" });
    suggestions.forEach(function (s) {
      chips.appendChild(
        el("button", {
          class: "chip",
          type: "button",
          text: s,
          onclick: function () { sendMessage(s); }
        })
      );
    });
    wrap.appendChild(chips);
    return wrap;
  }

  function refreshSuggestions() {
    var existing = els.thread.querySelectorAll(".chips");
    // Chips live inside .row.bot containers; replace the last chip-only rows
    var rows = els.thread.querySelectorAll(".row.bot");
    rows.forEach(function (row) {
      var chips = row.querySelector(".chips");
      if (chips && row.childNodes.length === 1 && row.firstChild === chips) {
        row.parentNode.removeChild(row);
      }
    });
    var list = (state.serverConfig && state.serverConfig.suggestions) || [];
    if (list.length) els.thread.appendChild(buildChipRow(list.slice(0, 6)));
  }

  // -------------------------------------------------------------------------
  // Welcome / empty state
  // -------------------------------------------------------------------------

  function seedWelcome() {
    var cfgWelcome = state.serverConfig && state.serverConfig.welcome;
    var welcome = cfgWelcome || (state.locale === "hi"
      ? "नमस्ते! मैं NFSU पुस्तकालय सहायक हूँ। किताबें, पत्रिकाएँ, शोध प्रबंध या पुस्तकालय सेवाओं के बारे में पूछें।"
      : "Hello! I am the NFSU Library assistant. Ask me for books, journals, theses, or library services.");

    var row = el("div", { class: "row bot" });
    row.appendChild(el("div", { class: "bubble", text: welcome }));
    els.thread.appendChild(row);

    var list = (state.serverConfig && state.serverConfig.suggestions) || [
      "Find forensic DNA books",
      "Show books on cybercrime investigation",
      "Library timing & rules",
      "Renew my book",
      "How do I access ONOS off campus?"
    ];
    els.thread.appendChild(buildChipRow(list.slice(0, 6)));
    scrollThread();
  }

  function showUnavailable() {
    var row = el("div", { class: "row bot" });
    var bubble = el("div", { class: "bubble" });
    bubble.appendChild(document.createTextNode(t("unavailable")));
    var cta = el("div", { class: "cta-row" });
    cta.appendChild(
      el("a", {
        class: "cta primary",
        href: cfg.opacBase + "/opac-search.pl",
        target: "_blank",
        rel: "noopener noreferrer"
      }, [el("span", { html: ICONS.search }), document.createTextNode(t("fallbackLink"))])
    );
    bubble.appendChild(cta);
    row.appendChild(bubble);
    els.thread.appendChild(row);
    scrollThread();
  }

  // -------------------------------------------------------------------------
  // Chat transport
  // -------------------------------------------------------------------------

  function sendMessage(text) {
    var message = (text || "").trim();
    if (!message || state.loading) return;

    els.input.value = "";
    appendUserBubble(message);
    state.history.push({ role: "user", content: message });
    if (state.history.length > 12) state.history = state.history.slice(-12);

    state.loading = true;
    els.sendBtn.disabled = true;
    var typingRow = appendTyping();

    var controller = new AbortController();
    var timer = window.setTimeout(function () { controller.abort(); }, 30000);

    fetch(cfg.apiBase + "/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Requested-With": "NFSU-Chatbot" },
      body: JSON.stringify({
        message: message,
        session_id: state.sessionId,
        locale: state.locale,
        history: state.history.slice(0, -1)
      }),
      signal: controller.signal
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        window.clearTimeout(timer);
        if (result.status === 429) {
          removeTyping();
          appendBotResponse({
            message: result.data.message || t("retry"),
            kind: "error"
          });
          return;
        }
        if (!result.ok) throw new Error("http_" + result.status);

        var data = result.data;
        state.sessionId = data.session_id || state.sessionId;
        if (data.message) {
          state.history.push({ role: "assistant", content: data.message });
        }
        if (!state.open) state.unread += 1;
        updateBadge();
        appendBotResponse(data);
      })
      .catch(function () {
        window.clearTimeout(timer);
        removeTyping();
        appendBotResponse({
          message: state.locale === "hi"
            ? "मुझे उत्तर देने में समस्या हो रही है। कृपया पुनः प्रयास करें, या KOHA खोज सीधे खोलें।"
            : "I could not reach the library service just now. Please try again, or open KOHA search directly.",
          kind: "error",
          advanced_search_url: cfg.opacBase + "/cgi-bin/koha/opac-search.pl"
        });
      })
      .then(function () {
        state.loading = false;
        els.sendBtn.disabled = false;
        els.input.focus();
      });
  }

  // -------------------------------------------------------------------------
  // Config fetch (enable / disable / suspend)
  // -------------------------------------------------------------------------

  function loadConfig() {
    if (!cfg.apiBase) {
      // Offline demo mode — widget still renders with defaults.
      state.serverConfig = null;
      return Promise.resolve();
    }
    return fetch(cfg.apiBase + "/api/v1/config?locale=" + encodeURIComponent(state.locale), {
      headers: { "X-Requested-With": "NFSU-Chatbot" }
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        state.serverConfig = data;
        if (data && data.enabled === false) {
          cfg.enabled = false;
          if (els.trigger) els.trigger.remove();
          if (els.drawer) els.drawer.remove();
        }
        if (data && data.supported_locales && data.supported_locales.indexOf(state.locale) === -1) {
          state.locale = data.default_locale || "en";
          cfg.locale = state.locale;
        }
      })
      .catch(function () {
        // Backend down: keep widget usable with local defaults (graceful).
        state.serverConfig = null;
      });
  }

  // -------------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------------

  function boot() {
    if (window.__NFSU_CHATBOOTED__) return;
    window.__NFSU_CHATBOOTED__ = true;

    currentTheme = resolveTheme();
    state.locale = cfg.locale;

    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onChange = function () {
        if (!readStoredTheme() && cfg.theme === "system") {
          currentTheme = mq.matches ? "dark" : "light";
          applyTheme();
          if (els.themeBtn) {
            els.themeBtn.innerHTML = currentTheme === "dark" ? ICONS.sun : ICONS.moon;
          }
        }
      };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }

    buildDom();
    applyTheme();
    loadConfig();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
