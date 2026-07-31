(() => {
  const body = document.body;
  const openNav = () => { body.classList.add("ds-nav-open"); document.querySelector(".ds-sidebar-close")?.focus(); };
  const closeNav = () => { body.classList.remove("ds-nav-open"); document.querySelector(".ds-menu-toggle")?.focus(); };
  document.querySelector(".ds-menu-toggle")?.addEventListener("click", openNav);
  document.querySelector(".ds-sidebar-close")?.addEventListener("click", closeNav);
  document.querySelector(".ds-sidebar-overlay")?.addEventListener("click", closeNav);
  document.addEventListener("keydown", e => { if (e.key === "Escape") { closeNav(); document.querySelectorAll(".ds-modal:not([hidden])").forEach(x => x.hidden = true); } });
  document.querySelectorAll(".ds-nav-group").forEach((group, index) => {
    const key = `sastre-nav-${index}`;
    if (sessionStorage.getItem(key) === "open") group.open = true;
    group.addEventListener("toggle", () => sessionStorage.setItem(key, group.open ? "open" : "closed"));
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
