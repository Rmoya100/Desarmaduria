from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, ExpressionWrapper, F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import FormaPagoForm, RolForm, TipoDocumentoForm, UsuarioForm
from .models import (DetalleEntrada,DetalleVenta,FormaPago,Gasto,
    Producto,Rol,TipoDocumento,Usuario,Vehiculo,Venta,)
from .permisos import permiso_requerido, tiene_permiso

# Bajo este umbral (entradas - ventas) un producto se marca "bajo stock" en el
# dashboard. No existe un campo de stock minimo en el schema original, asi
# que es un valor fijo, ajustable aqui si el negocio define uno propio.
UMBRAL_BAJO_STOCK = 5


@login_required
def en_construccion(request, titulo):
    return render(request, "inventario/en_construccion.html", {"titulo": titulo})


@login_required
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    ventas_mes = Venta.objects.filter(fecha_venta__gte=inicio_mes, fecha_venta__lte=hoy)
    gastos_mes = Gasto.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy)

    total_ventas_mes = DetalleVenta.objects.filter(venta__in=ventas_mes).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("cantidad") * F("precio"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )["total"] or Decimal("0")
    total_gastos_mes = gastos_mes.aggregate(total=Sum("monto"))["total"] or Decimal("0")

    # Sumas por separado (no un .annotate() combinado): sumar dos relaciones
    # inversas distintas (entradas y ventas) en la misma anotacion duplica
    # filas por el cruce de joins y da totales inflados.
    entradas_por_producto = dict(
        DetalleEntrada.objects.values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )
    ventas_por_producto = dict(
        DetalleVenta.objects.values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )
    productos_bajo_stock = sorted(
        (
            {"producto": producto, "stock": entradas_por_producto.get(producto.pk, 0) - ventas_por_producto.get(producto.pk, 0)}
            for producto in Producto.objects.select_related("categoria")
        ),
        key=lambda item: item["stock"],
    )
    productos_bajo_stock = [
        item for item in productos_bajo_stock if item["stock"] <= UMBRAL_BAJO_STOCK
    ][:8]

    top_productos = (
        DetalleVenta.objects.values("producto__nombre")
        .annotate(cantidad_total=Sum("cantidad"))
        .order_by("-cantidad_total")[:5]
    )

    contexto = {
        "total_ventas_mes": total_ventas_mes,
        "cantidad_ventas_mes": ventas_mes.count(),
        "total_gastos_mes": total_gastos_mes,
        "cantidad_gastos_mes": gastos_mes.count(),
        "utilidad_mes": total_ventas_mes - total_gastos_mes,
        "total_productos": Producto.objects.count(),
        "total_vehiculos": Vehiculo.objects.count(),
        "umbral_bajo_stock": UMBRAL_BAJO_STOCK,
        "productos_bajo_stock": productos_bajo_stock,
        "top_productos": top_productos,
        "ventas_recientes": Venta.objects.select_related(
            "tipo_documento", "forma_pago", "usuario"
        ).order_by("-fecha_venta", "-id_venta")[:5],
        "gastos_recientes": Gasto.objects.select_related("concepto", "usuario").order_by(
            "-fecha", "-id_gasto"
        )[:5],
    }
    return render(request, "inventario/dashboard.html", contexto)


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
@permiso_requerido("usuarios", "ver")
def usuarios_lista(request):
    usuarios = Usuario.objects.select_related("rol").order_by("username")
    contexto = {
        "usuarios": usuarios,
        "puede_crear": tiene_permiso(request.user, "usuarios", "crear"),
        "puede_editar": tiene_permiso(request.user, "usuarios", "editar"),
    }
    return render(request, "inventario/usuarios_lista.html", contexto)


@permiso_requerido("usuarios", "crear")
def usuario_crear(request):
    form = UsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario creado correctamente.")
        return redirect("usuarios")
    contexto = {"form": form, "titulo": "Nuevo usuario", "cancelar_url": reverse("usuarios")}
    return render(request, "inventario/usuario_form.html", contexto)


@permiso_requerido("usuarios", "editar")
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Usuario actualizado correctamente.")
        return redirect("usuarios")
    contexto = {"form": form, "titulo": "Editar usuario", "cancelar_url": reverse("usuarios")}
    return render(request, "inventario/usuario_form.html", contexto)


# ---------------------------------------------------------------------------
# Roles y permisos
# ---------------------------------------------------------------------------
@permiso_requerido("roles", "ver")
def roles_lista(request):
    roles = Rol.objects.prefetch_related("rol_permisos__permiso").order_by("nombre_rol")
    contexto = {
        "roles": roles,
        "puede_crear": tiene_permiso(request.user, "roles", "crear"),
        "puede_editar": tiene_permiso(request.user, "roles", "editar"),
    }
    return render(request, "inventario/roles_lista.html", contexto)


