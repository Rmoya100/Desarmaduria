from django.urls import path

from . import views

urlpatterns = [
    path("", views.ventas, name="reportes"),
    path("ventas/exportar/pdf/", views.ventas_exportar_pdf, name="reporte_ventas_pdf"),
    path("ventas/exportar/excel/", views.ventas_exportar_excel, name="reporte_ventas_excel"),

    path("utilidad/", views.utilidad, name="reporte_utilidad"),
    path("utilidad/exportar/pdf/", views.utilidad_exportar_pdf, name="reporte_utilidad_pdf"),
    path("utilidad/exportar/excel/", views.utilidad_exportar_excel, name="reporte_utilidad_excel"),

    path("rotacion/", views.rotacion, name="reporte_rotacion"),
    path("rotacion/exportar/pdf/", views.rotacion_exportar_pdf, name="reporte_rotacion_pdf"),
    path("rotacion/exportar/excel/", views.rotacion_exportar_excel, name="reporte_rotacion_excel"),

    path("caja/", views.caja, name="reporte_caja"),
    path("caja/exportar/pdf/", views.caja_exportar_pdf, name="reporte_caja_pdf"),
    path("caja/exportar/excel/", views.caja_exportar_excel, name="reporte_caja_excel"),
    path("caja/saldo-inicial/", views.saldo_inicial_editar, name="saldo_inicial_editar"),

    path("vehiculos/", views.vehiculos, name="reporte_vehiculos"),
    path("vehiculos/exportar/pdf/", views.vehiculos_exportar_pdf, name="reporte_vehiculos_pdf"),
    path("vehiculos/exportar/excel/", views.vehiculos_exportar_excel, name="reporte_vehiculos_excel"),
]
