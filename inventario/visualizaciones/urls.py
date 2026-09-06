from django.urls import path

from .views import (
    inventario_valorizado,
    inventario_visualizacion,
    producto_crear,
    producto_editar,
    producto_eliminar,
    productos_edicion_masiva,
    productos_exportar_excel,
    productos_importar,
    productos_lista,
)


urlpatterns = [
    path("", inventario_visualizacion, name="inventario_visualizacion"),
    path("valorizado/", inventario_valorizado, name="inventario_valorizado"),
    path("productos/", productos_lista, name="productos_lista"),
    path("productos/nuevo/", producto_crear, name="producto_crear"),
    path("productos/exportar/", productos_exportar_excel, name="productos_exportar_excel"),
    path("productos/importar/", productos_importar, name="productos_importar"),
    path("productos/edicion-masiva/", productos_edicion_masiva, name="productos_edicion_masiva"),
    path("productos/<int:pk>/editar/", producto_editar, name="producto_editar"),
    path("productos/<int:pk>/eliminar/", producto_eliminar, name="producto_eliminar"),
]
