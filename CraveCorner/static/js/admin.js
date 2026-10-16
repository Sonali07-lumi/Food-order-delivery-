(() => {
  "use strict";
  const C = window.CraveCorner;
  const e = C.escapeHtml;
  let session = null;
  let refreshTimer = null;
  let showCompletedOnly = false;
  const formatDate = (value) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
  const errorText = (error) => e(error?.message || "The request could not be completed.");
  function displayError(target, error, retryAction) {
    if (!target) return;
    target.innerHTML = `<div class="error-message" role="alert">${errorText(error)}${retryAction ? ` <button class="button button-small" type="button" data-error-retry>Retry</button>` : ""}</div>`;
    target.querySelector("[data-error-retry]")?.addEventListener("click", retryAction);
  }
  async function initLogin() {
    const form = document.querySelector("[data-admin-login]");
    if (!form) return;
    try {
      const current = await C.api("/api/admin/session");
      if (current?.username) { session = current; window.location.replace("/admin"); return; }
    } catch (_) { /* unauthenticated is the normal sign-in state */ }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const target = form.querySelector("[data-login-message]");
      const button = form.querySelector("[data-login-submit]");
      target.innerHTML = "";
      if (!form.elements.username.value.trim() || !form.elements.password.value) {
        target.innerHTML = `<div class="admin-error" role="alert">Enter your username and password.</div>`;
        return;
      }
      button.disabled = true; button.textContent = "Signing in…";
      try {
        const csrf = await C.csrfToken();
        session = await C.api("/api/admin/login", { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify({ username: form.elements.username.value.trim(), password: form.elements.password.value }) });
        if (!session?.username) throw new Error("The server did not return an authenticated staff session.");
        window.location.assign("/admin");
      } catch (error) {
        target.innerHTML = `<div class="admin-error" role="alert">${errorText(error)}</div>`;
        button.disabled = false; button.textContent = "Sign in to the kitchen";
      }
    });
  }
  function statMarkup(stats) {
    return [
      ["All orders", stats.total_orders],
      ["Waiting", stats.pending_orders],
      ["Preparing", stats.preparing_orders],
      ["Completed", stats.completed_orders],
      ["Sales completed", C.money(stats.completed_revenue)]
    ].map(([label, value]) => `<article class="stat-card"><span>${e(label)}</span><strong>${typeof value === "number" ? e(value) : e(value)}</strong></article>`).join("");
  }
  function statusClass(status) { return String(status).toLowerCase(); }
  async function loadDashboard() {
    const statsEl = document.querySelector("[data-admin-stats]");
    const queueEl = document.querySelector("[data-admin-queue]");
    const ordersEl = document.querySelector("[data-admin-orders]");
    const errorEl = document.querySelector("[data-admin-error]");
    try {
      const [stats, queue, orders] = await Promise.all([
        C.api("/api/admin/stats"), C.api("/api/admin/queue"), C.api("/api/admin/orders")
      ]);
      errorEl.innerHTML = "";
      statsEl.innerHTML = statMarkup(stats);
      const queueIds = queue.active || [];
      const queueOrders = queueIds.map((id) => orders.find((order) => String(order.order_number) === String(id))).filter(Boolean);
      queueEl.innerHTML = queueOrders.length ? `<ol class="queue-list">${queueOrders.map((order, index) => `<li><span class="queue-num">${index + 1}</span><div><strong>${e(order.order_number)}</strong><div class="muted" style="font-size:.78rem">${e(order.customer_name)} · ${formatDate(order.created_at)}</div></div>${String(order.order_number) === String(queue.front) ? `<span class="queue-front">Next up</span>` : ""}</li>`).join("")}</ol><p class="form-help" style="margin-top:1rem">Next action: ${e(queue.next_action || "No action required")}</p>` : `<div class="state-panel"><h3>Queue is clear.</h3><p>New orders will appear here as soon as they arrive.</p></div>`;
      const visibleOrders = showCompletedOnly ? orders.filter((order) => order.status === "COMPLETED") : orders;
      ordersEl.innerHTML = visibleOrders.length ? visibleOrders.slice().sort((a, b) => new Date(a.created_at) - new Date(b.created_at)).map((order) => {
        const orderNumber = e(order.order_number);
        const lineItems = (order.items || []).map((item) => `${Number(item.quantity)} × ${e(item.name)} (${C.money(item.unit_price)} each)`).join("<br>");
        return `<tr>
          <td><strong>${orderNumber}</strong><div class="muted" style="font-size:.75rem">${formatDate(order.created_at)}</div></td>
          <td>${e(order.customer_name)}<div class="muted" style="font-size:.75rem">${e(order.customer_phone)}</div></td>
          <td>${(order.items || []).map((item) => `${Number(item.quantity)} × ${e(item.name)}`).join("<br>")}</td>
          <td>${C.money(order.total_amount)}</td><td><span class="status-label ${statusClass(order.status)}">${e(order.status)}</span></td>
          <td><div class="admin-actions"><button class="button button-small button-outline" type="button" data-order-view="${orderNumber}" aria-expanded="false">View details</button>${order.status === "PENDING" ? `<button class="button button-small" type="button" data-order-action="start" data-order="${orderNumber}" ${queue.front && String(order.order_number) !== String(queue.front) ? "disabled title=\"The next order must be handled first.\"" : ""}>Start</button>` : ""}${order.status === "PREPARING" ? `<button class="button button-small button-gold" type="button" data-order-action="complete" data-order="${orderNumber}">Complete</button>` : ""}${order.status === "COMPLETED" ? `<span class="muted">Done</span>` : ""}</div></td>
        </tr><tr class="order-detail-row" data-detail-row="${orderNumber}" hidden><td colspan="6"><div class="order-detail-grid">
          <div><h4>Items</h4><p>${lineItems}<br><strong>Total: ${C.money(order.total_amount)}</strong></p></div>
          <div><h4>Customer</h4><p>${e(order.customer_name)}<br>${e(order.customer_phone)}<br>${e(order.delivery_address || "No pickup or delivery note.")}</p></div>
          <div><h4>Timeline</h4><p>Received: ${formatDate(order.created_at)}<br>Preparing: ${formatDate(order.started_at)}<br>Completed: ${formatDate(order.completed_at)}</p></div>
        </div></td></tr>`;
      }).join("") : `<tr><td colspan="6"><div class="state-panel"><h3>${showCompletedOnly ? "No completed orders yet." : "No orders yet."}</h3><p>${showCompletedOnly ? "Completed orders will stay available in this history." : "Live customer orders will appear here."}</p></div></td></tr>`;
      ordersEl.querySelectorAll("[data-order-view]").forEach((button) => button.addEventListener("click", () => {
        const detail = [...ordersEl.querySelectorAll("[data-detail-row]")].find((row) => row.dataset.detailRow === button.dataset.orderView);
        if (!detail) return;
        detail.hidden = !detail.hidden;
        button.setAttribute("aria-expanded", String(!detail.hidden));
        button.textContent = detail.hidden ? "View details" : "Hide details";
      }));
      ordersEl.querySelectorAll("[data-order-action]").forEach((button) => button.addEventListener("click", () => transitionOrder(button)));
      const updated = document.querySelector("[data-last-updated]");
      if (updated) updated.textContent = `Updated ${new Intl.DateTimeFormat("en-IN", { timeStyle: "short" }).format(new Date())} · refreshes every 12 sec`;
    } catch (error) {
      displayError(errorEl, error, loadDashboard);
      if (error.status === 401 || error.status === 403) window.location.replace("/admin/login");
      else {
        statsEl.innerHTML = `<div class="state-panel" style="grid-column:1/-1"><h3>Live statistics unavailable.</h3><p>${errorText(error)}</p></div>`;
        queueEl.innerHTML = `<div class="state-panel"><h3>Queue unavailable.</h3><p>${errorText(error)}</p></div>`;
        ordersEl.innerHTML = `<tr><td colspan="6"><div class="state-panel"><h3>Orders unavailable.</h3><p>${errorText(error)}</p></div></td></tr>`;
      }
    }
  }
  async function transitionOrder(button) {
    const action = button.dataset.orderAction;
    const order = button.dataset.order;
    const original = button.textContent;
    button.disabled = true; button.textContent = action === "start" ? "Starting…" : "Completing…";
    try {
      await C.mutate(`/api/admin/orders/${encodeURIComponent(order)}/${action}`, "POST", undefined, session?.csrf_token);
      await loadDashboard();
      C.showToast(action === "start" ? "Order moved to preparation." : "Order marked complete.");
    } catch (error) {
      button.disabled = false; button.textContent = original;
      displayError(document.querySelector("[data-admin-error]"), error);
    }
  }
  async function initAdmin() {
    if (!document.querySelector(".admin-shell")) return;
    try {
      session = await C.api("/api/admin/session");
      if (!session?.username) throw Object.assign(new Error("Staff session required."), { status: 401 });
      document.querySelector("[data-admin-user]").textContent = session.username;
      await loadDashboard();
      refreshTimer = setInterval(loadDashboard, 12000);
    } catch (error) {
      if (error.status === 401 || error.status === 403) window.location.replace("/admin/login");
      else displayError(document.querySelector("[data-admin-error]"), error);
    }
    document.querySelector("[data-logout]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        await C.mutate("/api/admin/logout", "POST", undefined, session?.csrf_token);
        if (refreshTimer) clearInterval(refreshTimer);
        window.location.assign("/admin/login");
      } catch (error) {
        button.disabled = false;
        displayError(document.querySelector("[data-admin-error]"), error);
      }
    });
    document.querySelector("[data-refresh-orders]")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      const original = button.textContent;
      button.textContent = "Refreshing…";
      await loadDashboard();
      button.disabled = false;
      button.textContent = original;
    });
    document.querySelector("[data-show-completed]")?.addEventListener("click", async (event) => {
      showCompletedOnly = !showCompletedOnly;
      event.currentTarget.textContent = showCompletedOnly ? "Show all orders" : "View completed orders";
      await loadDashboard();
    });
  }
  document.addEventListener("DOMContentLoaded", () => { initLogin(); initAdmin(); });
})();
