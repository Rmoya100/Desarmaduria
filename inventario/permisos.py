"""Chequeo de permisos de negocio (Rol -> RolPermiso -> Permiso).

Distinto del sistema de permisos nativo de Django (`user_permissions` /
`groups`), que no se usa en este proyecto: aqui el acceso se decide por el
`rol` de negocio del `Usuario` (ver `inventario.models.Rol/Permiso/RolPermiso`).
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def tiene_permiso(user, modulo, accion="ver"):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.rol_id:
        return False
    return user.rol.rol_permisos.filter(
        permiso__modulo=modulo, permiso__nombre_permiso=accion
    ).exists()


def permiso_requerido(modulo, accion="ver"):
    """Decorador para vistas cuyo modulo/accion se conoce en tiempo de
    definicion. Exige login (redirige) y luego el permiso (403)."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not tiene_permiso(request.user, modulo, accion):
                raise PermissionDenied(
                    f"No tienes permiso para '{accion}' en '{modulo}'."
                )
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
