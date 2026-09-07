from django.contrib import messages
from django.db import transaction
from django.forms import BaseFormSet, formset_factory
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import DetalleEntrada, Entrada, Marca, Modelo, Producto, Vehiculo
from ..permisos import permiso_requerido, tiene_permiso
from .forms import IngresoCabeceraForm, IngresoLineaForm


class _IngresoBaseFormSet(BaseFormSet):
    """La tabla trae una fila por producto activo, pero el navegador solo
    envia las filas con cantidad (deshabilita el resto). Sin esto el formset
    exige que TODAS las filas —incluidas las vacias que nunca llegan— sean
    validas y el guardado falla sin mostrar ningun campo en rojo."""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.empty_permitted = True


IngresoFormSet = formset_factory(
    IngresoLineaForm, formset=_IngresoBaseFormSet, extra=0
)


def _productos_activos():
    return (
        Producto.objects.filter(fecha_eliminacion__isnull=True)
        .select_related("categoria")
        .order_by("categoria__nombre_categoria", "nombre")
    )


def _initial_de(producto):
    return {
        "producto": producto.pk,
        "costo": producto.costo,
        "precio_venta": producto.precio_venta,
    }


def _vehiculo_de_cabecera(datos):
    marca, _ = Marca.objects.get_or_create(nombre_marca=datos["marca"].strip())
    modelo, _ = Modelo.objects.get_or_create(
        marca=marca, nombre_modelo=datos["modelo"].strip()
    )
    tipo = (datos.get("tipo") or "").strip()
    vehiculo, creado = Vehiculo.objects.get_or_create(
        modelo=modelo, anio=datos["anio"], defaults={"tipo": tipo}
    )
    if tipo and not creado and vehiculo.tipo != tipo:
        vehiculo.tipo = tipo
        vehiculo.save(update_fields=["tipo"])
    return vehiculo


def _guardar_ingreso(usuario, cabecera, lineas):
    with transaction.atomic():
        vehiculo = _vehiculo_de_cabecera(cabecera)
        entrada = Entrada.objects.create(
            fecha=cabecera["fecha"], usuario=usuario, vehiculo=vehiculo
        )
        for datos in lineas:
            producto = datos["producto"]
            DetalleEntrada.objects.create(
                entrada=entrada, producto=producto, cantidad=datos["cantidad"]
            )
            campos = ["vehiculo"]
            producto.vehiculo = vehiculo
            if datos.get("costo") is not None:
                producto.costo = datos["costo"]
                campos.append("costo")
            if datos.get("precio_venta") is not None:
                producto.precio_venta = datos["precio_venta"]
                campos.append("precio_venta")
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
                    f"Ingreso registrado: {len(lineas)} producto(s).",
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
        {"cabecera": cabecera, "formset": formset, "filas": filas, "categorias": categorias},
    )


@permiso_requerido("ingresos", "ver")
def ingresos_lista(request):
    entradas = (
        Entrada.objects.select_related(
            "vehiculo__modelo__marca", "usuario"
        )
        .prefetch_related("detalles__producto__categoria")
        .order_by("-fecha", "-id_entrada")
    )

    desde = request.GET.get("desde") or ""
    hasta = request.GET.get("hasta") or ""
    if desde:
        entradas = entradas.filter(fecha__gte=desde)
    if hasta:
        entradas = entradas.filter(fecha__lte=hasta)

    filas = []
    for entrada in entradas:
        detalles = list(entrada.detalles.all())
        filas.append(
            {
                "entrada": entrada,
                "detalles": detalles,
                "unidades": sum(d.cantidad for d in detalles),
            }
        )

    return render(
        request,
        "inventario/ingresos/ingreso_list.html",
        {
            "filas": filas,
            "desde": desde,
            "hasta": hasta,
            "puede_crear": tiene_permiso(request.user, "ingresos", "crear"),
        },
    )
