from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Producto
from ..permisos import permiso_requerido, tiene_permiso
from ..servicios.catalogo import importar_catalogo
from ..servicios.inventario import productos_con_stock, valor_inventario
from .forms import (
    ImportarCatalogoForm,
    InventarioFiltroForm,
    ProductoFiltroForm,
    ProductoForm,
)

# Clave donde se guarda la vista previa entre el paso 1 (subir) y el paso 2
# (confirmar). Se almacenan los datos ya interpretados, nunca el archivo.
SESION_IMPORTACION = "importacion_catalogo"


def _productos_filtrados(request):
    form = InventarioFiltroForm(request.GET or None)
    productos = productos_con_stock()

    if form.is_valid():
        datos = form.cleaned_data
        if datos["categoria"]:
            productos = productos.filter(categoria=datos["categoria"])
        if datos["marca"]:
            productos = productos.filter(vehiculo__modelo__marca=datos["marca"])
        if datos["modelo"]:
            productos = productos.filter(vehiculo__modelo=datos["modelo"])
        if datos["estado"] == "disponible":
            productos = productos.filter(stock_disponible__gt=0)
        elif datos["estado"] == "agotado":
            productos = productos.filter(stock_disponible__lte=0)
    return form, productos


@login_required
def inventario_visualizacion(request):
    form, productos = _productos_filtrados(request)

    resumen = productos.aggregate(
        productos=Sum("stock_disponible"),
        unidades_vendidas=Sum("total_vendido"),
        unidades_ingresadas=Sum("total_entradas"),
    )
    productos = list(productos)
    disponibles = sum(p.stock_disponible for p in productos)
    contexto = {
        "form": form,
        "productos": productos,
        "resumen": resumen,
        "valor_inventario": valor_inventario(productos),
        "metricas": [
            {"titulo": "Unidades disponibles", "valor": disponibles, "detalle": "Stock actual"},
            {"titulo": "Productos con stock", "valor": sum(p.stock_disponible > 0 for p in productos), "detalle": "Referencias activas"},
            {"titulo": "Unidades vendidas", "valor": sum(p.total_vendido for p in productos), "detalle": "Salidas registradas"},
        ],
    }
    return render(request, "inventario/visualizaciones/inventario.html", contexto)


@login_required
def inventario_valorizado(request):
    form, productos = _productos_filtrados(request)
    productos = list(productos)
    for producto in productos:
        producto.valor_stock = (producto.costo or 0) * producto.stock_disponible
    contexto = {
        "form": form,
        "productos": productos,
        "valor_inventario": valor_inventario(productos),
        "unidades_disponibles": sum(p.stock_disponible for p in productos),
        "productos_con_stock": sum(1 for p in productos if p.stock_disponible > 0),
        "metricas": [
            {"titulo": "Unidades disponibles", "valor": sum(p.stock_disponible for p in productos), "detalle": "Stock actual"},
            {"titulo": "Valor del inventario", "valor": f"${valor_inventario(productos):,.0f}", "detalle": "A costo de adquisición"},
            {"titulo": "Unidades vendidas", "valor": sum(p.total_vendido for p in productos), "detalle": "Salidas registradas"},
            {"titulo": "Productos con stock", "valor": sum(p.stock_disponible > 0 for p in productos), "detalle": "Referencias activas"},
        ],
    }
    return render(
        request, "inventario/visualizaciones/inventario_valorizado.html", contexto
    )


