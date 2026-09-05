from django.contrib.auth import views as auth_views
from django.urls import path

from inventario.forms import LoginForm
from inventario.views import (
    catalogo_eliminar,
    catalogo_form,
    catalogo_lista,
    en_construccion,
    rol_crear,
    rol_editar,
    roles_lista,
    usuario_crear,
    usuario_editar,
    usuarios_lista,
)

urlpatterns = [
    path('', en_construccion, {'titulo': 'Dashboard'}, name='dashboard'),
    path('inventario/', en_construccion, {'titulo': 'Inventario'}, name='inventario'),
    path('gastos/', en_construccion, {'titulo': 'Gastos'}, name='gastos'),
    path('reportes/', en_construccion, {'titulo': 'Reportes'}, name='reportes'),

    path(
        'login/',
        auth_views.LoginView.as_view(template_name='inventario/login.html', authentication_form=LoginForm),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('usuarios/', usuarios_lista, name='usuarios'),
    path('usuarios/nuevo/', usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', usuario_editar, name='usuario_editar'),

    path('usuarios/roles/', roles_lista, name='roles'),
    path('usuarios/roles/nuevo/', rol_crear, name='rol_crear'),
    path('usuarios/roles/<int:pk>/editar/', rol_editar, name='rol_editar'),

    path('usuarios/formas-pago/', catalogo_lista, {'clave': 'formas_pago'}, name='formas_pago'),
    path('usuarios/formas-pago/nueva/', catalogo_form, {'clave': 'formas_pago'}, name='formas_pago_crear'),
    path('usuarios/formas-pago/<int:pk>/editar/', catalogo_form, {'clave': 'formas_pago'}, name='formas_pago_editar'),
    path('usuarios/formas-pago/<int:pk>/eliminar/', catalogo_eliminar, {'clave': 'formas_pago'}, name='formas_pago_eliminar'),

    path('usuarios/documentos/', catalogo_lista, {'clave': 'documentos'}, name='documentos'),
    path('usuarios/documentos/nuevo/', catalogo_form, {'clave': 'documentos'}, name='documentos_crear'),
    path('usuarios/documentos/<int:pk>/editar/', catalogo_form, {'clave': 'documentos'}, name='documentos_editar'),
    path('usuarios/documentos/<int:pk>/eliminar/', catalogo_eliminar, {'clave': 'documentos'}, name='documentos_eliminar'),
]
