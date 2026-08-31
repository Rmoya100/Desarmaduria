from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import FormaPagoForm, RolForm, TipoDocumentoForm, UsuarioForm
from .models import FormaPago, Rol, TipoDocumento, Usuario
from .permisos import permiso_requerido, tiene_permiso


@login_required
def en_construccion(request, titulo):
    return render(request, "inventario/en_construccion.html", {"titulo": titulo})


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


@login_required
def catalogo_lista(request, clave):
    if not tiene_permiso(request.user, clave, "ver"):
        raise PermissionDenied(f"No tienes permiso para 'ver' en '{clave}'.")
    cfg = CATALOGOS[clave]
    items = cfg["model"].objects.order_by("pk")
    contexto = {
        "items": items,
        "cfg": cfg,
        "clave": clave,
        "puede_crear": tiene_permiso(request.user, clave, "crear"),
        "puede_editar": tiene_permiso(request.user, clave, "editar"),
        "puede_eliminar": tiene_permiso(request.user, clave, "eliminar"),
    }
    return render(request, "inventario/catalogo_lista.html", contexto)


@login_required
def catalogo_form(request, clave, pk=None):
    accion = "editar" if pk else "crear"
    if not tiene_permiso(request.user, clave, accion):
        raise PermissionDenied(f"No tienes permiso para '{accion}' en '{clave}'.")
    cfg = CATALOGOS[clave]
    instancia = get_object_or_404(cfg["model"], pk=pk) if pk else None
    form = cfg["form"](request.POST or None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Guardado correctamente.")
        return redirect(cfg["url_lista"])
    contexto = {
        "form": form,
        "titulo": f"Editar {cfg['titulo_singular']}" if instancia else cfg["nuevo"],
        "cancelar_url": reverse(cfg["url_lista"]),
        "clave": clave,
    }
    return render(request, "inventario/catalogo_form.html", contexto)


@login_required
def catalogo_eliminar(request, clave, pk):
    if not tiene_permiso(request.user, clave, "eliminar"):
        raise PermissionDenied(f"No tienes permiso para 'eliminar' en '{clave}'.")
    cfg = CATALOGOS[clave]
    instancia = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        try:
            instancia.delete()
            messages.success(request, "Eliminado correctamente.")
        except ProtectedError:
            messages.error(
                request, "No se puede eliminar: está en uso por otros registros."
            )
        return redirect(cfg["url_lista"])
    contexto = {"instancia": instancia, "cfg": cfg, "clave": clave}
    return render(request, "inventario/catalogo_eliminar.html", contexto)
