"""Restricciones transversales para roles de operacion acotada."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


class BodegaSoloIngresosMiddleware:
    """Limita el rol Bodega al flujo de consulta y creacion de ingresos.

    Los permisos siguen siendo la fuente de autorizacion de cada vista. Esta
    regla adicional evita que un usuario de Bodega entre a pantallas que aun
    son solo autenticadas, como el dashboard o reportes, mediante una URL
    escrita directamente.
    """

    rutas_permitidas = {"ingresos", "ingreso_crear", "ingreso_detalle", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not user.is_authenticated or user.is_superuser:
            return None
        if not user.rol_id or user.rol.nombre_rol.casefold() != "bodega":
            return None

        nombre_ruta = request.resolver_match.url_name
        if nombre_ruta == "dashboard":
            return redirect(reverse("ingresos"))
        if nombre_ruta not in self.rutas_permitidas:
            raise PermissionDenied("El rol Bodega solo puede acceder a Ingresos.")
        return None


class VendedorSoloInventarioMiddleware:
    """Limita el rol Vendedor a la visualizacion de inventario.

    Igual que `BodegaSoloIngresosMiddleware`: los permisos ("productos.ver")
    siguen siendo la fuente de autorizacion de cada vista. Esta regla evita
    que un usuario de Vendedor entre a pantallas que aun son solo
    autenticadas (gastos, reportes, dashboard) mediante una URL escrita
    directamente.
    """

    rutas_permitidas = {"inventario_visualizacion", "productos_lista", "consulta_ventas", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not user.is_authenticated or user.is_superuser:
            return None
        if not user.rol_id or user.rol.nombre_rol.casefold() != "vendedor":
            return None

        nombre_ruta = request.resolver_match.url_name
        if nombre_ruta == "dashboard":
            return redirect(reverse("inventario_visualizacion"))
        if nombre_ruta not in self.rutas_permitidas:
            raise PermissionDenied("El rol Vendedor solo puede ver el inventario.")
        return None
