from django.db import migrations

MODULOS_ACCIONES = {
    "usuarios": ["ver", "crear", "editar"],
    "roles": ["ver", "crear", "editar"],
    "formas_pago": ["ver", "crear", "editar", "eliminar"],
    "documentos": ["ver", "crear", "editar", "eliminar"],
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
    Rol = apps.get_model("inventario", "Rol")
    Rol.objects.filter(nombre_rol="Administrador").delete()


class Migration(migrations.Migration):
    dependencies = [("inventario", "0001_initial")]
    operations = [migrations.RunPython(crear_seed, revertir_seed)]
