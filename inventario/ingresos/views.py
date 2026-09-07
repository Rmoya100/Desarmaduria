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


def _marca_modelo(datos):
    marca, _ = Marca.objects.get_or_create(nombre_marca=datos["marca"].strip())
    modelo, _ = Modelo.objects.get_or_create(
        marca=marca, nombre_modelo=datos["modelo"].strip()
    )
    return modelo


def _vehiculo_de_fila(datos):
    modelo = _marca_modelo(datos)
    vehiculo, _ = Vehiculo.objects.get_or_create(modelo=modelo, anio=datos["anio"])
    return vehiculo


def _vehiculo_donante(datos):
    modelo = _marca_modelo(datos)
    patente = (datos.get("patente") or "").strip() or None
    if patente:
        existente = Vehiculo.objects.filter(patente=patente).first()
        if existente:
            return existente
    vehiculo, creado = Vehiculo.objects.get_or_create(
        modelo=modelo, anio=datos["anio"], defaults={"patente": patente}
    )
    if patente and not creado and not vehiculo.patente:
        vehiculo.patente = patente
        vehiculo.save(update_fields=["patente"])
    return vehiculo


def _guardar_ingreso(usuario, cabecera, lineas):
    with transaction.atomic():
        # `fecha` es la fecha de negocio del ingreso; se toma del sistema al
        # guardar. `fecha_registro` (auto_now_add) guarda el timestamp exacto.
        entrada = Entrada.objects.create(
            fecha=timezone.localdate(), usuario=usuario
        )

        vehiculo_donante = None
        if cabecera.get("marca"):
            vehiculo_donante = _vehiculo_donante(cabecera)
            entrada.vehiculo = vehiculo_donante
            entrada.save(update_fields=["vehiculo"])
        aplicar_donante = bool(
            vehiculo_donante and cabecera.get("asignar_a_productos")
        )

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
                producto.vehiculo = _vehiculo_de_fila(datos)
                campos.append("vehiculo")
            elif aplicar_donante:
                producto.vehiculo = vehiculo_donante
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
        if not (cabecera.is_valid() and formset.is_valid()):
            messages.error(
                request,
                "No se guardó el ingreso: revisa los datos marcados en rojo.",
            )
        else:
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
                _guardar_ingreso(request.user, cabecera.cleaned_data, lineas)
                messages.success(
                    request,
                    f"Ingreso registrado: {len(lineas)} producto(s) actualizado(s).",
                )
                return redirect("ingresos")
    else:
        cabecera = IngresoCabeceraForm()
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
