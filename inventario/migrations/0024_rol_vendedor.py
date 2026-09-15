from django.db import migrations


PERMISOS_VENDEDOR = (("productos", "ver"),)


def crear_rol_vendedor(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Rol = apps.get_model("inventario", "Rol")
    RolPermiso = apps.get_model("inventario", "RolPermiso")

    rol, _ = Rol.objects.get_or_create(nombre_rol="Vendedor")
    # La migracion es idempotente y deja el rol exactamente con los permisos
    # definidos, incluso si se ejecuto antes en una base de pruebas.
    RolPermiso.objects.filter(rol=rol).delete()
    for modulo, accion in PERMISOS_VENDEDOR:
        permiso = Permiso.objects.get(modulo=modulo, nombre_permiso=accion)
        RolPermiso.objects.get_or_create(rol=rol, permiso=permiso)


def eliminar_rol_vendedor(apps, schema_editor):
    Rol = apps.get_model("inventario", "Rol")
    Rol.objects.filter(nombre_rol="Vendedor").delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0023_seed_permisos_productos")]

    operations = [migrations.RunPython(crear_rol_vendedor, eliminar_rol_vendedor)]
