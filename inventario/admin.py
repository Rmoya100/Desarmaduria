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
    Rol,
    RolPermiso,
    TipoDocumento,
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
    list_display = ("patente", "modelo", "anio")
    list_filter = ("modelo__marca", "anio")
    search_fields = ("patente",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "vehiculo", "costo")
    list_filter = ("categoria",)
    search_fields = ("nombre",)


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


admin.site.register(
    [
        Rol,
        Permiso,
        RolPermiso,
        Marca,
        Modelo,
        Categoria,
        FormaPago,
        TipoDocumento,
        ConceptoGasto,
    ]
)
