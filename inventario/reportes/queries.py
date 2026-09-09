"""Consultas de agregacion para el modulo Reportes.

Separado de views.py porque cada reporte se pide en 3 formatos (HTML, PDF,
Excel) y los 3 deben agregar exactamente los mismos numeros.
"""

from datetime import date, timedelta
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

from ..models import DetalleVenta, Gasto, Producto, SaldoInicial, Venta

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
def ventas_anotadas():
    """Queryset base de Venta con `total_venta` (suma de cantidad*precio de
    sus detalles) ya anotado, sin filtro de fecha. Lo reutilizan tanto este
    reporte como el listado del modulo Ventas, para que ambos calculen el
    total de la misma forma."""
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)
    return (
        Venta.objects.select_related("tipo_documento", "forma_pago", "usuario")
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


def reporte_ventas(desde, hasta):
    detalles = DetalleVenta.objects.filter(
        venta__fecha_venta__gte=desde, venta__fecha_venta__lte=hasta
    )
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)

    ventas = ventas_anotadas().filter(
        fecha_venta__gte=desde, fecha_venta__lte=hasta
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
# Reporte 4: Flujo de caja (saldo inicial + ventas - gastos)
# ---------------------------------------------------------------------------
def saldo_caja(hasta):
    """Saldo en caja calculado hasta la fecha `hasta` (inclusive): el saldo
    inicial configurado mas las ventas y menos los gastos registrados desde
    su fecha de corte (o desde siempre, si aun no se ha cargado un saldo
    inicial)."""
    saldo_inicial = SaldoInicial.objects.first()
    monto_base = saldo_inicial.monto if saldo_inicial else Decimal("0")
    desde_corte = saldo_inicial.fecha if saldo_inicial else None

    ventas = DetalleVenta.objects.filter(venta__fecha_venta__lte=hasta)
    gastos = Gasto.objects.filter(fecha__lte=hasta)
    if desde_corte:
        ventas = ventas.filter(venta__fecha_venta__gte=desde_corte)
        gastos = gastos.filter(fecha__gte=desde_corte)

    total_ventas = (
        ventas.aggregate(total=Sum(F("cantidad") * F("precio"), output_field=MONTO))["total"]
        or Decimal("0")
    )
    total_gastos = gastos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    return monto_base + total_ventas - total_gastos


def reporte_caja(desde, hasta):
    """Utilidad mes a mes (reutiliza reporte_utilidad) mas el saldo en caja
    acumulado: cada fila arrastra el saldo del mes anterior, partiendo del
    saldo justo antes de `desde`."""
    datos = reporte_utilidad(desde, hasta)
    saldo_inicial = SaldoInicial.objects.first()

    inicio_arrastre = date.fromisoformat(desde) if isinstance(desde, str) else desde
    if saldo_inicial and saldo_inicial.fecha > inicio_arrastre:
        inicio_arrastre = saldo_inicial.fecha
    saldo_antes_del_periodo = saldo_caja(inicio_arrastre - timedelta(days=1))

    saldo_acumulado = saldo_antes_del_periodo
    for fila in datos["filas"]:
        saldo_acumulado += fila["utilidad"]
        fila["saldo_acumulado"] = saldo_acumulado

    return {
        **datos,
        "saldo_inicial": saldo_inicial,
        "saldo_antes_del_periodo": saldo_antes_del_periodo,
        "saldo_actual": saldo_acumulado,
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
