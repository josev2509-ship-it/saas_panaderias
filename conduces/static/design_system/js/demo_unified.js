(() => {
  const main = document.querySelector('.ds-main');
  if (!main) return;
  main.dataset.demoUnified = 'true';
  const title = main.querySelector('h1');
  const hasHeader = title && title.closest('[data-enterprise-page-header],.ds-page-header,.com-hero,.el-page-header');
  if (title) {
    title.classList.add('ds-demo-title');
    if (!main.querySelector('.el-breadcrumbs,.ds-breadcrumbs,.ds-demo-breadcrumbs')) {
      const parts = location.pathname.split('/').filter(Boolean);
      const domain = parts[0] ? parts[0].replaceAll('-', ' ') : 'inicio';
      const nav = document.createElement('nav');
      nav.className = 'ds-demo-breadcrumbs';
      nav.setAttribute('aria-label', 'Migas de pan');
      nav.innerHTML = `<a href="/">Inicio</a><span>${domain}</span><span aria-current="page"></span>`;
      nav.lastElementChild.textContent = title.textContent.trim();
      const anchor = hasHeader ? title.closest('[data-enterprise-page-header],.ds-page-header,.com-hero,.el-page-header') : title;
      anchor.parentNode.insertBefore(nav, anchor);
    }
  }
  main.querySelectorAll('form').forEach(form => {
    if (form.querySelector('input[type="password"],input:not([type]),input[type="text"],select,textarea')) form.dataset.demoForm = 'true';
    const actions = [...form.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]')];
    if (actions.length && !actions[0].closest('.el-command-bar,.ds-filter-bar,.filters')) actions[actions.length - 1].parentElement?.classList.add('ds-demo-form-actions');
  });
  main.querySelectorAll('td, .empty, .ds-empty-state').forEach(node => {
    if (/^(sin |no hay |todavía no |aún no )/i.test(node.textContent.trim())) node.classList.add('ds-demo-empty');
  });
})();
