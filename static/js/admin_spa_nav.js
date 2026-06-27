/**
 * FlexyRide Admin SPA Navigation
 * 
 * Intercepts sidebar link clicks and loads only the main content area
 * via fetch(), preventing the sidebar from reloading on every navigation.
 */
(function () {
  "use strict";

  const ADMIN_PREFIX = "/headquarters/";
  const MAIN_SELECTOR = "#main";
  const SIDEBAR_SELECTOR = "#nav-sidebar";
  const PAGE_SELECTOR = "#page";

  // Only activate on admin pages
  if (!window.location.pathname.startsWith(ADMIN_PREFIX)) return;

  /**
   * Check if a URL is an admin page we can SPA-navigate to.
   */
  function isAdminUrl(url) {
    try {
      const u = new URL(url, window.location.origin);
      return (
        u.origin === window.location.origin &&
        u.pathname.startsWith(ADMIN_PREFIX)
      );
    } catch {
      return false;
    }
  }

  /**
   * Update the active/highlighted state on sidebar links.
   */
  function updateSidebarActive(pathname) {
    const sidebar = document.querySelector(SIDEBAR_SELECTOR);
    if (!sidebar) return;

    // Remove all existing active indicators
    sidebar.querySelectorAll("a").forEach((a) => {
      // Unfold uses bg-primary-* classes for active state
      a.classList.remove(
        "bg-primary-50",
        "dark:bg-base-800",
        "font-semibold"
      );
    });

    // Find and highlight the matching link
    sidebar.querySelectorAll("a[href]").forEach((a) => {
      try {
        const linkPath = new URL(a.href, window.location.origin).pathname;
        if (linkPath === pathname) {
          a.classList.add(
            "bg-primary-50",
            "dark:bg-base-800",
            "font-semibold"
          );
        }
      } catch {
        // skip malformed URLs
      }
    });
  }

  /**
   * Load a page via fetch and swap only the #main content.
   */
  async function navigateTo(url, pushState = true) {
    const mainEl = document.querySelector(MAIN_SELECTOR);
    if (!mainEl) {
      // Fallback: can't find main container, do a full navigation
      window.location.href = url;
      return;
    }

    // Show a subtle loading indicator
    mainEl.style.opacity = "0.5";
    mainEl.style.transition = "opacity 0.15s ease";
    mainEl.style.pointerEvents = "none";

    try {
      const response = await fetch(url, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      });

      if (!response.ok) {
        // Non-200 response — fall back to full page load
        window.location.href = url;
        return;
      }

      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      const newMain = doc.querySelector(MAIN_SELECTOR);
      if (!newMain) {
        // The fetched page doesn't have a #main (login page, popup, etc.)
        window.location.href = url;
        return;
      }

      // Swap the main content
      mainEl.innerHTML = newMain.innerHTML;
      // Copy over any class changes (Unfold sometimes modifies #main classes)
      mainEl.className = newMain.className;

      // Update document title
      const newTitle = doc.querySelector("title");
      if (newTitle) {
        document.title = newTitle.textContent;
      }

      // Push to browser history
      if (pushState) {
        history.pushState({ spaNav: true }, "", url);
      }

      // Update sidebar active state
      const pathname = new URL(url, window.location.origin).pathname;
      updateSidebarActive(pathname);

      // Re-initialize Alpine.js components in the new content
      reinitializeScripts(mainEl, doc);

      // Scroll to top of content
      mainEl.scrollTop = 0;
      window.scrollTo(0, 0);
    } catch (err) {
      console.warn("[SPA Nav] Fetch failed, falling back:", err);
      window.location.href = url;
    } finally {
      mainEl.style.opacity = "";
      mainEl.style.transition = "";
      mainEl.style.pointerEvents = "";
    }
  }

  /**
   * Re-initialize dynamic components after content swap.
   */
  function reinitializeScripts(mainEl, doc) {
    // Re-run inline scripts in the new content
    mainEl.querySelectorAll("script").forEach((oldScript) => {
      const newScript = document.createElement("script");
      if (oldScript.src) {
        newScript.src = oldScript.src;
      } else {
        newScript.textContent = oldScript.textContent;
      }
      // Copy attributes
      Array.from(oldScript.attributes).forEach((attr) => {
        if (attr.name !== "src") {
          newScript.setAttribute(attr.name, attr.value);
        }
      });
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });

    // Re-initialize Alpine.js on the swapped content
    if (window.Alpine) {
      // Alpine.js needs to discover new x-data elements
      try {
        window.Alpine.initTree(mainEl);
      } catch {
        // Older Alpine versions may not have initTree
      }
    }

    // Re-initialize simplebar if present
    if (window.SimpleBar) {
      mainEl
        .querySelectorAll("[data-simplebar]")
        .forEach((el) => new SimpleBar(el));
    }
  }

  /**
   * Attach click interceptors to the sidebar.
   */
  function attachSidebarListeners() {
    const sidebar = document.querySelector(SIDEBAR_SELECTOR);
    if (!sidebar) return;

    sidebar.addEventListener("click", function (e) {
      // Find the closest <a> tag
      const link = e.target.closest("a[href]");
      if (!link) return;

      const href = link.href;

      // Skip non-admin links, new-tab clicks, or modifier keys
      if (
        !isAdminUrl(href) ||
        link.target === "_blank" ||
        e.ctrlKey ||
        e.metaKey ||
        e.shiftKey
      ) {
        return;
      }

      // Skip if it's the current page
      if (
        new URL(href, window.location.origin).pathname ===
        window.location.pathname
      ) {
        e.preventDefault();
        return;
      }

      e.preventDefault();
      navigateTo(href);
    });
  }

  /**
   * Handle browser back/forward buttons.
   */
  window.addEventListener("popstate", function (e) {
    if (window.location.pathname.startsWith(ADMIN_PREFIX)) {
      navigateTo(window.location.href, false);
    }
  });

  /**
   * Initialize on DOM ready.
   */
  function init() {
    attachSidebarListeners();
    updateSidebarActive(window.location.pathname);

    // Replace the current history entry so popstate works on first nav
    history.replaceState({ spaNav: true }, "", window.location.href);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
