from django.db import migrations


PERMISOS_BODEGA = (("ingresos", "ver"), ("ingresos", "crear"))


def crear_rol_bodega(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Rol = apps.get_model("inventario", "Rol")
    RolPermiso = apps.get_model("inventario", "RolPermiso")

    rol, _ = Rol.objects.get_or_create(nombre_rol="Bodega")
    # La migracion es idempotente y deja el rol exactamente con los dos
    # permisos definidos, incluso si se ejecuto antes en una base de pruebas.
    RolPermiso.objects.filter(rol=rol).delete()
    for modulo, accion in PERMISOS_BODEGA:
        permiso = Permiso.objects.get(modulo=modulo, nombre_permiso=accion)
        RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)


def eliminar_rol_bodega(apps, schema_editor):
    Rol = apps.get_model("inventario", "Rol")
    Rol.objects.filter(nombre_rol="Bodega").delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0021_merge_20260913_0000")]

    operations = [migrations.RunPython(crear_rol_bodega, eliminar_rol_bodega)]
