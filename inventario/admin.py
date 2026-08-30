from django.contrib import admin

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
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "nombre_usuario", "email", "rol", "activo")
    list_filter = ("activo", "rol")
    search_fields = ("username", "nombre_usuario", "email")


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
    list_display = ("id_gasto", "concepto", "fecha", "monto", "usuario")
    list_filter = ("fecha", "concepto")


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
