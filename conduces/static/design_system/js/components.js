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
  document.querySelector(".ds-global-search input")?.addEventListener("keydown", event => {
    if (event.key === "Enter" && event.target.value.trim().length >= 2) {
      event.preventDefault();
      window.location.assign(`/core/buscar/?q=${encodeURIComponent(event.target.value.trim())}`);
    }
  });
  const favoriteButton = document.createElement("button");
  favoriteButton.type = "button"; favoriteButton.className = "ds-favorite-fab";
  favoriteButton.title = "Agregar o quitar esta pantalla de favoritos";
  favoriteButton.setAttribute("aria-label", favoriteButton.title); favoriteButton.textContent = "☆ Favorito";
  document.querySelector(".ds-main")?.prepend(favoriteButton);
  favoriteButton.addEventListener("click", async () => {
    const csrf = document.cookie.split("; ").find(x => x.startsWith("csrftoken="))?.split("=")[1];
    const data = new URLSearchParams({url: location.pathname, etiqueta: document.title, tipo: "pantalla"});
    const response = await fetch("/core/favoritos/toggle/", {method:"POST", headers:{"X-CSRFToken":csrf || "", "X-Requested-With":"XMLHttpRequest"}, body:data});
    if (!response.ok) return;
    const state = await response.json(); favoriteButton.textContent = state.favorite ? "★ Favorito" : "☆ Favorito";
    favoriteButton.setAttribute("aria-pressed", String(state.favorite));
  });
  const uxScope = [document.querySelector(".ds-user")?.dataset.userId, document.querySelector(".ds-company")?.dataset.companyId, location.pathname].join("|");
  document.querySelectorAll("table").forEach((table, tableIndex) => {
    table.classList.add("ds-enterprise-table"); table.parentElement?.classList.add("ds-enterprise-table-wrap");
    table.querySelectorAll("th").forEach(th => { th.tabIndex = 0; th.setAttribute("scope", "col"); });
    if (table.dataset.enterpriseControls === "off") return;
    if (!table.tHead || table.dataset.enterpriseReady) return; table.dataset.enterpriseReady = "true";
    const toolbar = document.createElement("div"); toolbar.className = "ds-table-toolbar"; toolbar.setAttribute("role", "toolbar");
    const search = document.createElement("input"); search.type = "search"; search.placeholder = "Buscar en la tabla"; search.setAttribute("aria-label", "Buscar en la tabla");
    search.addEventListener("input", () => table.querySelectorAll("tbody tr").forEach(row => row.hidden = !row.textContent.toLocaleLowerCase("es").includes(search.value.toLocaleLowerCase("es"))));
    const key = `sastre-private-views|${uxScope}|${tableIndex}`;
    const readViews = () => { try { return JSON.parse(localStorage.getItem(key)) || {views:[], defaultId:null}; } catch { return {views:[], defaultId:null}; } };
    const writeViews = state => localStorage.setItem(key, JSON.stringify(state));
    const selector = document.createElement("select"); selector.setAttribute("aria-label", "Vistas guardadas privadas");
    const renderViews = selected => { const state=readViews(); selector.replaceChildren(new Option("Vistas privadas", ""), ...state.views.map(view => new Option(`${view.id===state.defaultId ? "★ " : ""}${view.name}`, view.id))); selector.value=selected || ""; };
    selector.addEventListener("change", () => { const view=readViews().views.find(item => item.id===selector.value); if(view){search.value=view.query;search.dispatchEvent(new Event("input"));} });
    const save = document.createElement("button"); save.type="button"; save.className="ds-btn ds-btn--secondary ds-btn--sm"; save.textContent="Guardar vista";
    save.addEventListener("click", () => { const name=window.prompt("Nombre de la vista privada"); if(!name?.trim()) return; const state=readViews(); const id=String(Date.now()); state.views.push({id,name:name.trim(),query:search.value}); writeViews(state); renderViews(id); });
    const rename = document.createElement("button"); rename.type="button"; rename.className="ds-btn ds-btn--tertiary ds-btn--sm"; rename.textContent="Renombrar"; rename.addEventListener("click",()=>{const state=readViews(),view=state.views.find(item=>item.id===selector.value);if(!view)return;const name=window.prompt("Nuevo nombre",view.name);if(!name?.trim())return;view.name=name.trim();writeViews(state);renderViews(view.id);});
    const makeDefault = document.createElement("button"); makeDefault.type="button"; makeDefault.className="ds-btn ds-btn--tertiary ds-btn--sm"; makeDefault.textContent="Predeterminada"; makeDefault.addEventListener("click",()=>{if(!selector.value)return;const state=readViews();state.defaultId=selector.value;writeViews(state);renderViews(selector.value);});
    const remove = document.createElement("button"); remove.type="button"; remove.className="ds-btn ds-btn--tertiary ds-btn--sm"; remove.textContent="Eliminar vista"; remove.addEventListener("click",()=>{if(!selector.value)return;const state=readViews();state.views=state.views.filter(item=>item.id!==selector.value);if(state.defaultId===selector.value)state.defaultId=null;writeViews(state);renderViews();});
    const clear = document.createElement("button"); clear.type="button"; clear.className="ds-btn ds-btn--tertiary ds-btn--sm"; clear.textContent="Limpiar filtro"; clear.addEventListener("click",()=>{search.value="";search.dispatchEvent(new Event("input"));selector.value="";});
    renderViews(); const initial=readViews(); if(initial.defaultId){selector.value=initial.defaultId;selector.dispatchEvent(new Event("change"));}
    toolbar.append(search, selector, save, rename, makeDefault, remove, clear); table.parentElement?.before(toolbar);
  });
  document.querySelectorAll("form").forEach(form => { form.classList.add("ds-enterprise-form"); form.querySelectorAll("[required]").forEach(field => { const label = form.querySelector(`label[for="${field.id}"]`); if(label && !label.querySelector(".ds-required")){const mark=document.createElement("span");mark.className="ds-required";mark.textContent=" *";mark.setAttribute("aria-hidden","true");label.append(mark);} }); });
  document.querySelectorAll(".ds-messages .ds-alert").forEach(message => { message.classList.add("ds-toast"); message.setAttribute("role", message.classList.contains("ds-alert--danger") ? "alert" : "status"); });
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
