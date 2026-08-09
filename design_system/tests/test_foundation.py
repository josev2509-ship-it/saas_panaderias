import json
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from design_system.icons.registry import ICONS, icon
from design_system.validation import STATIC_ROOT, validate_static_contract


class FoundationContractTests(SimpleTestCase):
    required_files = (
        "tokens/colors.css", "tokens/typography.css", "tokens/spacing.css",
        "tokens/radius.css", "tokens/shadows.css", "tokens/elevation.css",
        "tokens/motion.css", "tokens/zindex.css", "tokens/breakpoints.css",
        "themes/light.css", "themes/dark.prepared.css", "foundations/grid.css",
        "foundations/layout.css", "foundations/utilities.css",
        "foundations/accessibility.css",
    )

    def read(self, relative):
        return (STATIC_ROOT / relative).read_text(encoding="utf-8")

    def test_required_assets_and_static_discovery(self):
        for relative in self.required_files:
            self.assertTrue((STATIC_ROOT / relative).is_file(), relative)
        self.assertIsNotNone(finders.find("sedl/sedl.css"))

    def test_required_color_scales_and_unique_tokens(self):
        colors = self.read("tokens/colors.css")
        for scale in ("primary", "neutral"):
            levels = (0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950) if scale == "neutral" else (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)
            for level in levels:
                self.assertIn(f"--sedl-{scale}-{level}:", colors)
        for scale in ("green", "amber", "red", "cyan"):
            for level in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950):
                self.assertIn(f"--sedl-{scale}-{level}:", colors)
        for path in (STATIC_ROOT / "tokens").glob("*.css"):
            names = re.findall(r"(--sedl-[\w-]+)\s*:", path.read_text(encoding="utf-8"))
            self.assertEqual(len(names), len(set(names)), path.name)

    def test_typography_spacing_radius_motion_and_zindex_names(self):
        joined = "\n".join(self.read(path) for path in self.required_files)
        for name in ("display", "h1", "h2", "h3", "h4", "h5", "body-lg", "body", "body-sm", "label", "caption", "overline", "code", "kpi-xs", "kpi-sm", "kpi-md", "kpi-lg"):
            for attribute in ("size", "weight", "line", "track"):
                self.assertIn(f"--sedl-type-{name}-{attribute}:", joined)
        for name in ("page-gutter", "section-gap", "card-padding", "form-gap", "inline-gap", "table-cell-x", "table-cell-y", "radius-round", "shadow-xl", "motion-slow", "ease-emphasized", "z-critical", "breakpoint-2xl"):
            self.assertIn(f"--sedl-{name}:", joined)

    def test_light_complete_and_dark_prepared_not_activated(self):
        aliases = ("bg", "surface", "text", "border", "interaction", "success", "warning", "danger", "info", "disabled-bg", "focus", "overlay", "chart-1")
        light, dark = self.read("themes/light.css"), self.read("themes/dark.prepared.css")
        for alias in aliases:
            self.assertIn(f"--sedl-{alias}:", light)
            self.assertIn(f"--sedl-{alias}:", dark)
        self.assertNotIn("dark.prepared.css", self.read("sedl.css"))

    def test_grid_accessibility_and_static_validation(self):
        self.assertIn("repeat(12", self.read("foundations/grid.css"))
        accessibility = self.read("foundations/accessibility.css")
        for marker in ("prefers-reduced-motion", "forced-colors", ":focus-visible", "sedl-skip-link", "sedl-touch-target", "sedl-visually-hidden"):
            self.assertIn(marker, accessibility)
        self.assertEqual(validate_static_contract(), [])

    def test_icon_registry_matches_manifest_and_fallback(self):
        manifest = json.loads((Path(__file__).parents[1] / "icons/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["icons"]), set(ICONS))
        self.assertEqual(icon("unknown").name, manifest["fallback"])
        self.assertEqual(manifest["color"], "currentColor")


class CatalogSecurityTests(TestCase):
    @override_settings(SEDL_CATALOG_ENABLED=True)
    def test_catalog_requires_authentication_and_staff(self):
        url = reverse("sedl:catalog")
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create(username="reader")
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)

    @override_settings(SEDL_CATALOG_ENABLED=True)
    def test_catalog_renders_for_staff(self):
        user = get_user_model().objects.create(username="staff", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse("sedl:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SEDL Core Foundation v1")
        self.assertContains(response, static("sedl/sedl.css"))

    @override_settings(SEDL_CATALOG_ENABLED=False)
    def test_catalog_can_be_disabled(self):
        user = get_user_model().objects.create(username="staff", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("sedl:catalog")).status_code, 404)
