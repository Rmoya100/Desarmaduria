from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum

from ..models import (
    Categoria,
    DetalleEntrada,
    Entrada,
    Producto,
    Vehiculo,
)

COLUMNAS = ["codigo", "nombre", "categoria", "vehiculo_id", "costo", "precio_venta", "stock_actual"]
COLUMNAS_MINIMAS = {"nombre", "categoria"}


def _texto(fila, clave):
    return str(fila.get(clave, "") or "").strip()


def _a_decimal(raw):
    texto = str(raw).strip().replace(",", ".") if raw is not None else ""
    if texto == "":
        return None
    return Decimal(texto)


def _a_entero(raw):
    texto = str(raw).strip().replace(",", ".") if raw is not None else ""
    if texto == "":
        return None
    return int(float(texto))


def _stock_actual(producto):
    entradas = producto.detalles_entrada.aggregate(t=Sum("cantidad"))["t"] or 0
    ventas = producto.detalles_venta.aggregate(t=Sum("cantidad"))["t"] or 0
    return entradas - ventas


def procesar_filas_productos(filas, usuario):
    creados = actualizados = ajustes_stock = 0
    errores = []
    preparadas = []

    # Pasada 1: validar sin tocar la base.
    for indice, fila in enumerate(filas, start=2):
        codigo = _texto(fila, "codigo")
        nombre = _texto(fila, "nombre")
        cat_nombre = _texto(fila, "categoria")
        veh_raw = _texto(fila, "vehiculo_id")

        existente = Producto.objects.filter(codigo=codigo).first() if codigo else None

        if not nombre and existente is None:
            errores.append(f"Fila {indice}: falta el nombre.")
            continue
        if not cat_nombre and existente is None:
            errores.append(f"Fila {indice}: falta la categoría.")
            continue
        if len(cat_nombre) > 50:
            errores.append(f"Fila {indice}: la categoría supera los 50 caracteres.")
            continue

        vehiculo = None
        if veh_raw:
            try:
                vehiculo = Vehiculo.objects.get(pk=int(float(veh_raw)))
            except (ValueError, TypeError, Vehiculo.DoesNotExist):
                errores.append(f"Fila {indice}: el vehículo id '{veh_raw}' no existe.")
                continue

        try:
            costo = _a_decimal(fila.get("costo"))
            precio_venta = _a_decimal(fila.get("precio_venta"))
            stock_excel = _a_entero(fila.get("stock_actual"))
        except (InvalidOperation, ValueError):
            errores.append(f"Fila {indice}: valores numéricos inválidos.")
            continue

        preparadas.append(
            {
                "fila": indice,
                "codigo": codigo,
                "nombre": nombre,
                "cat_nombre": cat_nombre,
                "veh_raw": veh_raw,
                "vehiculo": vehiculo,
                "costo": costo,
                "precio_venta": precio_venta,
                "stock_excel": stock_excel,
                "existente": existente,
            }
        )

    # Pasada 2: escribir todo dentro de una transaccion.
    try:
        with transaction.atomic():
            entrada_ajuste = None
            for datos in preparadas:
                categoria = None
                if datos["cat_nombre"]:
                    categoria, _ = Categoria.objects.get_or_create(
                        nombre_categoria=datos["cat_nombre"]
                    )

                producto = datos["existente"]
                if producto is None:
                    producto = Producto(
                        codigo=datos["codigo"] or None,
                        nombre=datos["nombre"],
                        categoria=categoria,
                        vehiculo=datos["vehiculo"],
                        costo=datos["costo"],
                        precio_venta=datos["precio_venta"],
                    )
                    producto.save()
                    creados += 1
                else:
                    if datos["nombre"]:
                        producto.nombre = datos["nombre"]
                    if categoria is not None:
                        producto.categoria = categoria
                    if datos["veh_raw"]:
                        producto.vehiculo = datos["vehiculo"]
                    if datos["costo"] is not None:
                        producto.costo = datos["costo"]
                    if datos["precio_venta"] is not None:
                        producto.precio_venta = datos["precio_venta"]
                    producto.save()
                    actualizados += 1

                if datos["stock_excel"] is not None:
                    actual = _stock_actual(producto)
                    delta = datos["stock_excel"] - actual
                    if delta > 0:
                        if entrada_ajuste is None:
                            entrada_ajuste = Entrada.objects.create(
                                fecha=date.today(), vehiculo=None, usuario=usuario
                            )
                        DetalleEntrada.objects.create(
                            entrada=entrada_ajuste, producto=producto, cantidad=delta
                        )
                        ajustes_stock += 1
                    elif delta < 0:
                        errores.append(
                            f"Fila {datos['fila']}: no se puede reducir stock por Excel "
                            f"({producto.nombre}: {actual} → {datos['stock_excel']}). "
                            "Regístralo con una venta."
                        )
    except Exception as exc:  # noqa: BLE001
        errores.append(f"Error inesperado — no se guardó nada: {exc}")
        return 0, 0, 0, errores

    return creados, actualizados, ajustes_stock, errores
