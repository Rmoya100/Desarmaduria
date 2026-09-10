from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

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
def normalizar_texto(valor):
    """Estandariza los textos que identifican un vehiculo (marca, modelo,
    tipo, patente): sin espacios sobrantes y en MAYUSCULAS.

    Se aplica en `save()` y no solo en el formulario para que el dato quede
    igual venga de donde venga: el modulo de ingresos, el Django Admin o un
    comando de carga masiva.
    """
    if not valor:
        return valor
    return " ".join(str(valor).split()).upper()


class Marca(models.Model):
    id_marca = models.AutoField(primary_key=True, db_column="idMarca")
    nombre_marca = models.CharField(
        max_length=50, unique=True, db_column="nombreMarca"
    )

    class Meta:
        db_table = "marca"

    def save(self, *args, **kwargs):
        self.nombre_marca = normalizar_texto(self.nombre_marca)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_marca


class TipoVehiculo(models.Model):
    """Carroceria del vehiculo: SEDAN, SUV, CAMIONETA, FURGON..."""

    id_tipo_vehiculo = models.AutoField(
        primary_key=True, db_column="idTipoVehiculo"
    )
    nombre_tipo = models.CharField(
        max_length=50, unique=True, db_column="nombreTipo"
    )

    class Meta:
        db_table = "tipoVehiculo"
        verbose_name = "tipo de vehiculo"
        verbose_name_plural = "tipos de vehiculo"

    def save(self, *args, **kwargs):
        self.nombre_tipo = normalizar_texto(self.nombre_tipo)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_tipo


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

    def save(self, *args, **kwargs):
        self.nombre_modelo = normalizar_texto(self.nombre_modelo)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.marca} {self.nombre_modelo}"


