(() => {
  "use strict";
  const CART_KEY = "cravecorner_cart_v1";
  const money = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const getCart = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter((row) => Number.isInteger(Number(row.id)) && Number(row.quantity) > 0) : [];
    } catch (_) { return []; }
  };
  const saveCart = (cart) => {
    const valid = cart.filter((row) => Number(row.quantity) > 0).map((row) => ({ id: Number(row.id), quantity: Math.min(50, Math.max(1, Number(row.quantity))) }));
    localStorage.setItem(CART_KEY, JSON.stringify(valid));
    updateCartBadge();
    window.dispatchEvent(new CustomEvent("cravecorner:cart", { detail: valid }));
    return valid;
  };
  const updateCartBadge = () => {
    const count = getCart().reduce((sum, row) => sum + row.quantity, 0);
    document.querySelectorAll("[data-cart-count]").forEach((el) => {
      if (el.textContent !== String(count)) {
        el.textContent = String(count);
        el.classList.remove("cart-pop");
        requestAnimationFrame(() => el.classList.add("cart-pop"));
      }
    });
  };
  let revealObserver;
  function reveal(root = document) {
    const nodes = [];
    if (root.matches?.(".reveal")) nodes.push(root);
    nodes.push(...(root.querySelectorAll?.(".reveal") || []));
    if (!nodes.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12 });
    }
    nodes.forEach((node) => revealObserver.observe(node));
  }
  function initCursorGlow() {
    if (!window.matchMedia("(pointer: fine)").matches || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const glow = document.createElement("div");
    glow.className = "cursor-glow";
    glow.setAttribute("aria-hidden", "true");
    document.body.append(glow);
    let frame = 0;
    window.addEventListener("pointermove", (event) => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        glow.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0) translate(-50%, -50%)`;
        frame = 0;
      });
    }, { passive: true });
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "include", ...options, headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) } });
    let payload = null;
    const text = await response.text();
    if (text) { try { payload = JSON.parse(text); } catch (_) { payload = { message: text }; } }
    if (!response.ok) {
      const message = payload?.detail || payload?.message || payload?.error || `Request failed (${response.status}).`;
      const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }
  async function csrfToken() {
    const result = await api("/api/csrf");
    if (!result?.csrf_token) throw new Error("Could not establish a secure session. Please try again.");
    return result.csrf_token;
  }
  async function mutate(path, method, body, token) {
    const csrf = await csrfToken().catch((error) => {
      if (token) return token;
      throw error;
    });
    return api(path, { method, headers: { "X-CSRF-Token": csrf }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  }
  const showToast = (message) => {
    const toast = document.querySelector("[data-toast]");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.add("hidden"), 3200);
  };
  const fetchItemsForCart = async (cart = getCart()) => Promise.all(cart.map(async (row) => {
    try { return { ...row, item: await api(`/api/menu/${encodeURIComponent(row.id)}`) }; }
    catch (error) { return { ...row, item: null, error }; }
  }));
  document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.classList.add("js-reveal");
    updateCartBadge();
    const year = document.querySelector("[data-year]");
    if (year) year.textContent = String(new Date().getFullYear());
    const toggle = document.querySelector(".menu-toggle");
    const nav = document.querySelector("#primary-nav");
    if (toggle && nav) toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      toggle.textContent = open ? "×" : "☰";
    });
    reveal();
    initCursorGlow();
  });
  window.CraveCorner = { money, escapeHtml, getCart, saveCart, updateCartBadge, api, csrfToken, mutate, showToast, fetchItemsForCart, reveal };
})();
