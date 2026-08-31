from django.urls import path

from inventario.views import en_construccion

urlpatterns = [
    path('', en_construccion, {'titulo': 'Dashboard'}, name='dashboard'),
    path('inventario/', en_construccion, {'titulo': 'Inventario'}, name='inventario'),
    path('gastos/', en_construccion, {'titulo': 'Gastos'}, name='gastos'),
    path('reportes/', en_construccion, {'titulo': 'Reportes'}, name='reportes'),
    path('usuarios/', en_construccion, {'titulo': 'Usuarios'}, name='usuarios'),
]