class Vehiculo(models.Model):
    """Ficha de vehiculo: marca + modelo + tipo + rango de anios.

    No representa un auto fisico concreto sino una generacion del modelo:
    una misma pieza sirve para todos los anios del rango, asi que dos compras
    con los mismos datos reutilizan la misma ficha (ver
    `servicios.ingresos.obtener_o_crear_vehiculo`).
    """

    id_vehiculo = models.AutoField(primary_key=True, db_column="idVehiculo")
    modelo = models.ForeignKey(
        Modelo,
        on_delete=models.PROTECT,
        db_column="idModelo",
        related_name="vehiculos",
    )
    tipo_vehiculo = models.ForeignKey(
        TipoVehiculo,
        on_delete=models.PROTECT,
        db_column="idTipoVehiculo",
        related_name="vehiculos",
        null=True,
        blank=True,
    )
    # Conserva la columna `anio` original del esquema; el nombre en Python
    # cambia a `anio_desde` para que quede claro que es el inicio del rango.
    anio_desde = models.PositiveSmallIntegerField(db_column="anio")
    anio_hasta = models.PositiveSmallIntegerField(
        null=True, blank=True, db_column="anioHasta"
    )
    patente = models.CharField(
        max_length=10, null=True, blank=True, unique=True, db_column="patente"
    )

    class Meta:
        db_table = "vehiculo"

    @property
    def rango_anios(self):
        if self.anio_hasta and self.anio_hasta != self.anio_desde:
            return f"{self.anio_desde}-{self.anio_hasta}"
        return str(self.anio_desde)

    def save(self, *args, **kwargs):
        self.patente = normalizar_texto(self.patente) or None
        super().save(*args, **kwargs)

    def __str__(self):
        descripcion = f"{self.modelo} {self.rango_anios}"
        if self.patente:
            descripcion = f"{descripcion} · {self.patente}"
        return descripcion


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

    def save(self, *args, **kwargs):
        self.nombre_categoria = normalizar_texto(self.nombre_categoria)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_categoria


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True, db_column="idProducto")
    codigo = models.CharField(
        max_length=50, unique=True, null=True, blank=True, db_column="codigo"
    )
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
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        db_column="precioVenta",
    )
    foto = models.ImageField(
        upload_to="productos/%Y/%m/",
        blank=True,
        null=True,
        db_column="foto",
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

    @property
    def foto_principal(self):
        """Primera foto de la galeria marcada como principal.

        Mientras convive con el campo `foto` original (ver migracion de
        datos 0015), esto es lo que deben usar las plantillas en vez de
        `producto.foto` directamente.

        Si la vista ya trajo las fotos principales con `prefetch_related`
        (ver `_filtrar_lista_productos`), se reusa ese resultado en vez de
        lanzar una consulta nueva por producto listado (evita N+1).
        """
        prefetch = getattr(self, "_fotos_principales_prefetch", None)
        if prefetch is not None:
            return prefetch[0] if prefetch else None
        return self.fotos.filter(es_principal=True).first()

    @property
    def descripcion_completa(self):
        """Nombre + vehiculo (marca, modelo, anio) cuando el producto es
        stock real de un vehiculo puntual; solo el nombre si es una
        plantilla de catalogo. Se usa en Ventas para no confundir productos
        con el mismo nombre que pertenecen a vehiculos distintos (una fila
        Producto por vehiculo, ver docs/analisis_fotos_productos.md)."""
        if self.vehiculo_id:
            return f"{self.nombre} · {self.vehiculo}"
        return self.nombre

    def eliminar(self, usuario):
        self.fecha_eliminacion = timezone.now()
        self.eliminado_por = usuario
        self.save(update_fields=["fecha_eliminacion", "eliminado_por"])

    def save(self, *args, **kwargs):
        # Mismo estandar que marca/modelo/categoria: sin esto, una pieza
        # creada a mano como "puerta trasera" convivria en el catalogo con la
        # "PUERTA TRASERA" importada del Excel como si fueran distintas.
        self.nombre = normalizar_texto(self.nombre)
        if self.foto and not self.foto.name.lower().endswith(".webp"):
            self.foto = convertir_a_webp(self.foto)
        super().save(*args, **kwargs)
        # El codigo depende del pk, asi que se completa tras el primer INSERT.
        if not self.codigo:
            self.codigo = f"PRD-{self.pk:06d}"
            super().save(update_fields=["codigo"])

    def __str__(self):
        return self.descripcion_completa


def ruta_foto_producto(instance, filename):
    """Ruta trazable a marca/modelo/categoria/producto sin consultar la BD:
    productos/<vehiculo|catalogo>/<categoria>/<producto_id>/<uuid>.webp"""
    producto = instance.producto
    vehiculo_slug = str(producto.vehiculo_id) if producto.vehiculo_id else "catalogo"
    categoria_slug = slugify(producto.categoria.nombre_categoria) or "sin-categoria"
    return f"productos/{vehiculo_slug}/{categoria_slug}/{producto.id_producto}/{uuid4().hex}.webp"


class ProductoFoto(models.Model):
    """Una de N fotos de un `Producto` (galeria).

    No se necesita una entidad intermedia entre `Vehiculo` y `Producto` para
    esto: `Producto` ya identifica de forma unica la combinacion
    Marca+Modelo+Anio+Categoria+Producto (ver analisis en
    docs/analisis_fotos_productos.md), asi que la foto cuelga directo de el.
    """

    id_foto = models.AutoField(primary_key=True, db_column="idFoto")
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, db_column="idProducto", related_name="fotos"
    )
    imagen = models.ImageField(upload_to=ruta_foto_producto, db_column="imagen")
    es_principal = models.BooleanField(default=False, db_column="esPrincipal")
    orden = models.PositiveSmallIntegerField(default=0, db_column="orden")
    ancho_px = models.PositiveSmallIntegerField(null=True, blank=True, db_column="anchoPx")
    alto_px = models.PositiveSmallIntegerField(null=True, blank=True, db_column="altoPx")
    peso_bytes = models.PositiveIntegerField(null=True, blank=True, db_column="pesoBytes")
    creado_en = models.DateTimeField(auto_now_add=True, db_column="creadoEn")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="creadoPor",
        related_name="fotos_producto_creadas",
    )

    class Meta:
        db_table = "productoFoto"
        ordering = ["orden", "id_foto"]
        indexes = [
            models.Index(fields=["producto", "es_principal"]),
            models.Index(fields=["producto", "orden"]),
        ]

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen.name.lower().endswith(".webp"):
            self.imagen = convertir_a_webp(self.imagen)
        if self.imagen:
            self.peso_bytes = self.imagen.size
            try:
                self.ancho_px, self.alto_px = self.imagen.width, self.imagen.height
            except Exception:
                pass
        es_la_primera_foto = not self.pk and not self.producto.fotos.exists()
        if es_la_primera_foto:
            self.es_principal = True
        super().save(*args, **kwargs)
        if self.es_principal:
            # Garantiza una unica foto principal por producto (a nivel de
            # aplicacion: MySQL no soporta indices unicos filtrados simples).
            self.producto.fotos.exclude(pk=self.pk).update(es_principal=False)

    def delete(self, *args, **kwargs):
        producto = self.producto
        era_principal = self.es_principal
        super().delete(*args, **kwargs)
        if era_principal:
            # Si se borra la foto principal, la siguiente por orden la
            # reemplaza automaticamente: siempre debe haber una principal
            # mientras existan fotos.
            siguiente = producto.fotos.order_by("orden", "id_foto").first()
            if siguiente:
                siguiente.es_principal = True
                siguiente.save(update_fields=["es_principal"])

    def __str__(self):
        return f"Foto {self.id_foto} de {self.producto}"


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
        if self.imagen and not self.imagen.name.lower().endswith(".webp"):
            self.imagen = convertir_a_webp(self.imagen)
        super().save(*args, **kwargs)


class SaldoInicial(models.Model):
    """Carga del saldo en caja al empezar a usar el sistema.

    Es un dato de configuracion, no un movimiento: siempre hay una unica fila
    (pk=1). El saldo en caja actual se calcula al vuelo (ver
    reportes/queries.py) como este monto mas las ventas y menos los gastos
    registrados desde `fecha` en adelante.
    """

    id_saldo_inicial = models.AutoField(primary_key=True, db_column="idSaldoInicial")
    monto = models.DecimalField(max_digits=12, decimal_places=2, db_column="monto")
    fecha = models.DateField(db_column="fecha")
    observaciones = models.CharField(
        max_length=200, null=True, blank=True, db_column="observaciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="idUsuario",
        related_name="saldos_iniciales_editados",
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, db_column="fechaActualizacion"
    )

    class Meta:
        db_table = "saldoInicial"

    def __str__(self):
        return f"Saldo inicial: {self.monto} (desde {self.fecha})"
