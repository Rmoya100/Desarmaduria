# Migracion de datos: por cada Producto con `foto` no vacio, crea la fila
# ProductoFoto correspondiente (es_principal=True, orden=0) apuntando al
# MISMO archivo ya guardado en disco -- no se reconvierte ni se mueve nada,
# para que la migracion sea rapida y reversible (ver docs/analisis_fotos_
# productos.md, seccion 10, paso 2).
from django.db import migrations


def migrar_fotos(apps, schema_editor):
    Producto = apps.get_model("inventario", "Producto")
    ProductoFoto = apps.get_model("inventario", "ProductoFoto")

    productos = Producto.objects.exclude(foto="").exclude(foto__isnull=True)
    ProductoFoto.objects.bulk_create(
        ProductoFoto(producto=producto, imagen=producto.foto.name, es_principal=True, orden=0)
        for producto in productos.only("id_producto", "foto")
    )


def revertir_migracion(apps, schema_editor):
    ProductoFoto = apps.get_model("inventario", "ProductoFoto")
    ProductoFoto.objects.filter(orden=0, es_principal=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0014_productofoto"),
    ]

    operations = [
        migrations.RunPython(migrar_fotos, revertir_migracion),
    ]
