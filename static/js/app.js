/* ============================================================
   BookBuddy front-end behaviour:
   1. Progressive cover-image fallback so a dead link never
      leaves a broken card.
   2. A searchable "card catalog" combobox bound to the full
      list of books available for recommendation.
   ============================================================ */

(function () {
  "use strict";

  /* ---------- 1. Cover image fallback ---------- */
  // Each <img class="cover-img"> carries data-orig (the dataset's
  // own image URL). We first try Open Library's cover API by ISBN
  // (usually more reliable/live), then fall back to the dataset's
  // own URL, then finally reveal a drawn placeholder so the card
  // layout never breaks.
  window.handleCoverError = function (img) {
    const stage = img.getAttribute("data-stage") || "olid";

    if (stage === "olid") {
      const orig = img.getAttribute("data-orig");
      if (orig) {
        img.setAttribute("data-stage", "orig");
        img.src = orig;
        return;
      }
    }

    // Every fallback exhausted: show the drawn placeholder.
    img.style.display = "none";
    const wrap = img.closest(".book-cover");
    if (wrap) {
      const fallback = wrap.querySelector(".cover-fallback");
      if (fallback) fallback.style.display = "flex";
    }
  };

  /* ---------- 2. Searchable combobox ---------- */
  function initCombobox(root) {
    const input = root.querySelector(".combobox-input");
    const panel = root.querySelector(".combobox-panel");
    const hidden = root.querySelector(".combobox-hidden");
    const submitBtn = root.querySelector(".combobox-submit");
    const sourceId = root.getAttribute("data-source");
    const sourceEl = sourceId ? document.getElementById(sourceId) : null;

    if (!input || !panel || !sourceEl) return;

    let books = [];
    try {
      books = JSON.parse(sourceEl.textContent);
    } catch (e) {
      books = [];
    }

    let activeIndex = -1;
    let currentMatches = [];

    function render(matches) {
      panel.innerHTML = "";
      currentMatches = matches;
      activeIndex = -1;

      if (matches.length === 0) {
        const empty = document.createElement("div");
        empty.className = "combobox-empty";
        empty.textContent = "No titles match — try a different spelling.";
        panel.appendChild(empty);
        panel.classList.add("open");
        return;
      }

      matches.slice(0, 60).forEach(function (title, i) {
        const opt = document.createElement("div");
        opt.className = "combobox-option";
        opt.setAttribute("role", "option");
        opt.dataset.title = title;

        const label = document.createElement("span");
        label.textContent = title;

        opt.appendChild(label);

        opt.addEventListener("mousedown", function (e) {
          e.preventDefault();
          selectTitle(title);
        });

        panel.appendChild(opt);
      });

      panel.classList.add("open");
    }

    function filterBooks(query) {
      const q = query.trim().toLowerCase();
      if (!q) return books.slice(0, 60);
      return books.filter(function (title) {
        return title.toLowerCase().indexOf(q) !== -1;
      });
    }

    function selectTitle(title) {
      input.value = title;
      if (hidden) hidden.value = title;
      if (submitBtn) submitBtn.disabled = false;
      closePanel();
    }

    function closePanel() {
      panel.classList.remove("open");
      activeIndex = -1;
    }

    function setActive(i) {
      const opts = panel.querySelectorAll(".combobox-option");
      opts.forEach(function (el) { el.classList.remove("active-option"); });
      if (i >= 0 && i < opts.length) {
        opts[i].classList.add("active-option");
        opts[i].scrollIntoView({ block: "nearest" });
        activeIndex = i;
      }
    }

    input.addEventListener("focus", function () {
      if (hidden) hidden.value = "";
      if (submitBtn) submitBtn.disabled = true;
      render(filterBooks(input.value));
    });

    input.addEventListener("input", function () {
      if (hidden) hidden.value = "";
      if (submitBtn) submitBtn.disabled = true;
      render(filterBooks(input.value));
    });

    input.addEventListener("keydown", function (e) {
      const opts = panel.querySelectorAll(".combobox-option");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!panel.classList.contains("open")) { render(filterBooks(input.value)); return; }
        setActive(Math.min(activeIndex + 1, opts.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(Math.max(activeIndex - 1, 0));
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && currentMatches[activeIndex]) {
          e.preventDefault();
          selectTitle(currentMatches[activeIndex]);
        }
      } else if (e.key === "Escape") {
        closePanel();
      }
    });

    document.addEventListener("click", function (e) {
      if (!root.contains(e.target)) closePanel();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-combobox]").forEach(initCombobox);

    // Mark active nav link
    const path = window.location.pathname;
    document.querySelectorAll(".nav-links a").forEach(function (a) {
      if (a.getAttribute("href") === path) a.classList.add("active");
    });
  });
})();
