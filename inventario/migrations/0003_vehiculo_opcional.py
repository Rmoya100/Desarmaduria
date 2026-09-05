from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventario", "0002_seed_permisos")]

    operations = [
        migrations.AlterField(
            model_name="producto",
            name="vehiculo",
            field=models.ForeignKey(
                blank=True,
                db_column="idVehiculo",
                null=True,
                on_delete=models.PROTECT,
                related_name="productos",
                to="inventario.vehiculo",
            ),
        ),
        migrations.AlterField(
            model_name="entrada",
            name="vehiculo",
            field=models.ForeignKey(
                blank=True,
                db_column="idVehiculo",
                null=True,
                on_delete=models.PROTECT,
                related_name="entradas",
                to="inventario.vehiculo",
            ),
        ),
    ]