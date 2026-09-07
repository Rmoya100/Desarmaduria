from django.db import migrations

MODULOS_ACCIONES = {
    "ventas": ["ver", "crear", "editar", "eliminar"],
}


def crear_seed(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Rol = apps.get_model("inventario", "Rol")
    RolPermiso = apps.get_model("inventario", "RolPermiso")

    permisos = []
    for modulo, acciones in MODULOS_ACCIONES.items():
        for accion in acciones:
            permiso, _ = Permiso.objects.get_or_create(
                modulo=modulo, nombre_permiso=accion
            )
            permisos.append(permiso)

    rol_admin, _ = Rol.objects.get_or_create(nombre_rol="Administrador")
    for permiso in permisos:
        RolPermiso.objects.get_or_create(rol=rol_admin, permiso=permiso)


def revertir_seed(apps, schema_editor):
    Permiso = apps.get_model("inventario", "Permiso")
    Permiso.objects.filter(modulo__in=MODULOS_ACCIONES.keys()).delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0005_merge_20260905_1739")]
    operations = [migrations.RunPython(crear_seed, revertir_seed)]
