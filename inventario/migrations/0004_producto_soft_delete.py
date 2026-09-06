from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventario", "0003_vehiculo_opcional"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="fecha_eliminacion",
            field=models.DateTimeField(
                blank=True,
                db_column="fechaEliminacion",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="eliminado_por",
            field=models.ForeignKey(
                blank=True,
                db_column="eliminadoPor",
                null=True,
                on_delete=models.SET_NULL,
                related_name="productos_eliminados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]