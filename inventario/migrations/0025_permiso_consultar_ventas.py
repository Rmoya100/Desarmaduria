from django.db import migrations


def crear_seed(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Rol = apps.get_model("inventario", "Rol")
    RolPermiso = apps.get_model("inventario", "RolPermiso")

    permiso, _ = Permiso.objects.get_or_create(modulo="ventas", nombre_permiso="consultar")

    rol_admin, _ = Rol.objects.get_or_create(nombre_rol="Administrador")
    RolPermiso.objects.get_or_create(rol=rol_admin, permiso=permiso)

    # El rol Vendedor solo consulta el catalogo de stock disponible (pantalla
    # "Consulta para ventas"), no el modulo de ventas completo (historial,
    # crear/editar/eliminar venta), que sigue exigiendo "ventas.ver".
    rol_vendedor = Rol.objects.filter(nombre_rol="Vendedor").first()
    if rol_vendedor:
        RolPermiso.objects.get_or_create(rol=rol_vendedor, permiso=permiso)


def revertir_seed(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Permiso.objects.filter(modulo="ventas", nombre_permiso="consultar").delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0024_rol_vendedor")]
    operations = [migrations.RunPython(crear_seed, revertir_seed)]
