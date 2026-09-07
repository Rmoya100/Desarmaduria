from django.urls import path

from . import views

urlpatterns = [
    path("", views.ingresos_lista, name="ingresos"),
    path("nuevo/", views.ingreso_crear, name="ingreso_crear"),
]
