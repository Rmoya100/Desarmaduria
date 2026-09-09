"""Vistas del modulo de Ingresos de inventario.

Funciones basadas en vistas (mismo estilo que Ventas) con permiso explicito
por accion. La logica de negocio esta en `servicios.ingresos`; aqui solo se
orquesta: validar formularios, llamar al servicio y elegir que renderizar.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Entrada, Marca, Modelo, TipoVehiculo
from ..permisos import permiso_requerido, tiene_permiso
from ..servicios.ingresos import (
    cantidades_por_pieza,
    catalogo_piezas,
    eliminar_ingreso,
    registrar_ingreso,
)
from .forms import (
    CategoriasIngresoForm,
    EntradaForm,
    LineasIngresoForm,
    VehiculoIngresoForm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ingresos_filtrados(request):
    """Ingresos ordenados por fecha y acotados por desde/hasta= si vienen en la
    URL. Las cantidades se agregan en la consulta para no recorrer los
    detalles de cada ingreso en la plantilla (N+1)."""
    queryset = (
        Entrada.objects.select_related(
            "vehiculo__modelo__marca", "vehiculo__tipo_vehiculo", "usuario"
        )
        .annotate(
            piezas=Count("detalles", distinct=True),
            unidades=Sum("detalles__cantidad"),
        )
        .order_by("-fecha", "-id_entrada")
    )
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    if desde:
        queryset = queryset.filter(fecha__gte=desde)
    if hasta:
        queryset = queryset.filter(fecha__lte=hasta)
    return queryset


def _piezas_permitidas(entrada):
    """Piezas que el formulario puede aceptar: el catalogo completo mas las
    piezas ya ingresadas que no tengan una plantilla equivalente (productos
    creados a mano desde el modulo de Productos)."""
    piezas = list(catalogo_piezas())
    if not entrada.pk:
        return piezas
    claves = {(pieza.categoria_id, pieza.nombre) for pieza in piezas}
    for detalle in entrada.detalles.select_related("producto__categoria"):
        producto = detalle.producto
        if (producto.categoria_id, producto.nombre) in claves:
            continue
        claves.add((producto.categoria_id, producto.nombre))
        piezas.append(producto)
    return piezas


def _agrupar_por_categoria(piezas, cantidades, seleccionadas):
    """Estructura que consume la plantilla: una lista de categorias, cada una
    con sus piezas y la cantidad tecleada (o guardada) de cada pieza."""
    grupos = {}
    for pieza in piezas:
        grupo = grupos.setdefault(
            pieza.categoria_id,
            {
                "categoria": pieza.categoria,
                "piezas": [],
                "seleccionada": pieza.categoria_id in seleccionadas,
            },
        )
        cantidad = cantidades.get(pieza.pk)
        grupo["piezas"].append(
            {"pieza": pieza, "cantidad": "" if not cantidad else cantidad}
        )
    return sorted(
        grupos.values(), key=lambda grupo: grupo["categoria"].nombre_categoria
    )


def _initial_vehiculo(entrada):
    vehiculo = entrada.vehiculo if entrada.pk else None
    if vehiculo is None:
        return {}
    return {
        "marca": vehiculo.modelo.marca.nombre_marca,
        "modelo": vehiculo.modelo.nombre_modelo,
        "tipo_vehiculo": (
            vehiculo.tipo_vehiculo.nombre_tipo if vehiculo.tipo_vehiculo else ""
        ),
        "anio_desde": vehiculo.anio_desde,
        "anio_hasta": vehiculo.anio_hasta,
    }


def _procesar_formulario(request, entrada, titulo, mensaje_exito):
    piezas = _piezas_permitidas(entrada)

    if request.method == "POST":
        form = EntradaForm(request.POST, instance=entrada)
        form_vehiculo = VehiculoIngresoForm(request.POST)
        form_categorias = CategoriasIngresoForm(request.POST)
        form_lineas = LineasIngresoForm(request.POST, request.FILES, piezas_permitidas=piezas)
        # Se evaluan los cuatro (sin cortocircuito) para mostrar de una vez
        # todos los errores del formulario.
        valido = all(
            [
                form.is_valid(),
                form_vehiculo.is_valid(),
                form_categorias.is_valid(),
                form_lineas.is_valid(),
            ]
        )
        if valido:
            try:
                _entrada, avisos = registrar_ingreso(
                    entrada,
                    form_vehiculo.datos_vehiculo(),
                    form.cleaned_data["fecha"],
                    form_lineas.lineas,
                    request.user,
                    fotos_por_pieza=form_lineas.fotos,
                )
            except ValidationError as error:
                form_lineas.add_error(None, error)
            else:
                for aviso in avisos:
                    messages.warning(request, aviso)
                messages.success(request, mensaje_exito)
                return redirect("ingreso_detalle", pk=entrada.pk)
        cantidades = form_lineas.cantidades
        seleccionadas = {
            categoria.pk
            for categoria in form_categorias.cleaned_data.get("categorias", [])
        } if form_categorias.is_valid() else set()
    else:
        form = EntradaForm(instance=entrada)
        form_vehiculo = VehiculoIngresoForm(initial=_initial_vehiculo(entrada))
        form_categorias = CategoriasIngresoForm()
        form_lineas = None
        cantidades = cantidades_por_pieza(entrada) if entrada.pk else {}
        if entrada.pk:
            # Al editar no se pre-marca ninguna categoria: se ven solo las
            # piezas ya cargadas y el resto se agrega desde el modal.
            seleccionadas = set()
        else:
            seleccionadas = {
                pieza.categoria_id for pieza in piezas if cantidades.get(pieza.pk)
            }

    contexto = {
        "titulo": titulo,
        "entrada": entrada if entrada.pk else None,
        "es_edicion": bool(entrada.pk),
        "form": form,
        "form_vehiculo": form_vehiculo,
        "form_lineas": form_lineas,
        "grupos": _agrupar_por_categoria(piezas, cantidades, seleccionadas),
        "marcas": Marca.objects.order_by("nombre_marca"),
        "modelos": Modelo.objects.order_by("nombre_modelo")
        .values_list("nombre_modelo", flat=True)
        .distinct(),
        "tipos": TipoVehiculo.objects.order_by("nombre_tipo"),
    }
    return render(request, "inventario/ingresos/entrada_form.html", contexto)


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------
@permiso_requerido("ingresos", "ver")
def ingresos_lista(request):
    ingresos = ingresos_filtrados(request)
    contexto = {
        "ingresos": ingresos,
        "desde": request.GET.get("desde", ""),
        "hasta": request.GET.get("hasta", ""),
        "total_unidades": ingresos.aggregate(total=Sum("detalles__cantidad"))["total"]
        or 0,
        "puede_crear": tiene_permiso(request.user, "ingresos", "crear"),
        "puede_editar": tiene_permiso(request.user, "ingresos", "editar"),
        "puede_eliminar": tiene_permiso(request.user, "ingresos", "eliminar"),
    }
    return render(request, "inventario/ingresos/entrada_list.html", contexto)


@permiso_requerido("ingresos", "crear")
def ingreso_crear(request):
    return _procesar_formulario(
        request,
        Entrada(),
        "Nuevo ingreso de inventario",
        "Ingreso registrado correctamente.",
    )


@permiso_requerido("ingresos", "editar")
def ingreso_editar(request, pk):
    entrada = get_object_or_404(
        Entrada.objects.select_related("vehiculo__modelo__marca"), pk=pk
    )
    return _procesar_formulario(
        request,
        entrada,
        f"Editar ingreso #{entrada.pk}",
        "Ingreso actualizado correctamente.",
    )


@permiso_requerido("ingresos", "ver")
def ingreso_detalle(request, pk):
    entrada = get_object_or_404(
        Entrada.objects.select_related(
            "vehiculo__modelo__marca", "vehiculo__tipo_vehiculo", "usuario"
        ),
        pk=pk,
    )
    detalles = entrada.detalles.select_related("producto__categoria").order_by(
        "producto__categoria__nombre_categoria", "producto__nombre"
    )
    contexto = {
        "entrada": entrada,
        "detalles": detalles,
        "total_unidades": sum(detalle.cantidad for detalle in detalles),
        "puede_editar": tiene_permiso(request.user, "ingresos", "editar"),
        "puede_eliminar": tiene_permiso(request.user, "ingresos", "eliminar"),
    }
    return render(request, "inventario/ingresos/entrada_detalle.html", contexto)


@permiso_requerido("ingresos", "eliminar")
def ingreso_eliminar(request, pk):
    entrada = get_object_or_404(
        Entrada.objects.select_related("vehiculo__modelo__marca"), pk=pk
    )
    detalles = entrada.detalles.select_related("producto")
    if request.method == "POST":
        try:
            eliminar_ingreso(entrada)
        except ValidationError as error:
            for mensaje in error.messages:
                messages.error(request, mensaje)
        else:
            messages.success(request, "Ingreso eliminado correctamente.")
            return redirect("ingresos")
    contexto = {
        "entrada": entrada,
        "detalles": detalles,
        "total_unidades": sum(detalle.cantidad for detalle in detalles),
    }
    return render(request, "inventario/ingresos/entrada_confirm_delete.html", contexto)
