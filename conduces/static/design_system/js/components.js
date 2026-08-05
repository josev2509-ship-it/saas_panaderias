(() => {
  const body = document.body;
  const openNav = () => { body.classList.add("ds-nav-open"); document.querySelector(".ds-sidebar-close")?.focus(); };
  const closeNav = () => { body.classList.remove("ds-nav-open"); document.querySelector(".ds-menu-toggle")?.focus(); };
  document.querySelector(".ds-menu-toggle")?.addEventListener("click", openNav);
  document.querySelector(".ds-sidebar-close")?.addEventListener("click", closeNav);
  document.querySelector(".ds-sidebar-overlay")?.addEventListener("click", closeNav);
  document.addEventListener("keydown", e => { if (e.key === "Escape") { closeNav(); document.querySelectorAll(".ds-modal:not([hidden])").forEach(x => x.hidden = true); } });
  body.classList.toggle("ds-sidebar-collapsed", localStorage.getItem("sastre-sidebar-collapsed") === "true");
  document.querySelector(".ds-collapse-toggle")?.addEventListener("click", () => {
    body.classList.toggle("ds-sidebar-collapsed");
    localStorage.setItem("sastre-sidebar-collapsed", String(body.classList.contains("ds-sidebar-collapsed")));
  });
  document.querySelectorAll(".app-menu a").forEach(link => {
    if (link.pathname === window.location.pathname) link.setAttribute("aria-current", "page");
  });
  document.querySelectorAll(".ds-nav-group").forEach((group, index) => {
    const key = `sastre-nav-${group.dataset.group || index}`;
    const hasActive = Boolean(group.querySelector('[aria-current="page"]'));
    group.open = hasActive || localStorage.getItem(key) === "open";
    group.addEventListener("toggle", () => localStorage.setItem(key, group.open ? "open" : "closed"));
  });
  document.querySelector("[data-menu-search]")?.addEventListener("input", event => {
    const query = event.target.value.trim().toLocaleLowerCase("es");
    document.querySelectorAll(".app-menu a").forEach(link => link.hidden = Boolean(query) && !link.textContent.toLocaleLowerCase("es").includes(query));
    document.querySelectorAll(".ds-nav-group").forEach(group => { const visible = Boolean(group.querySelector("a:not([hidden])")); group.hidden = Boolean(query) && !visible; if (query && visible) group.open = true; });
  });
  document.querySelectorAll("[data-ds-menu]").forEach(trigger => {
    const panel = document.getElementById(trigger.getAttribute("aria-controls"));
    trigger.addEventListener("click", () => { panel.hidden = !panel.hidden; trigger.setAttribute("aria-expanded", String(!panel.hidden)); });
  });
  document.querySelectorAll("[data-ds-modal-open]").forEach(trigger => trigger.addEventListener("click", () => {
    const modal = document.getElementById(trigger.dataset.dsModalOpen); modal.hidden = false; modal.querySelector("button,input,select,textarea,a")?.focus();
  }));
  document.querySelectorAll("[data-ds-modal-close]").forEach(trigger => trigger.addEventListener("click", () => trigger.closest(".ds-modal").hidden = true));
  document.querySelectorAll("form[data-ds-protect-submit], form[onsubmit*='confirm']").forEach(form => form.addEventListener("submit", () => {
    form.querySelectorAll("button[type=submit]").forEach(button => { button.disabled = true; button.setAttribute("aria-busy", "true"); button.dataset.originalText = button.textContent; button.textContent = "Procesando…"; });
  }));
})();
