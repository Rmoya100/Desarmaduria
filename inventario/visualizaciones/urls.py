from django.urls import path

from .views import (
    inventario_valorizado,
    inventario_visualizacion,
    producto_crear,
    producto_editar,
    producto_eliminar,
    productos_lista,
)


urlpatterns = [
    path("", inventario_visualizacion, name="inventario_visualizacion"),
    path("valorizado/", inventario_valorizado, name="inventario_valorizado"),
    path("productos/", productos_lista, name="productos_lista"),
    path("productos/nuevo/", producto_crear, name="producto_crear"),
    path("productos/<int:pk>/editar/", producto_editar, name="producto_editar"),
    path("productos/<int:pk>/eliminar/", producto_eliminar, name="producto_eliminar"),
]