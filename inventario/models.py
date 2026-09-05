"""Modelos de la app `inventario`.

Portados desde schema_desarmaduria.sql. Se conservan los nombres de tabla y
de columna del esquema original mediante `Meta.db_table` y `db_column`, de modo
que `makemigrations` + `migrate` generan exactamente esas tablas en MySQL.

Notas de portabilidad:
- Los PK `... UNSIGNED AUTO_INCREMENT` se mapean a `AutoField` (INT). Django no
  distingue MEDIUMINT/SMALLINT; el rango efectivo es mayor, sin impacto funcional.
- `TINYINT(1)` -> `BooleanField`.
- `YEAR` -> `PositiveSmallIntegerField` (Django no tiene campo YEAR nativo).
- `DATETIME DEFAULT CURRENT_TIMESTAMP` -> `auto_now_add=True`.
- `rolPermiso` tenia PK compuesta (idRol, idPermiso); Django <5.2 no soporta PK
  compuesta, se usa PK surrogado `id` + restriccion UNIQUE sobre ambas FKs.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .services import convertir_a_webp


# ---------------------------------------------------------------------------
# Seguridad / usuarios
# ---------------------------------------------------------------------------
class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True, db_column="idRol")
    nombre_rol = models.CharField(max_length=50, unique=True, db_column="nombreRol")

    class Meta:
        db_table = "rol"

    def __str__(self):
        return self.nombre_rol


class Permiso(models.Model):
    id_permiso = models.AutoField(primary_key=True, db_column="idPermiso")
    nombre_permiso = models.CharField(max_length=50, db_column="nombrePermiso")
    modulo = models.CharField(max_length=50, db_column="modulo")

    class Meta:
        db_table = "permiso"
        constraints = [
            models.UniqueConstraint(
                fields=["modulo", "nombre_permiso"],
                name="uq_permiso_modulo_nombre",
            )
        ]

    def __str__(self):
        return f"{self.modulo}.{self.nombre_permiso}"


class RolPermiso(models.Model):
    rol = models.ForeignKey(
        Rol, on_delete=models.CASCADE, db_column="idRol", related_name="rol_permisos"
    )
    permiso = models.ForeignKey(
        Permiso,
        on_delete=models.CASCADE,
        db_column="idPermiso",
        related_name="rol_permisos",
    )

    class Meta:
        db_table = "rolPermiso"
        constraints = [
            models.UniqueConstraint(
                fields=["rol", "permiso"], name="uq_rolpermiso_rol_permiso"
            )
        ]

    def __str__(self):
        return f"{self.rol} / {self.permiso}"


class Usuario(AbstractUser):
  

    first_name = None
    last_name = None

    id = models.AutoField(primary_key=True, db_column="idUsuario")
    nombre_usuario = models.CharField(max_length=100, db_column="nombreUsuario")
    username = models.CharField(max_length=50, unique=True, db_column="username")
    email = models.EmailField(max_length=100, unique=True, db_column="email")
    password = models.CharField(max_length=255, db_column="passwordHash")
    # Nullable a proposito: el superusuario tecnico (createsuperuser) no tiene
    # un rol de negocio. Los usuarios reales SI deben tener uno.
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        db_column="idRol",
        related_name="usuarios",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_column="activo")
    date_joined = models.DateTimeField(auto_now_add=True, db_column="fechaCreacion")
    last_login = models.DateTimeField(null=True, blank=True, db_column="ultimoAcceso")

    # Campos que `createsuperuser` pedira ademas del username.
    REQUIRED_FIELDS = ["email", "nombre_usuario"]

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return self.username


# ---------------------------------------------------------------------------
# Vehiculos
# ---------------------------------------------------------------------------
class Marca(models.Model):
    id_marca = models.AutoField(primary_key=True, db_column="idMarca")
    nombre_marca = models.CharField(
        max_length=50, unique=True, db_column="nombreMarca"
    )

    class Meta:
        db_table = "marca"

    def __str__(self):
        return self.nombre_marca


class Modelo(models.Model):
    id_modelo = models.AutoField(primary_key=True, db_column="idModelo")
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, db_column="idMarca", related_name="modelos"
    )
    nombre_modelo = models.CharField(max_length=50, db_column="nombreModelo")

    class Meta:
        db_table = "modelo"
        constraints = [
            models.UniqueConstraint(
                fields=["marca", "nombre_modelo"], name="uq_modelo_marca_nombre"
            )
        ]

    def __str__(self):
        return f"{self.marca} {self.nombre_modelo}"


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True, db_column="idVehiculo")
    modelo = models.ForeignKey(
        Modelo,
        on_delete=models.PROTECT,
        db_column="idModelo",
        related_name="vehiculos",
    )
    anio = models.PositiveSmallIntegerField(db_column="anio")
    patente = models.CharField(
        max_length=10, null=True, blank=True, unique=True, db_column="patente"
    )

    class Meta:
        db_table = "vehiculo"

    def __str__(self):
        return self.patente or f"{self.modelo} ({self.anio})"


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True, db_column="idCategoria")
    nombre_categoria = models.CharField(
        max_length=50, unique=True, db_column="nombreCategoria"
    )

    class Meta:
        db_table = "categoria"

    def __str__(self):
        return self.nombre_categoria


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True, db_column="idProducto")
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        db_column="idCategoria",
        related_name="productos",
    )
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        db_column="idVehiculo",
        related_name="productos",
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=100, db_column="nombre")
    costo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, db_column="costo"
    )
    fecha_eliminacion = models.DateTimeField(
        null=True, blank=True, db_column="fechaEliminacion"
    )
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos_eliminados",
        db_column="eliminadoPor",
    )

    class Meta:
        db_table = "producto"

    def eliminar(self, usuario):
        self.fecha_eliminacion = timezone.now()
        self.eliminado_por = usuario
        self.save(update_fields=["fecha_eliminacion", "eliminado_por"])

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------
class FormaPago(models.Model):
    id_forma_pago = models.AutoField(primary_key=True, db_column="idFormaPago")
    forma_pago = models.CharField(
        max_length=50, unique=True, db_column="formaPago"
    )

    class Meta:
        db_table = "formaPago"

    def __str__(self):
        return self.forma_pago


class TipoDocumento(models.Model):
    id_tipo_documento = models.AutoField(
        primary_key=True, db_column="idTipoDocumento"
    )
    tipo_documento = models.CharField(
        max_length=50, unique=True, db_column="tipoDocumento"
    )

    class Meta:
        db_table = "tipoDocumento"

    def __str__(self):
        return self.tipo_documento


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True, db_column="idVenta")
    fecha_venta = models.DateField(db_column="fechaVenta")
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        db_column="idTipoDocumento",
        related_name="ventas",
    )
    forma_pago = models.ForeignKey(
        FormaPago,
        on_delete=models.PROTECT,
        db_column="idFormaPago",
        related_name="ventas",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="ventas",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, db_column="fechaRegistro"
    )

    class Meta:
        db_table = "venta"

    def __str__(self):
        return f"Venta #{self.id_venta} ({self.fecha_venta})"


class DetalleVenta(models.Model):
    id_detalle_venta = models.AutoField(
        primary_key=True, db_column="idDetalleVenta"
    )
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column="idVenta",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="detalles_venta",
    )
    cantidad = models.PositiveIntegerField(db_column="cantidad")
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="precio"
    )

    class Meta:
        db_table = "detalleVenta"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.producto_id or not self.cantidad:
            return
        from .servicios.inventario import productos_con_stock

        producto = productos_con_stock().get(pk=self.producto_id)
        stock = producto.stock_disponible
        if self.pk:
            stock += self.cantidad
        if self.cantidad > stock:
            raise ValidationError(
                {"cantidad": f"Stock insuficiente. Disponible: {stock}."}
            )

    def __str__(self):
        return f"{self.cantidad} x {self.producto} (venta {self.venta_id})"


# ---------------------------------------------------------------------------
# Entradas de stock
# ---------------------------------------------------------------------------
class Entrada(models.Model):
    id_entrada = models.AutoField(primary_key=True, db_column="idEntrada")
    fecha = models.DateField(db_column="fecha")
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        db_column="idVehiculo",
        related_name="entradas",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="entradas",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, db_column="fechaRegistro"
    )

    class Meta:
        db_table = "entrada"

    def __str__(self):
        return f"Entrada #{self.id_entrada} ({self.fecha})"


class DetalleEntrada(models.Model):
    id_detalle_entrada = models.AutoField(
        primary_key=True, db_column="idDetalleEntrada"
    )
    entrada = models.ForeignKey(
        Entrada,
        on_delete=models.CASCADE,
        db_column="idEntrada",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="detalles_entrada",
    )
    cantidad = models.PositiveIntegerField(db_column="cantidad")

    class Meta:
        db_table = "detalleEntrada"

    def __str__(self):
        return f"{self.cantidad} x {self.producto} (entrada {self.entrada_id})"


# ---------------------------------------------------------------------------
# Gastos
# ---------------------------------------------------------------------------
class ConceptoGasto(models.Model):
    id_concepto = models.AutoField(primary_key=True, db_column="idConcepto")
    nombre_gasto = models.CharField(
        max_length=50, unique=True, db_column="nombreGasto"
    )

    class Meta:
        db_table = "conceptoGasto"

    def __str__(self):
        return self.nombre_gasto


class Gasto(models.Model):
    id_gasto = models.AutoField(primary_key=True, db_column="idGasto")
    concepto = models.ForeignKey(
        ConceptoGasto,
        on_delete=models.PROTECT,
        db_column="idConcepto",
        related_name="gastos",
    )
    forma_pago = models.ForeignKey(
        FormaPago,
        on_delete=models.PROTECT,
        db_column="idFormaPago",
        related_name="gastos",
    )
    fecha = models.DateField(db_column="fecha")
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, db_column="monto"
    )
    observaciones = models.CharField(
        max_length=200, null=True, blank=True, db_column="observaciones"
    )
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="idTipoDocumento",
        related_name="gastos",
    )
    numero_documento = models.CharField(
        max_length=50, blank=True, db_column="numeroDocumento"
    )
    imagen = models.ImageField(
        upload_to="gastos/comprobantes/%Y/%m/",
        blank=True,
        null=True,
        db_column="imagen",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="gastos",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, db_column="fechaRegistro"
    )

    class Meta:
        db_table = "gasto"

    def __str__(self):
        return f"{self.concepto}: {self.monto} ({self.fecha})"

    def save(self, *args, **kwargs):
        # Se compara la extension en vez de un flag aparte: una vez
        # convertida, el nombre siempre termina en .webp, asi que un save()
        # posterior sin cambiar la imagen no la vuelve a procesar.
        if self.imagen and not self.imagen.name.lower().endswith(".webp"):
            self.imagen = convertir_a_webp(self.imagen)
        super().save(*args, **kwargs)
