"""Reglas de negocio del modulo de Ingresos de inventario.

Vive fuera de las vistas para poder probarse sin cliente HTTP y para que el
Django Admin o un comando puedan reutilizar exactamente las mismas reglas.

Modelo mental del flujo:

    CATALOGO (plantilla)        INGRESO                 PRODUCTO REAL
    producto sin vehiculo  -->  vehiculo del ingreso -> producto con vehiculo
    "PUERTA DEL. IZQ."          TOYOTA YARIS 2014-2018  y su stock propio

El operador marca cantidades sobre las piezas del catalogo; al guardar, cada
pieza se traduce al producto real de ese vehiculo (creandolo la primera vez).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from ..models import (
    DetalleEntrada,
    DetalleVenta,
    Marca,
    Modelo,
    Producto,
    TipoVehiculo,
    Vehiculo,
)


# ---------------------------------------------------------------------------
# Catalogo de piezas
# ---------------------------------------------------------------------------
def catalogo_piezas(categorias=None):
    """Piezas plantilla: productos sin vehiculo asignado y no eliminados.

    Son la lista que se ofrece al ingresar (una pieza generica por categoria);
    los productos CON vehiculo son stock real y no se ofrecen de nuevo.
    """
    piezas = Producto.objects.filter(
        vehiculo__isnull=True, fecha_eliminacion__isnull=True
    ).select_related("categoria")
    if categorias is not None:
        piezas = piezas.filter(categoria__in=categorias)
    return piezas.order_by("categoria__nombre_categoria", "nombre")


# ---------------------------------------------------------------------------
# Ficha de vehiculo
# ---------------------------------------------------------------------------
def obtener_o_crear_vehiculo(marca, modelo, tipo_vehiculo, anio_desde, anio_hasta=None):
    """Devuelve la ficha de vehiculo, creando marca/modelo/tipo si no existen.

    La busqueda es `iexact` a proposito: en la base pueden quedar registros
    antiguos con otra capitalizacion ("Toyota") y no deben duplicarse al
    ingresar el mismo dato en mayusculas.
    """
    if anio_hasta == anio_desde:
        # Un rango de un solo anio se guarda como rango abierto para que la
        # ficha sea siempre la misma se escriba "2014" o "2014-2014".
        anio_hasta = None

    registro_marca = Marca.objects.filter(nombre_marca__iexact=marca).first()
    if registro_marca is None:
        registro_marca = Marca.objects.create(nombre_marca=marca)

    registro_modelo = Modelo.objects.filter(
        marca=registro_marca, nombre_modelo__iexact=modelo
    ).first()
    if registro_modelo is None:
        registro_modelo = Modelo.objects.create(
            marca=registro_marca, nombre_modelo=modelo
        )

    registro_tipo = None
    if tipo_vehiculo:
        registro_tipo = TipoVehiculo.objects.filter(
            nombre_tipo__iexact=tipo_vehiculo
        ).first()
        if registro_tipo is None:
            registro_tipo = TipoVehiculo.objects.create(nombre_tipo=tipo_vehiculo)

    vehiculo = Vehiculo.objects.filter(
        modelo=registro_modelo,
        tipo_vehiculo=registro_tipo,
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
        patente__isnull=True,
    ).first()
    if vehiculo is not None:
        return vehiculo
    return Vehiculo.objects.create(
        modelo=registro_modelo,
        tipo_vehiculo=registro_tipo,
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
    )


# ---------------------------------------------------------------------------
# Traduccion de pieza del catalogo a producto real
# ---------------------------------------------------------------------------
def resolver_producto(producto_base, vehiculo):
    """Producto de stock para `vehiculo` equivalente a `producto_base`.

    Sirve para los dos casos: una plantilla del catalogo (sin vehiculo) y un
    producto de otro vehiculo, que aparece al cambiar el vehiculo de un
    ingreso ya guardado.
    """
    if producto_base.vehiculo_id == vehiculo.pk:
        return producto_base
    existente = Producto.objects.filter(
        nombre=producto_base.nombre,
        categoria_id=producto_base.categoria_id,
        vehiculo=vehiculo,
        fecha_eliminacion__isnull=True,
    ).first()
    if existente is not None:
        return existente
    return Producto.objects.create(
        nombre=producto_base.nombre,
        categoria_id=producto_base.categoria_id,
        vehiculo=vehiculo,
        costo=producto_base.costo,
    )


# ---------------------------------------------------------------------------
# Validacion de stock
# ---------------------------------------------------------------------------
def _totales_por_producto(modelo_detalle, pks):
    return {
        fila["producto"]: fila["total"]
        for fila in modelo_detalle.objects.filter(producto__in=pks)
        .values("producto")
        .annotate(total=Sum("cantidad"))
    }


def validar_stock_resultante(entrada, lineas):
    """Impide que editar o eliminar un ingreso deje stock negativo.

    Si de una pieza ya se vendieron 2 unidades, el ingreso que las aporto no
    puede bajarse a 1 ni eliminarse: la venta quedaria sin respaldo. Se
    comprueba producto por producto sobre el estado que quedaria en la base.

    `lineas` es la lista [(producto_real, cantidad)] que quedaria guardada;
    una lista vacia representa la eliminacion del ingreso.
    """
    cantidades_nuevas = {}
    for producto, cantidad in lineas:
        cantidades_nuevas[producto.pk] = cantidades_nuevas.get(producto.pk, 0) + cantidad

    cantidades_actuales = {}
    if entrada.pk:
        for detalle in entrada.detalles.all():
            cantidades_actuales[detalle.producto_id] = (
                cantidades_actuales.get(detalle.producto_id, 0) + detalle.cantidad
            )

    afectados = set(cantidades_nuevas) | set(cantidades_actuales)
    if not afectados:
        return

    ingresado = _totales_por_producto(DetalleEntrada, afectados)
    vendido = _totales_por_producto(DetalleVenta, afectados)
    nombres = dict(
        Producto.objects.filter(pk__in=afectados).values_list("pk", "nombre")
    )

    errores = []
    for pk in afectados:
        resultante = (
            ingresado.get(pk, 0)
            - cantidades_actuales.get(pk, 0)
            + cantidades_nuevas.get(pk, 0)
            - vendido.get(pk, 0)
        )
        if resultante < 0:
            errores.append(
                f"«{nombres.get(pk, pk)}»: ya se vendieron "
                f"{vendido.get(pk, 0)} unidades, no puedes dejar el stock en "
                f"{resultante}."
            )
    if errores:
        raise ValidationError(errores)


# ---------------------------------------------------------------------------
# Operaciones de escritura
# ---------------------------------------------------------------------------
@transaction.atomic
def registrar_ingreso(entrada, datos_vehiculo, fecha, lineas_base, usuario):
    """Crea o actualiza un ingreso completo.

    `lineas_base` viene del formulario como [(pieza_del_catalogo, cantidad)].
    Todo ocurre en una transaccion: si la validacion de stock falla no queda
    ni la ficha de vehiculo ni los productos que se hubieran creado.
    """
    vehiculo = obtener_o_crear_vehiculo(**datos_vehiculo)
    lineas = [
        (resolver_producto(base, vehiculo), cantidad)
        for base, cantidad in lineas_base
        if cantidad > 0
    ]
    validar_stock_resultante(entrada, lineas)

    entrada.fecha = fecha
    entrada.vehiculo = vehiculo
    if entrada.usuario_id is None:
        # El usuario que registro el ingreso no cambia al editarlo.
        entrada.usuario = usuario
    entrada.save()

    entrada.detalles.all().delete()
    DetalleEntrada.objects.bulk_create(
        [
            DetalleEntrada(entrada=entrada, producto=producto, cantidad=cantidad)
            for producto, cantidad in lineas
        ]
    )
    return entrada


@transaction.atomic
def eliminar_ingreso(entrada):
    """Elimina el ingreso y sus detalles (CASCADE) si no deja stock negativo."""
    validar_stock_resultante(entrada, [])
    entrada.delete()


# ---------------------------------------------------------------------------
# Lectura para la pantalla de edicion
# ---------------------------------------------------------------------------
def cantidades_por_pieza(entrada):
    """Cantidades del ingreso mapeadas a la pieza del catalogo que las origino.

    Los detalles apuntan a productos con vehiculo; la pantalla trabaja con las
    plantillas, asi que se busca la plantilla equivalente por nombre +
    categoria. Si un detalle no tiene plantilla (producto creado a mano) se
    conserva su propio id: `resolver_producto` sabe tratar ambos casos.
    """
    detalles = entrada.detalles.select_related("producto")
    if not detalles:
        return {}
    plantillas = {
        (pieza.categoria_id, pieza.nombre): pieza.pk for pieza in catalogo_piezas()
    }
    cantidades = {}
    for detalle in detalles:
        clave = (detalle.producto.categoria_id, detalle.producto.nombre)
        pk = plantillas.get(clave, detalle.producto_id)
        cantidades[pk] = cantidades.get(pk, 0) + detalle.cantidad
    return cantidades
