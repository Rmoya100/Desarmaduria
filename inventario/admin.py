from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Categoria,
    ConceptoGasto,
    DetalleEntrada,
    DetalleVenta,
    Entrada,
    FormaPago,
    Gasto,
    Marca,
    Modelo,
    Permiso,
    Producto,
    ProductoFoto,
    Rol,
    RolPermiso,
    SaldoInicial,
    TipoDocumento,
    TipoVehiculo,
    Usuario,
    Vehiculo,
    Venta,
)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


class DetalleEntradaInline(admin.TabularInline):
    model = DetalleEntrada
    extra = 1


class ProductoFotoInline(admin.TabularInline):
    model = ProductoFoto
    extra = 0
    fields = ("imagen", "es_principal", "orden", "ancho_px", "alto_px", "peso_bytes")
    readonly_fields = ("ancho_px", "alto_px", "peso_bytes")


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Hereda de `UserAdmin`, no de `ModelAdmin`.

    Es importante: `UserAdmin` usa un formulario que HASHEA la contrasena al
    guardarla. Con un `ModelAdmin` comun, la clave se guardaria tal cual la
    escribio el operador, en texto plano.
    """

    list_display = ("username", "nombre_usuario", "email", "rol", "is_active")
    list_filter = ("is_active", "is_staff", "rol")
    search_fields = ("username", "nombre_usuario", "email")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("nombre_usuario", "email", "rol")}),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "nombre_usuario",
                    "email",
                    "rol",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("modelo", "tipo_vehiculo", "anio_desde", "anio_hasta", "patente")
    list_filter = ("modelo__marca", "tipo_vehiculo", "anio_desde")
    search_fields = ("patente", "modelo__nombre_modelo")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "categoria",
        "vehiculo",
        "costo",
        "precio_venta",
        "fecha_eliminacion",
        "eliminado_por",
    )
    list_filter = ("categoria", "fecha_eliminacion")
    search_fields = ("nombre", "codigo")
    inlines = [ProductoFotoInline]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id_venta", "fecha_venta", "tipo_documento", "forma_pago", "usuario")
    list_filter = ("fecha_venta", "tipo_documento", "forma_pago")
    inlines = [DetalleVentaInline]


@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ("id_entrada", "fecha", "vehiculo", "usuario")
    list_filter = ("fecha",)
    inlines = [DetalleEntradaInline]


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("id_gasto", "concepto", "forma_pago", "fecha", "monto", "usuario")
    list_filter = ("fecha", "concepto", "forma_pago")


@admin.register(SaldoInicial)
class SaldoInicialAdmin(admin.ModelAdmin):
    list_display = ("monto", "fecha", "usuario", "fecha_actualizacion")


admin.site.register(
    [
        Rol,
        Permiso,
        RolPermiso,
        Marca,
        Modelo,
        TipoVehiculo,
        Categoria,
        FormaPago,
        TipoDocumento,
        ConceptoGasto,
    ]
)
