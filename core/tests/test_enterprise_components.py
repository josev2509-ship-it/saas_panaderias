from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase

class EnterpriseComponentPropagationTests(SimpleTestCase):
    def setUp(self):
        root=Path(settings.BASE_DIR); self.js=(root/"conduces/static/design_system/js/components.js").read_text(encoding="utf-8"); self.css=(root/"conduces/static/design_system/css/components.css").read_text(encoding="utf-8")
    def test_table_and_private_saved_view_contract(self):
        for marker in ("ds-enterprise-table", "Guardar vista", "localStorage", "uxScope", "Vistas guardadas privadas", "Renombrar", "Predeterminada", "Eliminar vista"): self.assertIn(marker,self.js)
        base=(Path(settings.BASE_DIR)/"panaderia_saas/templates/base.html").read_text(encoding="utf-8")
        self.assertIn('data-user-id="{{ request.user.pk }}"',base); self.assertIn("data-company-id=",base)
    def test_forms_feedback_and_accessibility_contract(self):
        for marker in ("ds-enterprise-form", "[required]", "aria-hidden", "ds-toast", 'setAttribute("role"'): self.assertIn(marker,self.js)
    def test_visual_only_does_not_define_business_transitions(self):
        for forbidden in ("/aprobar/", "/rechazar/", "/contabilizar/", "/resolver/"):
            self.assertNotIn(forbidden, self.js.lower())
    def test_responsive_component_styles_exist(self):
        self.assertIn("ds-enterprise-table-wrap",self.css); self.assertIn("max-width:768px",(Path(settings.BASE_DIR)/"conduces/static/design_system/css/responsive.css").read_text(encoding="utf-8"))
    def test_alert_center_is_visual_only(self):
        template=(Path(settings.BASE_DIR)/"templates/core/experience/alerts.html").read_text(encoding="utf-8")
        self.assertIn("Ver origen",template); self.assertIn("ds-empty",template); self.assertNotIn("alerta_accion",template); self.assertNotIn("Resolver",template)
