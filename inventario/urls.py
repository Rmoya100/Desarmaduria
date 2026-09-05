from django.urls import path

from inventario.views import (
    ConceptoGastoCreateView,
    ConceptoGastoDeleteView,
    ConceptoGastoListView,
    ConceptoGastoUpdateView,
    GastoCreateView,
    GastoDeleteView,
    GastoListView,
    GastoUpdateView,
    en_construccion,
    gasto_comprobante,
    gasto_comprobante_pdf,
    gastos_exportar_excel,
    gastos_exportar_pdf,
)

urlpatterns = [
    path('', en_construccion, {'titulo': 'Dashboard'}, name='dashboard'),
    path('inventario/', en_construccion, {'titulo': 'Inventario'}, name='inventario'),
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
    path('reportes/', en_construccion, {'titulo': 'Reportes'}, name='reportes'),
    path('usuarios/', en_construccion, {'titulo': 'Usuarios'}, name='usuarios'),
]
