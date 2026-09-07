"""Estandariza a MAYUSCULAS las categorias y los nombres de producto.

Mismo criterio y misma seguridad que la 0008 (la colacion por defecto de
MySQL no distingue mayusculas, asi que normalizar no puede generar duplicados
en `categoria.nombreCategoria`). No se revierte: la capitalizacion original
no es recuperable y el estado normalizado es igualmente valido.
"""

from django.db import migrations


def normalizar(valor):
    if not valor:
        return valor
    return " ".join(str(valor).split()).upper()


def normalizar_existentes(apps, schema_editor):
    Categoria = apps.get_model("inventario", "Categoria")
    Producto = apps.get_model("inventario", "Producto")

    for categoria in Categoria.objects.all():
        nombre = normalizar(categoria.nombre_categoria)
        if nombre != categoria.nombre_categoria:
            categoria.nombre_categoria = nombre
            categoria.save(update_fields=["nombre_categoria"])

    for producto in Producto.objects.all():
        nombre = normalizar(producto.nombre)
        if nombre != producto.nombre:
            producto.nombre = nombre
            producto.save(update_fields=["nombre"])


class Migration(migrations.Migration):

    dependencies = [("inventario", "0009_seed_permisos_ingresos")]

    operations = [
        migrations.RunPython(normalizar_existentes, migrations.RunPython.noop)
    ]
