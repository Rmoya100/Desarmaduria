"""Ficha de vehiculo con tipo de carroceria y rango de anios.

`anio` pasa a llamarse `anio_desde` en Python pero conserva la columna
`anio` en MySQL (`db_column`), por lo que el RENAME no toca datos.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("inventario", "0006_seed_permisos_ventas")]

    operations = [
        migrations.CreateModel(
            name="TipoVehiculo",
            fields=[
                (
                    "id_tipo_vehiculo",
                    models.AutoField(
                        db_column="idTipoVehiculo",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "nombre_tipo",
                    models.CharField(
                        db_column="nombreTipo", max_length=50, unique=True
                    ),
                ),
            ],
            options={
                "verbose_name": "tipo de vehiculo",
                "verbose_name_plural": "tipos de vehiculo",
                "db_table": "tipoVehiculo",
            },
        ),
        migrations.RenameField(
            model_name="vehiculo",
            old_name="anio",
            new_name="anio_desde",
        ),
        migrations.AlterField(
            model_name="vehiculo",
            name="anio_desde",
            field=models.PositiveSmallIntegerField(db_column="anio"),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="anio_hasta",
            field=models.PositiveSmallIntegerField(
                blank=True, db_column="anioHasta", null=True
            ),
        ),
        migrations.AddField(
            model_name="vehiculo",
            name="tipo_vehiculo",
            field=models.ForeignKey(
                blank=True,
                db_column="idTipoVehiculo",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vehiculos",
                to="inventario.tipovehiculo",
            ),
        ),
    ]
