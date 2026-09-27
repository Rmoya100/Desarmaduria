from django.db.models import DecimalField, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from ..models import DetalleEntrada, DetalleVenta, Producto


def productos_con_stock():
    entradas = (
        DetalleEntrada.objects.filter(producto=OuterRef("pk"))
        .values("producto")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    ventas = (
        DetalleVenta.objects.filter(producto=OuterRef("pk"))
        .values("producto")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    cantidad = Value(0, output_field=IntegerField())
    return Producto.objects.filter(fecha_eliminacion__isnull=True).select_related(
        "categoria", "vehiculo__modelo__marca"
    ).annotate(
        total_entradas=Coalesce(Subquery(entradas), cantidad),
        total_vendido=Coalesce(Subquery(ventas), cantidad),
    ).annotate(
        stock_disponible=Coalesce(Subquery(entradas), cantidad)
        - Coalesce(Subquery(ventas), cantidad),
    ).order_by("categoria__nombre_categoria", "nombre")


def valor_inventario(productos):
    """Valor a precio de venta estimado (`Producto.precio_venta`), no a costo:
    en piezas usadas se compra el vehiculo completo, no cada pieza por
    separado, asi que `Producto.costo` no se lleva por unidad."""
    total = 0
    for producto in productos:
        total += (producto.precio_venta or 0) * producto.stock_disponible
    return total