@permiso_requerido("roles", "crear")
def rol_crear(request):
    form = RolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Rol creado correctamente.")
        return redirect("roles")
    contexto = {"form": form, "titulo": "Nuevo rol", "cancelar_url": reverse("roles")}
    return render(request, "inventario/rol_form.html", contexto)


@permiso_requerido("roles", "editar")
def rol_editar(request, pk):
    rol = get_object_or_404(Rol, pk=pk)
    form = RolForm(request.POST or None, instance=rol)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Rol actualizado correctamente.")
        return redirect("roles")
    contexto = {"form": form, "titulo": "Editar rol", "cancelar_url": reverse("roles")}
    return render(request, "inventario/rol_form.html", contexto)


# ---------------------------------------------------------------------------
# Catalogos simples (Formas de pago / Tipos de documento)
#
# Misma forma exacta (un solo campo de texto unico): se comparte la vista,
# parametrizada por `clave` (fijo por URL, nunca viene del usuario).
# ---------------------------------------------------------------------------
CATALOGOS = {
    "formas_pago": {
        "model": FormaPago,
        "form": FormaPagoForm,
        "titulo": "Formas de pago",
        "titulo_singular": "forma de pago",
        "nuevo": "Nueva forma de pago",
        "url_lista": "formas_pago",
        "url_crear": "formas_pago_crear",
        "url_editar": "formas_pago_editar",
        "url_eliminar": "formas_pago_eliminar",
    },
    "documentos": {
        "model": TipoDocumento,
        "form": TipoDocumentoForm,
        "titulo": "Tipos de documento",
        "titulo_singular": "tipo de documento",
        "nuevo": "Nuevo tipo de documento",
        "url_lista": "documentos",
        "url_crear": "documentos_crear",
        "url_editar": "documentos_editar",
        "url_eliminar": "documentos_eliminar",
    },
}

    # Formato numerico de Excel (no texto): separa miles/decimales segun el
    # local del Excel que lo abra, y se puede seguir sumando/ordenado.
    for fila in ws.iter_rows(min_row=2, min_col=4, max_col=4):
        for celda in fila:
            celda.number_format = "#,##0.00"

    anchos = {"A": 12, "B": 20, "C": 16, "D": 14, "E": 12, "F": 16, "G": 30, "H": 16}
    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="gastos.xlsx"'
    wb.save(response)
    return response


class GastoFormMixin:
    model = Gasto
    form_class = GastoForm
    template_name = "inventario/gasto_form.html"
    success_url = reverse_lazy("gastos")


class GastoCreateView(GastoFormMixin, CreateView):
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Gasto registrado correctamente.")
        return super().form_valid(form)


class GastoUpdateView(GastoFormMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, "Gasto actualizado correctamente.")
        return super().form_valid(form)


class GastoDeleteView(DeleteView):
    model = Gasto
    success_url = reverse_lazy("gastos")

    def form_valid(self, form):
        messages.success(self.request, "Gasto eliminado correctamente.")
        return super().form_valid(form)


def gasto_comprobante(request, pk):
    gasto = get_object_or_404(
        Gasto.objects.select_related("concepto", "forma_pago", "usuario", "tipo_documento"), pk=pk
    )
    return render(request, "inventario/gasto_comprobante.html", {"gasto": gasto})


def gasto_comprobante_pdf(request, pk):
    gasto = get_object_or_404(
        Gasto.objects.select_related("concepto", "forma_pago", "usuario", "tipo_documento"), pk=pk
    )
    response = HttpResponse(
        gasto_comprobante_pdf_bytes(gasto), content_type="application/pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="comprobante_gasto_{gasto.pk}.pdf"'
    return response


class ConceptoGastoListView(ListView):
    model = ConceptoGasto
    ordering = "nombre_gasto"
    context_object_name = "conceptos"
    template_name = "inventario/concepto_list.html"


class ConceptoGastoFormMixin:
    model = ConceptoGasto
    form_class = ConceptoGastoForm
    template_name = "inventario/concepto_form.html"
    success_url = reverse_lazy("conceptos")


class ConceptoGastoCreateView(ConceptoGastoFormMixin, CreateView):
    def form_valid(self, form):
        messages.success(self.request, "Concepto registrado correctamente.")
        return super().form_valid(form)


class ConceptoGastoUpdateView(ConceptoGastoFormMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, "Concepto actualizado correctamente.")
        return super().form_valid(form)


class ConceptoGastoDeleteView(DeleteView):
    model = ConceptoGasto
    template_name = "inventario/concepto_confirm_delete.html"
    success_url = reverse_lazy("conceptos")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar: hay gastos registrados con ese concepto.",
            )
            return self.get(self.request, *self.args, **self.kwargs)
        messages.success(self.request, "Concepto eliminado correctamente.")
        return response
