from django.contrib.auth import views as auth_views
from django.urls import include, path

from inventario.forms import LoginForm
from inventario.views import (
    ConceptoGastoCreateView,
    ConceptoGastoDeleteView,
    ConceptoGastoListView,
    ConceptoGastoUpdateView,
    GastoCreateView,
    GastoDeleteView,
    GastoListView,
    GastoUpdateView,
    catalogo_eliminar,
    catalogo_form,
    catalogo_lista,
    dashboard,
    gasto_comprobante,
    gasto_comprobante_pdf,
    gastos_exportar_excel,
    gastos_exportar_pdf,
    rol_crear,
    rol_editar,
    roles_lista,
    usuario_crear,
    usuario_editar,
    usuarios_lista,
)

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('inventario/', include('inventario.visualizaciones.urls')),
    path('gastos/', GastoListView.as_view(), name='gastos'),
    path('gastos/nuevo/', GastoCreateView.as_view(), name='gasto_crear'),
    path('gastos/<int:pk>/editar/', GastoUpdateView.as_view(), name='gasto_editar'),
    path('gastos/<int:pk>/eliminar/', GastoDeleteView.as_view(), name='gasto_eliminar'),
    path('gastos/<int:pk>/comprobante/', gasto_comprobante, name='gasto_comprobante'),
    path('gastos/<int:pk>/comprobante/pdf/', gasto_comprobante_pdf, name='gasto_comprobante_pdf'),
    path('gastos/exportar/pdf/', gastos_exportar_pdf, name='gastos_exportar_pdf'),
    path('gastos/exportar/excel/', gastos_exportar_excel, name='gastos_exportar_excel'),
    path('gastos/conceptos/', ConceptoGastoListView.as_view(), name='conceptos'),
    path('gastos/conceptos/nuevo/', ConceptoGastoCreateView.as_view(), name='concepto_crear'),
    path('gastos/conceptos/<int:pk>/editar/', ConceptoGastoUpdateView.as_view(), name='concepto_editar'),
    path('gastos/conceptos/<int:pk>/eliminar/', ConceptoGastoDeleteView.as_view(), name='concepto_eliminar'),
    path('reportes/', include('inventario.reportes.urls')),

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
