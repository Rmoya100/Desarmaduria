"""Consultas de agregacion para el modulo Reportes.

Separado de views.py porque cada reporte se pide en 3 formatos (HTML, PDF,
Excel) y los 3 deben agregar exactamente los mismos numeros.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    DecimalField,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from ..models import DetalleVenta, Gasto, Producto, Venta

MONTO = DecimalField(max_digits=12, decimal_places=2)


def rango_desde_hasta(request, dias_por_defecto=None, meses_por_defecto=None):
    """Lee `desde`/`hasta` de la query string; si faltan, usa el rango por
    defecto del reporte que llama (mes actual, o los ultimos N meses)."""
    hoy = timezone.localdate()
    if meses_por_defecto is not None:
        default_desde = restar_meses(hoy.replace(day=1), meses_por_defecto - 1)
    elif dias_por_defecto is not None:
        default_desde = hoy - timedelta(days=dias_por_defecto)
    else:
        default_desde = hoy.replace(day=1)
    desde = request.GET.get("desde") or default_desde.isoformat()
    hasta = request.GET.get("hasta") or hoy.isoformat()
    return desde, hasta


def restar_meses(fecha, meses):
    total = fecha.month - 1 - meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    return fecha.replace(year=anio, month=mes, day=1)


# ---------------------------------------------------------------------------
# Reporte 1: Ventas por periodo
# ---------------------------------------------------------------------------
def reporte_ventas(desde, hasta):
    detalles = DetalleVenta.objects.filter(
        venta__fecha_venta__gte=desde, venta__fecha_venta__lte=hasta
    )
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)

    ventas = (
        Venta.objects.filter(fecha_venta__gte=desde, fecha_venta__lte=hasta)
        .select_related("tipo_documento", "forma_pago", "usuario")
        .annotate(
            total_venta=Coalesce(
                Subquery(
                    DetalleVenta.objects.filter(venta=OuterRef("pk"))
                    .values("venta")
                    .annotate(total=total_expr)
                    .values("total")
                ),
                Value(Decimal("0"), output_field=MONTO),
            )
        )
        .order_by("-fecha_venta", "-id_venta")
    )

    total_general = detalles.aggregate(total=total_expr)["total"] or Decimal("0")
    por_forma_pago = (
        detalles.values("venta__forma_pago__forma_pago")
        .annotate(total=total_expr)
        .order_by("-total")
    )
    por_tipo_documento = (
        detalles.values("venta__tipo_documento__tipo_documento")
        .annotate(total=total_expr)
        .order_by("-total")
    )

    return {
        "ventas": ventas,
        "total_general": total_general,
        "cantidad_ventas": ventas.count(),
        "por_forma_pago": por_forma_pago,
        "por_tipo_documento": por_tipo_documento,
    }


# ---------------------------------------------------------------------------
# Reporte 2: Utilidad por mes (ventas - gastos)
# ---------------------------------------------------------------------------
def reporte_utilidad(desde, hasta):
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)

    ventas_por_mes = (
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=desde, venta__fecha_venta__lte=hasta
        )
        .annotate(mes=TruncMonth("venta__fecha_venta"))
        .values("mes")
        .annotate(total=total_expr)
    )
    gastos_por_mes = (
        Gasto.objects.filter(fecha__gte=desde, fecha__lte=hasta)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
    )

    ventas_dict = {fila["mes"]: fila["total"] for fila in ventas_por_mes}
    gastos_dict = {fila["mes"]: fila["total"] for fila in gastos_por_mes}
    meses = sorted(set(ventas_dict) | set(gastos_dict))

    filas = []
    total_ventas = Decimal("0")
    total_gastos = Decimal("0")
    for mes in meses:
        ventas_mes = ventas_dict.get(mes) or Decimal("0")
        gastos_mes = gastos_dict.get(mes) or Decimal("0")
        total_ventas += ventas_mes
        total_gastos += gastos_mes
        filas.append(
            {
                "mes": mes,
                "ventas": ventas_mes,
                "gastos": gastos_mes,
                "utilidad": ventas_mes - gastos_mes,
            }
        )

    return {
        "filas": filas,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "total_utilidad": total_ventas - total_gastos,
    }


# ---------------------------------------------------------------------------
# Reporte 3: Rotacion de productos (mas / menos vendidos en el rango)
# ---------------------------------------------------------------------------
def reporte_rotacion(desde, hasta, limite=10):
    ventas_rango = (
        DetalleVenta.objects.filter(
            producto=OuterRef("pk"),
            venta__fecha_venta__gte=desde,
            venta__fecha_venta__lte=hasta,
        )
        .values("producto")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    cero = Value(0, output_field=IntegerField())

    productos = (
        Producto.objects.filter(fecha_eliminacion__isnull=True)
        .select_related("categoria", "vehiculo__modelo__marca")
        .annotate(cantidad_vendida=Coalesce(Subquery(ventas_rango), cero))
    )

    return {
        "mas_vendidos": productos.order_by("-cantidad_vendida", "nombre")[:limite],
        "menos_vendidos": productos.order_by("cantidad_vendida", "nombre")[:limite],
    }
