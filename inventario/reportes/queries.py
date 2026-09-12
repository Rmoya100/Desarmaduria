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
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from ..models import DetalleVenta, Gasto, Producto, SaldoInicial, Venta

MONTO = DecimalField(max_digits=12, decimal_places=2)

# El "mes" de la desarmaduria para efectos de Dashboard/Reportes no es el mes
# calendario: va del dia 5 de un mes al dia 6 del siguiente (ciclo de cierre
# del negocio). Gastos/Ventas/Ingresos (sus propias listas y filtros) NO usan
# esto; solo el "periodo actual" por defecto y el agrupamiento "por mes" de
# Dashboard y Reportes.
DIA_INICIO_PERIODO = 5


def inicio_de_periodo(fecha):
    """Fecha de inicio (dia 5) del periodo de negocio al que pertenece
    `fecha`. Es la clave que se usa para agrupar 'por mes' en vez de
    TruncMonth, para que el corte real quede el 5, no el 1."""
    if fecha.day >= DIA_INICIO_PERIODO:
        return fecha.replace(day=DIA_INICIO_PERIODO)
    anio = fecha.year - 1 if fecha.month == 1 else fecha.year
    mes = 12 if fecha.month == 1 else fecha.month - 1
    return fecha.replace(year=anio, month=mes, day=DIA_INICIO_PERIODO)


def etiqueta_periodo(inicio):
    """'5 sep - 6 oct 2026': como se muestra un periodo en reportes/PDF."""
    fin = restar_meses(inicio, -1) + timedelta(days=1)
    if inicio.year == fin.year:
        return f"{inicio.day} {_MES_CORTO[inicio.month]} – {fin.day} {_MES_CORTO[fin.month]} {fin.year}"
    return (
        f"{inicio.day} {_MES_CORTO[inicio.month]} {inicio.year} – "
        f"{fin.day} {_MES_CORTO[fin.month]} {fin.year}"
    )


_MES_CORTO = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def rango_desde_hasta(request, dias_por_defecto=None, meses_por_defecto=None):
    """Lee `desde`/`hasta` de la query string; si faltan, usa el rango por
    defecto del reporte que llama (periodo de negocio actual, o los ultimos
    N periodos)."""
    hoy = timezone.localdate()
    if meses_por_defecto is not None:
        default_desde = restar_meses(inicio_de_periodo(hoy), meses_por_defecto - 1)
    elif dias_por_defecto is not None:
        default_desde = hoy - timedelta(days=dias_por_defecto)
    else:
        default_desde = inicio_de_periodo(hoy)
    desde = request.GET.get("desde") or default_desde.isoformat()
    hasta = request.GET.get("hasta") or hoy.isoformat()
    return desde, hasta


def restar_meses(fecha, meses):
    total = fecha.month - 1 - meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    return fecha.replace(year=anio, month=mes)


# ---------------------------------------------------------------------------
# Reporte 1: Ventas por periodo
# ---------------------------------------------------------------------------
def ventas_anotadas():
    """Queryset base de Venta con `total_venta` ya anotado, sin filtro de
    fecha. Lo reutilizan tanto este reporte como el listado del modulo
    Ventas (y Reportes/Utilidad/Caja/Dashboard), para que todos calculen el
    total de la misma forma: si la venta tiene `monto_total` guardado (pago
    con tarjeta/transferencia, ver Venta.monto_total) se usa ese valor -ya
    incluye el 19% de IVA-; si no (venta en efectivo), se suma
    cantidad*precio de sus DetalleVenta, igual que antes."""
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)
    detalle_total = Subquery(
        DetalleVenta.objects.filter(venta=OuterRef("pk"))
        .values("venta")
        .annotate(total=total_expr)
        .values("total")
    )
    return (
        Venta.objects.select_related("tipo_documento", "forma_pago", "usuario")
        .annotate(
            total_venta=Coalesce(
                F("monto_total"),
                detalle_total,
                Value(Decimal("0"), output_field=MONTO),
            )
        )
        .order_by("-fecha_venta", "-id_venta")
    )


