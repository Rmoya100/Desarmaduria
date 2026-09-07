"""Estandariza a MAYUSCULAS los datos de vehiculo ya cargados.

Es seguro respecto de las restricciones UNIQUE: la colacion por defecto de
MySQL no distingue mayusculas de minusculas, de modo que no pueden coexistir
"Toyota" y "TOYOTA" en `marca.nombreMarca` y la normalizacion no genera
duplicados. No se revierte: no hay forma de recuperar la capitalizacion
original y el estado en mayusculas es igualmente valido.
"""

from django.db import migrations


def normalizar(valor):
    if not valor:
        return valor
    return " ".join(str(valor).split()).upper()


def normalizar_existentes(apps, schema_editor):
    Marca = apps.get_model("inventario", "Marca")
    Modelo = apps.get_model("inventario", "Modelo")
    Vehiculo = apps.get_model("inventario", "Vehiculo")

    for marca in Marca.objects.all():
        nombre = normalizar(marca.nombre_marca)
        if nombre != marca.nombre_marca:
            marca.nombre_marca = nombre
            marca.save(update_fields=["nombre_marca"])

    for modelo in Modelo.objects.all():
        nombre = normalizar(modelo.nombre_modelo)
        if nombre != modelo.nombre_modelo:
            modelo.nombre_modelo = nombre
            modelo.save(update_fields=["nombre_modelo"])

    for vehiculo in Vehiculo.objects.exclude(patente__isnull=True):
        patente = normalizar(vehiculo.patente) or None
        if patente != vehiculo.patente:
            vehiculo.patente = patente
            vehiculo.save(update_fields=["patente"])


class Migration(migrations.Migration):

    dependencies = [("inventario", "0007_tipo_vehiculo_y_rango_anios")]

    operations = [
        migrations.RunPython(normalizar_existentes, migrations.RunPython.noop)
    ]
