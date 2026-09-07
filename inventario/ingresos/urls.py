from django.urls import path

from .views import (
    ingreso_crear,
    ingreso_detalle,
    ingreso_editar,
    ingreso_eliminar,
    ingresos_lista,
)


urlpatterns = [
    path("", ingresos_lista, name="ingresos"),
    path("nuevo/", ingreso_crear, name="ingreso_crear"),
    path("<int:pk>/", ingreso_detalle, name="ingreso_detalle"),
    path("<int:pk>/editar/", ingreso_editar, name="ingreso_editar"),
    path("<int:pk>/eliminar/", ingreso_eliminar, name="ingreso_eliminar"),
]