def reporte_ventas(desde, hasta):
    ventas = ventas_anotadas().filter(
        fecha_venta__gte=desde, fecha_venta__lte=hasta
    )

    total_general = ventas.aggregate(total=Sum("total_venta"))["total"] or Decimal("0")
    por_forma_pago = (
        ventas.values("forma_pago__forma_pago")
        .annotate(total=Sum("total_venta"), iva=Sum("monto_iva"))
        .order_by("-total")
    )
    por_tipo_documento = (
        ventas.values("tipo_documento__tipo_documento")
        .annotate(total=Sum("total_venta"))
        .order_by("-total")
    )
    # Con IVA (transferencia/tarjeta, ver FormaPago.aplica_iva) vs sin IVA
    # (efectivo): las 2 metricas que pide "Dashboard y Reportes" ademas del
    # desglose fila por fila de por_forma_pago.
    resumen_iva = ventas.aggregate(
        total_efectivo=Coalesce(
            Sum("total_venta", filter=Q(monto_iva__isnull=True)), Decimal("0"), output_field=MONTO
        ),
        total_con_iva=Coalesce(
            Sum("total_venta", filter=Q(monto_iva__isnull=False)), Decimal("0"), output_field=MONTO
        ),
        total_iva=Coalesce(Sum("monto_iva"), Decimal("0"), output_field=MONTO),
    )

    return {
        "ventas": ventas,
        "total_general": total_general,
        "cantidad_ventas": ventas.count(),
        "por_forma_pago": por_forma_pago,
        "por_tipo_documento": por_tipo_documento,
        "total_efectivo": resumen_iva["total_efectivo"],
        "total_transferencia_tarjeta": resumen_iva["total_con_iva"],
        "total_iva": resumen_iva["total_iva"],
    }


# ---------------------------------------------------------------------------
# Reporte 2: Utilidad por periodo (ventas - gastos)
# ---------------------------------------------------------------------------
def reporte_utilidad(desde, hasta):
    # Se agrupa en Python por inicio_de_periodo() (dia 5), no con TruncMonth:
    # el corte del negocio no coincide con el mes calendario. El volumen de
    # ventas/gastos de una desarmaduria es bajo, asi que traer las filas
    # crudas y sumarlas aca no es un problema de rendimiento real.
    ventas = (
        ventas_anotadas()
        .filter(fecha_venta__gte=desde, fecha_venta__lte=hasta)
        .values_list("fecha_venta", "total_venta")
    )
    gastos = Gasto.objects.filter(fecha__gte=desde, fecha__lte=hasta).values_list(
        "fecha", "monto"
    )

    ventas_dict = {}
    for fecha_venta, total in ventas:
        clave = inicio_de_periodo(fecha_venta)
        ventas_dict[clave] = ventas_dict.get(clave, Decimal("0")) + total
    gastos_dict = {}
    for fecha, monto in gastos:
        clave = inicio_de_periodo(fecha)
        gastos_dict[clave] = gastos_dict.get(clave, Decimal("0")) + monto

    periodos = sorted(set(ventas_dict) | set(gastos_dict))

    filas = []
    total_ventas = Decimal("0")
    total_gastos = Decimal("0")
    for periodo in periodos:
        ventas_periodo = ventas_dict.get(periodo) or Decimal("0")
        gastos_periodo = gastos_dict.get(periodo) or Decimal("0")
        total_ventas += ventas_periodo
        total_gastos += gastos_periodo
        filas.append(
            {
                "mes": periodo,
                "etiqueta": etiqueta_periodo(periodo),
                "ventas": ventas_periodo,
                "gastos": gastos_periodo,
                "utilidad": ventas_periodo - gastos_periodo,
            }
        )

    return {
        "filas": filas,
        "total_ventas": total_ventas,
        "total_gastos": total_gastos,
        "total_utilidad": total_ventas - total_gastos,
    }


