from django.db import models


# ==========================
# EMPRESA
# ==========================
class Empresa(models.Model):
    nombre = models.CharField(max_length=255)
    rnc = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)

    # Ejemplo: 0001, 0005, 0100
    numero_inicial_conduce = models.CharField(max_length=20, default='0001')

    def __str__(self):
        return self.nombre


# ==========================
# CENTRO EDUCATIVO
# ==========================
class CentroEducativo(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)
    director = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    regional_distrito = models.CharField(max_length=100, blank=True, null=True)
    matricula = models.IntegerField(default=0)
    orden_carga = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.nombre} - Matrícula: {self.matricula}"


# ==========================
# MENÚ DIARIO
# ==========================
class MenuDiario(models.Model):
    fecha = models.DateField(unique=True)
    producto = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.fecha} - {self.producto}"


# ==========================
# CONDUCE
# ==========================
class Conduce(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True)
    fecha = models.DateField()
    centro = models.ForeignKey(CentroEducativo, on_delete=models.CASCADE)
    producto = models.CharField(max_length=255)
    cantidad = models.IntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)

    ESTADOS = (
    ('borrador', 'Borrador'),
    ('generado', 'Generado'),
    ('entregado', 'Entregado'),
    ('anulado', 'Anulado'),
)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='borrador'
    )

    def save(self, *args, **kwargs):

        # ==========================
        # GENERAR NÚMERO AUTOMÁTICO
        # ==========================
        if not self.numero:
            formato_base = str(self.empresa.numero_inicial_conduce)

            conduces_empresa = Conduce.objects.filter(empresa=self.empresa)

            numeros_validos = []
            largo_formato = len(formato_base)

            for conduce in conduces_empresa:
                if conduce.numero and conduce.numero.isdigit():
                    numeros_validos.append(int(conduce.numero))
                    largo_formato = max(largo_formato, len(conduce.numero))

            if numeros_validos:
                nuevo_numero = max(numeros_validos) + 1
            else:
                nuevo_numero = int(formato_base)

            self.numero = str(nuevo_numero).zfill(largo_formato)

        # ==========================
        # TRAER MATRÍCULA DEL CENTRO
        # ==========================
        if not self.cantidad or self.cantidad == 0:
            self.cantidad = self.centro.matricula

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conduce {self.numero} - {self.centro.nombre}"