@login_required
def productos_lista(request):
    filtro = ProductoFiltroForm(request.GET or None)
    productos = Producto.objects.filter(fecha_eliminacion__isnull=True).select_related(
        "categoria", "vehiculo__modelo__marca"
    )
    if filtro.is_valid():
        datos = filtro.cleaned_data
        if datos["nombre"]:
            productos = productos.filter(nombre__icontains=datos["nombre"])
        if datos["categoria"]:
            productos = productos.filter(
                categoria__nombre_categoria__icontains=datos["categoria"]
            )
        if datos["vehiculo"]:
            busqueda_vehiculo = datos["vehiculo"]
            productos = productos.filter(
                Q(vehiculo__patente__icontains=busqueda_vehiculo)
                | Q(vehiculo__modelo__nombre_modelo__icontains=busqueda_vehiculo)
                | Q(vehiculo__modelo__marca__nombre_marca__icontains=busqueda_vehiculo)
            )
        orden = request.GET.get("orden", "nombre")
        if orden not in ("nombre", "-nombre", "categoria", "-categoria", "costo", "-costo"):
            orden = "nombre"
        if orden in ("categoria", "-categoria"):
            orden = f"{orden}__nombre_categoria"
        productos = productos.order_by(orden, "nombre")
    else:
        productos = productos.order_by("nombre")
    return render(
        request,
        "inventario/visualizaciones/productos_lista.html",
        {
            "productos": productos,
            "filtro": filtro,
            "orden_actual": request.GET.get("orden", "nombre"),
            "form": ProductoForm(),
            "puede_importar": tiene_permiso(request.user, "productos", "importar"),
        },
    )


@login_required
def producto_crear(request):
    if request.method != "POST":
        return redirect("productos_lista")
    form = ProductoForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Producto creado correctamente.")
        return redirect("productos_lista")
    productos = Producto.objects.filter(fecha_eliminacion__isnull=True).select_related(
        "categoria", "vehiculo__modelo__marca"
    ).order_by("nombre")
    return render(
        request,
        "inventario/visualizaciones/productos_lista.html",
        {
            "productos": productos,
            "filtro": ProductoFiltroForm(request.GET or None),
            "form": form,
            "abrir_modal": True,
        },
    )


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto actualizado correctamente.")
        return redirect("productos_lista")
    plantilla = "inventario/visualizaciones/producto_form.html"
    if request.GET.get("partial"):
        plantilla = "inventario/visualizaciones/producto_form_modal.html"
    return render(request, plantilla, {"form": form, "producto": producto})


@permiso_requerido("productos", "importar")
def productos_importar(request):
    """Carga masiva del catalogo en dos pasos: subir y confirmar.

    Entre ambos, la vista previa vive en la sesion (los pares categoria/pieza
    ya interpretados, no el archivo), para que el operador vea que se va a
    crear sin tener que subir la planilla dos veces.
    """
    form = ImportarCatalogoForm()
    previsualizacion = None

    if request.method == "POST" and request.POST.get("confirmar") == "1":
        datos = request.session.get(SESION_IMPORTACION)
        if not datos:
            messages.error(
                request,
                "La vista previa expiró. Vuelve a subir la planilla.",
            )
            return redirect("productos_importar")
        piezas = [(categoria, nombre) for categoria, nombre in datos["piezas"]]
        resumen = importar_catalogo(piezas)
        request.session.pop(SESION_IMPORTACION, None)
        messages.success(
            request,
            f"Importación completada: {resumen.piezas_creadas} piezas nuevas y "
            f"{resumen.categorias_creadas} categorías nuevas "
            f"({resumen.piezas_existentes} ya existían).",
        )
        return redirect("productos_lista")

    if request.method == "POST":
        form = ImportarCatalogoForm(request.POST, request.FILES)
        if form.is_valid():
            lectura = form.lectura
            resumen = importar_catalogo(lectura.piezas, simular=True)
            request.session[SESION_IMPORTACION] = {
                "archivo": form.cleaned_data["archivo"].name,
                "piezas": [list(pieza) for pieza in lectura.piezas],
            }
            previsualizacion = {
                "archivo": form.cleaned_data["archivo"].name,
                "lectura": lectura,
                "resumen": resumen,
            }

    return render(
        request,
        "inventario/visualizaciones/importar_catalogo.html",
        {"form": form, "previsualizacion": previsualizacion},
    )


@login_required
def producto_eliminar(request, pk):
    if request.method != "POST":
        return redirect("productos_lista")
    if request.POST.get("confirmar_eliminacion") != "1":
        messages.error(request, "Debes confirmar la eliminación del producto.")
        return redirect("productos_lista")
    producto = get_object_or_404(
        Producto, pk=pk, fecha_eliminacion__isnull=True
    )
    producto.eliminar(request.user)
    messages.success(request, "Producto eliminado correctamente.")
    return redirect("productos_lista")