# ---------------------------------------------------------------------------
# Gastos por concepto y por periodo (tabla dinamica: filas=concepto,
# columnas=periodo)
# ---------------------------------------------------------------------------
def reporte_gastos_por_concepto(desde, hasta):
    filas = Gasto.objects.filter(fecha__gte=desde, fecha__lte=hasta).values_list(
        "concepto__nombre_gasto", "fecha", "monto"
    )

    periodos = set()
    por_concepto = {}
    for concepto, fecha, monto in filas:
        periodo = inicio_de_periodo(fecha)
        periodos.add(periodo)
        fila = por_concepto.setdefault(concepto, {})
        fila[periodo] = fila.get(periodo, Decimal("0")) + monto

    periodos = sorted(periodos)
    columnas = [{"inicio": p, "etiqueta": etiqueta_periodo(p)} for p in periodos]

    conceptos = []
    for nombre, montos_por_periodo in por_concepto.items():
        total_concepto = sum(montos_por_periodo.values(), Decimal("0"))
        conceptos.append(
            {
                "nombre": nombre,
                "montos": [montos_por_periodo.get(p, Decimal("0")) for p in periodos],
                "total": total_concepto,
            }
        )
    conceptos.sort(key=lambda c: c["total"], reverse=True)

    totales_por_periodo = [
        sum((c["montos"][i] for c in conceptos), Decimal("0")) for i in range(len(periodos))
    ]
    total_general = sum(totales_por_periodo, Decimal("0"))

    return {
        "columnas": columnas,
        "conceptos": conceptos,
        "totales_por_periodo": totales_por_periodo,
        "total_general": total_general,
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

    ventas = ventas_anotadas().filter(fecha_venta__lte=hasta)
    gastos = Gasto.objects.filter(fecha__lte=hasta)
    if desde_corte:
        ventas = ventas.filter(fecha_venta__gte=desde_corte)
        gastos = gastos.filter(fecha__gte=desde_corte)

    total_ventas = ventas.aggregate(total=Sum("total_venta"))["total"] or Decimal("0")
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


# ---------------------------------------------------------------------------
# Reporte 5: Ingresos por vehiculo
# ---------------------------------------------------------------------------
def reporte_ingresos_vehiculo(desde, hasta, limite=10):
    """Cuanto genero cada vehiculo (suma de cantidad*precio de las piezas
    vendidas que salieron de el) en el rango. Las piezas "plantilla de
    catalogo" (sin vehiculo asociado, ver Producto.vehiculo) no pertenecen a
    ningun vehiculo fisico y se excluyen: no hay como atribuirles un
    vehiculo de origen."""
    total_expr = Sum(F("cantidad") * F("precio"), output_field=MONTO)
    filas = (
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=desde,
            venta__fecha_venta__lte=hasta,
            producto__vehiculo__isnull=False,
        )
        .values(
            "producto__vehiculo",
            "producto__vehiculo__patente",
            "producto__vehiculo__modelo__nombre_modelo",
            "producto__vehiculo__modelo__marca__nombre_marca",
        )
        .annotate(total=total_expr, unidades=Sum("cantidad"))
        .order_by("-total")
    )

    vehiculos = [
        {
            "descripcion": (
                f"{fila['producto__vehiculo__modelo__marca__nombre_marca']} "
                f"{fila['producto__vehiculo__modelo__nombre_modelo']}"
                + (f" ({fila['producto__vehiculo__patente']})" if fila["producto__vehiculo__patente"] else "")
            ),
            "total": fila["total"],
            "unidades": fila["unidades"],
        }
        for fila in filas
    ]
    total_general = sum((v["total"] for v in vehiculos), Decimal("0"))

    return {
        "vehiculos": vehiculos[:limite],
        "total_general": total_general,
        "cantidad_vehiculos": len(vehiculos),
    }
