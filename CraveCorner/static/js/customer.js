(() => {
  "use strict";
  const C = window.CraveCorner;
  const e = C.escapeHtml;
  const foodImage = (item) => item.image_path ? `<img src="${e(item.image_path)}" alt="${e(item.name)}" loading="lazy" onerror="this.hidden=true">` : `<span class="image-placeholder" aria-hidden="true">${e((item.name || "C").slice(0, 1))}</span>`;
  const card = (item) => `<article class="dish-card reveal"><div class="dish-image">${foodImage(item)}</div><div class="dish-info"><div class="dish-meta"><h3>${e(item.name)}</h3><span class="price">${C.money(item.price)}</span></div><p>${e(item.description || "")}</p><div class="dish-foot"><span class="veg-tag">${item.is_vegetarian ? "Vegetarian" : e(item.category || "Made fresh")}</span><button class="button button-small" type="button" data-add-item="${e(item.id)}" aria-label="Add ${e(item.name)} to bag">Add +</button></div></div></article>`;
  const errorBlock = (message, retry) => `<div class="state-panel" role="alert"><h3>We couldn’t reach the kitchen.</h3><p>${e(message)}</p>${retry ? `<button class="button button-small" type="button" data-retry>Try again</button>` : ""}</div>`;
  function wireAddButtons(root = document) {
    root.querySelectorAll("[data-add-item]").forEach((button) => button.addEventListener("click", () => {
      const id = Number(button.dataset.addItem);
      const cart = C.getCart();
      const existing = cart.find((row) => row.id === id);
      if (existing) existing.quantity = Math.min(50, existing.quantity + 1);
      else cart.push({ id, quantity: 1 });
      C.saveCart(cart);
      C.showToast("Added to your bag.");
      button.textContent = "Added";
      setTimeout(() => { if (button.isConnected) button.textContent = "Add +"; }, 900);
    }));
  }
  async function loadFeatured() {
    const target = document.querySelector("[data-featured-menu]");
    if (!target) return;
    try {
      const items = await C.api("/api/menu");
      if (!items.length) { target.innerHTML = `<div class="state-panel" style="grid-column:1/-1"><h3>Today’s menu is taking a moment.</h3><p>There aren’t any dishes available right now. Please check back soon.</p><a class="text-link" href="/menu">Browse the menu →</a></div>`; return; }
      target.innerHTML = items.slice(0, 3).map(card).join("");
      wireAddButtons(target);
      C.reveal(target);
    } catch (error) { target.innerHTML = errorBlock(error.message, true); target.querySelector("[data-retry]")?.addEventListener("click", loadFeatured); }
  }
  async function initHomeCategories() {
    const target = document.querySelector("[data-home-categories]");
    if (!target) return;
    try {
      const items = await C.api("/api/menu");
      const categories = [...new Set(items.map((item) => item.category).filter(Boolean))].sort((a, b) => a.localeCompare(b));
      target.innerHTML = categories.length
        ? categories.map((name, index) => `<a class="category-card reveal" href="/menu?category=${encodeURIComponent(name)}"><span class="eyebrow">${String(index + 1).padStart(2, "0")} / From the menu</span><h3>${e(name)}</h3><span class="text-link">Explore ${e(name)} →</span></a>`).join("")
        : `<div class="state-panel" style="grid-column:1/-1"><h3>No categories are available.</h3><p>Please check the menu again later.</p></div>`;
      C.reveal(target);
    } catch (error) {
      target.innerHTML = errorBlock(error.message, true);
      target.querySelector("[data-retry]")?.addEventListener("click", initHomeCategories);
    }
  }
  async function initMenu() {
    const grid = document.querySelector("[data-menu-grid]");
    if (!grid) return;
    const form = document.querySelector("[data-menu-filters]");
    const tabs = document.querySelector("[data-category-tabs]");
    const count = document.querySelector("[data-menu-count]");
    let category = new URLSearchParams(window.location.search).get("category") || "";
    let timer;
    let allCategories = [];
    const load = async () => {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      const search = form.elements.search.value.trim();
      if (search) params.set("search", search);
      if (form.elements.vegetarian.checked) params.set("vegetarian", "true");
      grid.innerHTML = `<div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div>`;
      try {
        if (!allCategories.length) {
          const allItems = await C.api("/api/menu");
          allCategories = [...new Set(allItems.map((item) => item.category).filter(Boolean))].sort((a, b) => a.localeCompare(b));
        }
        const items = await C.api(`/api/menu${params.size ? `?${params.toString()}` : ""}`);
        const active = category;
        tabs.innerHTML = `<button class="category-tab" type="button" aria-pressed="${active === ""}" data-category="">Everything</button>${allCategories.map((name) => `<button class="category-tab" type="button" aria-pressed="${active === name}" data-category="${e(name)}">${e(name)}</button>`).join("")}`;
        tabs.querySelectorAll("[data-category]").forEach((button) => button.addEventListener("click", () => {
          category = button.dataset.category;
          const url = new URL(window.location.href);
          if (category) url.searchParams.set("category", category); else url.searchParams.delete("category");
          history.replaceState(null, "", url);
          load();
        }));
        count.textContent = `${items.length} ${items.length === 1 ? "dish" : "dishes"}${search ? ` matching “${search}”` : ""}`;
        grid.innerHTML = items.length ? items.map(card).join("") : `<div class="state-panel" style="grid-column:1/-1"><h3>No dishes found just yet.</h3><p>Try another search or category. The kitchen will be here when you’re ready.</p><button class="button button-small" data-clear-filters type="button">Clear filters</button></div>`;
        grid.querySelector("[data-clear-filters]")?.addEventListener("click", () => { category = ""; form.reset(); load(); });
        wireAddButtons(grid);
        C.reveal(grid);
      } catch (error) { count.textContent = ""; grid.innerHTML = errorBlock(error.message, true); grid.querySelector("[data-retry]")?.addEventListener("click", load); }
    };
    form.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
    form.addEventListener("change", load);
    load();
  }
  function renderCartRows(rows, target) {
    const valid = rows.filter((row) => row.item);
    if (rows.some((row) => !row.item)) C.saveCart(valid);
    if (!valid.length) {
      target.innerHTML = `<div class="state-panel"><h3>Your bag is having a quiet moment.</h3><p>There’s nothing in it yet. Let’s find something lovely.</p><a class="button" href="/menu">Explore the menu</a></div>`;
      document.querySelector("[data-summary-count]")?.replaceChildren("0");
      document.querySelector("[data-summary-total]")?.replaceChildren(C.money(0));
      const checkout = document.querySelector("[data-checkout-link]");
      if (checkout) { checkout.setAttribute("aria-disabled", "true"); checkout.classList.add("hidden"); }
      return;
    }
    const total = valid.reduce((sum, row) => sum + Number(row.item.price) * row.quantity, 0);
    target.innerHTML = `<div class="cart-list">${valid.map((row) => `<article class="cart-row"><div><h3>${e(row.item.name)}</h3><p>${C.money(row.item.price)} each</p></div><span class="price">${C.money(Number(row.item.price) * row.quantity)}</span><div class="quantity" aria-label="Quantity for ${e(row.item.name)}"><button type="button" data-quantity="${row.id}" data-delta="-1" aria-label="Remove one ${e(row.item.name)}">−</button><span>${row.quantity}</span><button type="button" data-quantity="${row.id}" data-delta="1" aria-label="Add one ${e(row.item.name)}">+</button></div></article>`).join("")}</div>`;
    document.querySelector("[data-summary-count]")?.replaceChildren(String(valid.reduce((sum, row) => sum + row.quantity, 0)));
    document.querySelector("[data-summary-total]")?.replaceChildren(C.money(total));
    document.querySelector("[data-checkout-link]")?.classList.remove("hidden");
    target.querySelectorAll("[data-quantity]").forEach((button) => button.addEventListener("click", async () => {
      const cart = C.getCart();
      const id = Number(button.dataset.quantity);
      const row = cart.find((entry) => entry.id === id);
      if (row) row.quantity += Number(button.dataset.delta);
      C.saveCart(cart);
      const updatedRows = valid.map((entry) => ({ ...entry, quantity: cart.find((current) => current.id === entry.id)?.quantity || 0 })).filter((entry) => entry.quantity > 0);
      renderCartRows(updatedRows, target);
    }));
  }
  async function initCart() {
    const target = document.querySelector("[data-cart-list]");
    if (!target) return;
    try { renderCartRows(await C.fetchItemsForCart(), target); }
    catch (error) { target.innerHTML = errorBlock(error.message, true); target.querySelector("[data-retry]")?.addEventListener("click", initCart); }
  }
  async function initCheckout() {
    const form = document.querySelector("[data-checkout-form]");
    if (!form) return;
    const summary = document.querySelector("[data-checkout-summary]");
    let rows;
    try {
      rows = (await C.fetchItemsForCart()).filter((row) => row.item);
      if (!rows.length) {
        summary.innerHTML = `<div class="state-panel"><h3>Your bag is empty.</h3><p>Add something from the menu before checkout.</p><a class="text-link" href="/menu">Browse the menu →</a></div>`;
        form.querySelector("[data-submit-order]").disabled = true;
        return;
      }
      C.saveCart(rows);
      summary.innerHTML = rows.map((row) => `<div class="order-summary-row"><span>${row.quantity} × ${e(row.item.name)}</span><strong>${C.money(row.item.price * row.quantity)}</strong></div>`).join("");
      const total = rows.reduce((sum, row) => sum + row.item.price * row.quantity, 0);
      document.querySelector("[data-checkout-total]").textContent = C.money(total);
    } catch (error) { summary.innerHTML = errorBlock(error.message, true); return; }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = form.querySelector("[data-form-message]");
      const submit = form.querySelector("[data-submit-order]");
      message.innerHTML = "";
      const name = form.elements.customer_name.value.trim();
      const phone = form.elements.customer_phone.value.trim();
      const address = form.elements.delivery_address.value.trim();
      if (name.length < 2 || phone.length < 10 || phone.length > 16 || !/^[+\d\s().-]+$/.test(phone)) {
        message.innerHTML = `<div class="error-message" role="alert">Please enter a name and a valid phone number (10–16 characters).</div>`;
        return;
      }
      submit.disabled = true; submit.textContent = "Sending your order…";
      try {
        const payload = { customer_name: name, customer_phone: phone, items: rows.map((row) => ({ menu_item_id: Number(row.item.id), quantity: row.quantity })) };
        if (address) payload.delivery_address = address;
        const result = await C.mutate("/api/orders", "POST", payload);
        C.saveCart([]);
        window.location.assign(`/confirmation/${encodeURIComponent(result.order_number)}`);
      } catch (error) {
        message.innerHTML = `<div class="error-message" role="alert">${e(error.message)}</div>`;
        submit.disabled = false; submit.innerHTML = `Place my order <span aria-hidden="true">→</span>`;
      }
    });
  }
  const formatTime = (value) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
  function renderOrder(order, result) {
    const statuses = ["PENDING", "PREPARING", "COMPLETED"];
    const state = statuses.indexOf(order.status);
    result.innerHTML = `<div style="margin-top:2rem"><div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap"><div><div class="eyebrow">Order ${e(order.order_number)}</div><h2 style="font-size:1.7rem;margin:0">${e(order.customer_name)}</h2></div><span class="status-pill">${e(order.status)}</span></div>
    <div class="track-steps" aria-label="Order progress">${["Received", "Preparing", "Ready"].map((label, index) => `<div class="track-step ${index <= state ? "done" : ""}"><div class="step-dot">${index < state ? "✓" : index + 1}</div>${label}</div>`).join("")}</div>
    <p class="muted" style="font-size:.85rem">Placed ${formatTime(order.created_at)}${order.started_at ? ` · Preparation began ${formatTime(order.started_at)}` : ""}${order.completed_at ? ` · Completed ${formatTime(order.completed_at)}` : ""}</p>
    <h3 style="font-size:1.1rem;margin:1.5rem 0 .5rem">In this order</h3>${(order.items || []).map((item) => `<div class="order-summary-row"><span>${Number(item.quantity)} × ${e(item.name)}</span><strong>${C.money(item.line_total)}</strong></div>`).join("")}<div class="summary-line summary-total"><span>Total</span><span>${C.money(order.total_amount)}</span></div></div>`;
  }
  async function initTracking() {
    const form = document.querySelector("[data-track-form]");
    const output = document.querySelector("[data-track-result]");
    if (!form || !output) return;
    let pollTimer;
    let currentOrder = "";
    const lookup = async (number) => {
      currentOrder = number;
      clearInterval(pollTimer);
      output.innerHTML = `<div class="skeleton" style="margin-top:2rem"></div><div class="skeleton"></div><div class="skeleton"></div>`;
      try {
        const order = await C.api(`/api/orders/${encodeURIComponent(number)}`);
        renderOrder(order, output);
        if (order.status !== "COMPLETED") pollTimer = setInterval(async () => {
          try {
            const latest = await C.api(`/api/orders/${encodeURIComponent(currentOrder)}`);
            renderOrder(latest, output);
            if (latest.status === "COMPLETED") clearInterval(pollTimer);
          } catch (_) { /* Retain the last known real status if a refresh is interrupted. */ }
        }, 12000);
      }
      catch (error) { output.innerHTML = `<div class="error-message" role="alert">${e(error.message)} Please check the order number and try again.</div>`; }
    };
    form.addEventListener("submit", (event) => { event.preventDefault(); const value = form.elements.order_number.value.trim(); if (value) { const url = new URL(window.location.href); url.searchParams.set("order", value); history.replaceState(null, "", url); lookup(value); } });
    const queryOrder = new URLSearchParams(window.location.search).get("order");
    if (queryOrder) { form.elements.order_number.value = queryOrder; lookup(queryOrder); }
  }
  function initConfirmation() {
    const root = document.querySelector("[data-confirmation]");
    if (!root) return;
    const pathNo = window.location.pathname.split("/").filter(Boolean).pop();
    const number = root.dataset.orderNumber || pathNo;
    const numberTarget = root.querySelector("[data-confirmation-number]");
    if (numberTarget) numberTarget.textContent = number;
    const trackLink = root.querySelector('a[href^="/tracking"]');
    if (trackLink) trackLink.href = `/tracking?order=${encodeURIComponent(number)}`;
    C.api(`/api/orders/${encodeURIComponent(number)}`).then((order) => {
      numberTarget.textContent = order.order_number;
      const summary = document.createElement("p");
      summary.className = "muted";
      summary.textContent = `${order.items?.length || 0} item types · ${C.money(order.total_amount)} · ${order.status}`;
      root.querySelector(".confirmation-box")?.append(summary);
    }).catch((error) => {
      const note = document.createElement("p"); note.className = "form-help"; note.textContent = `Order details are temporarily unavailable: ${error.message}`;
      root.querySelector(".confirmation-box")?.append(note);
    });
  }
  document.addEventListener("DOMContentLoaded", () => {
    loadFeatured(); initHomeCategories(); initMenu(); initCart(); initCheckout(); initTracking(); initConfirmation();
  });
})();
