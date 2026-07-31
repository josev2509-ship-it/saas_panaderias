from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse

from conduces.decorators import modulo_requerido
from conduces.models import Empresa
from catalogos.models import Almacen, CentroCosto, CondicionPago, ConversionUnidad, Impuesto, Moneda, MonedaEmpresa, TipoCompra, UnidadMedida


class CatalogosTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("catalogos", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa", modulo_catalogos=True)
        self.otra_user = User.objects.create_user("otra", password="x")
        self.otra = Empresa.objects.create(usuario=self.otra_user, nombre="Otra")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="catalogos"))
        self.client.force_login(self.user)

    def pago(self, empresa=None, codigo="CONT"):
        return CondicionPago.objects.create(empresa=empresa or self.empresa, codigo=codigo, nombre="Contado", tipo="CONTADO")

    def test_mismo_codigo_es_valido_en_dos_empresas(self):
        self.pago()
        self.pago(self.otra)
        self.assertEqual(CondicionPago.objects.count(), 2)

    def test_codigo_es_unico_dentro_de_empresa(self):
        self.pago()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.pago()

    def test_una_moneda_base_y_almacen_principal_por_empresa(self):
        dop = Moneda.objects.create(codigo="DOP", nombre="Peso", simbolo="RD$")
        usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        MonedaEmpresa.objects.create(empresa=self.empresa, moneda=dop, es_base=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MonedaEmpresa.objects.create(empresa=self.empresa, moneda=usd, es_base=True)
        Almacen.objects.create(empresa=self.empresa, codigo="A1", nombre="Principal", tipo="GENERAL", principal=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Almacen.objects.create(empresa=self.empresa, codigo="A2", nombre="Otro", tipo="GENERAL", principal=True)

    def test_conversion_valida_empresa_y_factor(self):
        kg = UnidadMedida.objects.create(empresa=self.empresa, codigo="KG", nombre="Kilogramo", simbolo="kg", magnitud="PESO")
        g = UnidadMedida.objects.create(empresa=self.empresa, codigo="G", nombre="Gramo", simbolo="g", magnitud="PESO")
        conversion = ConversionUnidad(empresa=self.empresa, unidad_origen=kg, unidad_destino=g, factor=Decimal("1000"), vigente_desde=date.today())
        conversion.full_clean()
        conversion.save()
        self.assertEqual(conversion.factor, Decimal("1000"))

    def test_centro_costo_rechaza_ciclo(self):
        raiz = CentroCosto.objects.create(empresa=self.empresa, codigo="R", nombre="Raíz")
        hijo = CentroCosto.objects.create(empresa=self.empresa, codigo="H", nombre="Hijo", centro_padre=raiz)
        raiz.centro_padre = hijo
        with self.assertRaises(ValidationError):
            raiz.full_clean()

    def test_impuesto_rechaza_tasa_fuera_de_rango(self):
        impuesto = Impuesto(empresa=self.empresa, codigo="X", nombre="X", tipo="ITBIS", tasa=Decimal("101"), vigente_desde=date.today())
        with self.assertRaises(ValidationError):
            impuesto.full_clean()

    def test_listado_aisla_empresa_y_usa_design_system(self):
        self.pago(codigo="UNO")
        self.pago(self.otra, codigo="DOS")
        response = self.client.get(reverse("catalogos:lista", args=["condiciones-pago"]))
        self.assertContains(response, "UNO")
        self.assertNotContains(response, "DOS")
        self.assertContains(response, "ds-responsive-table")

    def test_objeto_de_otra_empresa_no_es_editable(self):
        objeto = self.pago(self.otra)
        response = self.client.get(reverse("catalogos:editar", args=["condiciones-pago", objeto.pk]))
        self.assertEqual(response.status_code, 404)


class ModuloRequeridoTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("seguro")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa", modulo_catalogos=True)

    def decorated(self):
        @modulo_requerido("modulo_catalogos", "catalogos.view_condicionpago")
        def view(request):
            from django.http import HttpResponse
            return HttpResponse("ok")
        return view

    def test_anonimo_redirige(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assertEqual(self.decorated()(request).status_code, 302)

    def test_modulo_y_permiso_son_obligatorios(self):
        request = self.factory.get("/")
        request.user = self.user
        with self.assertRaises(Exception):
            self.decorated()(request)
        self.user.user_permissions.add(Permission.objects.get(codename="view_condicionpago"))
        self.user = User.objects.get(pk=self.user.pk)
        request.user = self.user
        self.assertEqual(self.decorated()(request).status_code, 200)
        self.empresa.modulo_catalogos = False
        self.empresa.save(update_fields=["modulo_catalogos"])
        with self.assertRaises(Exception):
            self.decorated()(request)

    def test_usuario_sin_empresa_y_superusuario_sin_empresa_fallan_seguro(self):
        for user in (User.objects.create_user("sin"), User.objects.create_superuser("root", "root@example.com", "x")):
            request = self.factory.get("/")
            request.user = user
            with self.assertRaises(Exception):
                self.decorated()(request)
