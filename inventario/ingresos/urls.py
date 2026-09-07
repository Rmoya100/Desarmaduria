from django.urls import path

from . import views

urlpatterns = [
    path("", views.ingreso_crear, name="ingresos"),
]
