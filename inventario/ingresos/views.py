from django.contrib import messages
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import DetalleEntrada, Entrada, Marca, Modelo, Producto, Vehiculo
from ..permisos import permiso_requerido
from .forms import IngresoCabeceraForm, IngresoLineaForm

IngresoFormSet = formset_factory(IngresoLineaForm, extra=0)


def _productos_activos():
    return (
        Producto.objects.filter(fecha_eliminacion__isnull=True)
        .select_related("categoria", "vehiculo__modelo__marca")
        .order_by("categoria__nombre_categoria", "nombre")
    )


def _initial_de(producto):
    inicial = {
        "producto": producto.pk,
        "costo": producto.costo,
        "precio_venta": producto.precio_venta,
    }
    if producto.vehiculo_id:
        veh = producto.vehiculo
        inicial.update(
            marca=veh.modelo.marca.nombre_marca,
            modelo=veh.modelo.nombre_modelo,
            anio=veh.anio,
        )
    return inicial


def _asignar_vehiculo(datos):
    marca, _ = Marca.objects.get_or_create(nombre_marca=datos["marca"].strip())
    modelo, _ = Modelo.objects.get_or_create(
        marca=marca, nombre_modelo=datos["modelo"].strip()
    )
    vehiculo, _ = Vehiculo.objects.get_or_create(modelo=modelo, anio=datos["anio"])
    return vehiculo


def _guardar_ingreso(usuario, fecha, lineas):
    with transaction.atomic():
        entrada = Entrada.objects.create(fecha=fecha, usuario=usuario)
        for datos in lineas:
            producto = datos["producto"]
            DetalleEntrada.objects.create(
                entrada=entrada, producto=producto, cantidad=datos["cantidad"]
            )
            campos = []
            if datos.get("costo") is not None:
                producto.costo = datos["costo"]
                campos.append("costo")
            if datos.get("precio_venta") is not None:
                producto.precio_venta = datos["precio_venta"]
                campos.append("precio_venta")
            if datos.get("marca"):
                producto.vehiculo = _asignar_vehiculo(datos)
                campos.append("vehiculo")
            if campos:
                producto.save(update_fields=campos)
    return entrada


@permiso_requerido("ingresos", "crear")
def ingreso_crear(request):
    productos = list(_productos_activos())

    if request.method == "POST":
        cabecera = IngresoCabeceraForm(request.POST)
        formset = IngresoFormSet(request.POST)
        if cabecera.is_valid() and formset.is_valid():
            lineas = [
                form.cleaned_data
                for form in formset.forms
                if form.cleaned_data.get("cantidad")
            ]
            if not lineas:
                messages.error(
                    request, "Ingresa la cantidad recibida de al menos un producto."
                )
            else:
                _guardar_ingreso(request.user, cabecera.cleaned_data["fecha"], lineas)
                messages.success(
                    request,
                    f"Ingreso registrado: {len(lineas)} producto(s) actualizado(s).",
                )
                return redirect("ingresos")
    else:
        cabecera = IngresoCabeceraForm(initial={"fecha": timezone.localdate()})
        formset = IngresoFormSet(initial=[_initial_de(p) for p in productos])

    productos_por_id = {p.pk: p for p in productos}
    filas = []
    for form in formset.forms:
        pk = form["producto"].value()
        filas.append((form, productos_por_id.get(int(pk)) if pk else None))

    categorias = sorted(
        {p.categoria for p in productos}, key=lambda c: c.nombre_categoria
    )
    return render(
        request,
        "inventario/ingresos/ingreso_form.html",
        {
            "cabecera": cabecera,
            "formset": formset,
            "filas": filas,
            "categorias": categorias,
        },
    )
