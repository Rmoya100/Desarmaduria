"""Carga el catalogo de piezas desde una planilla Excel.

A diferencia de `cargar_excel_prueba`, que ademas inventa una entrada con
stock ficticio para poblar demos, este comando solo crea el catalogo: las
piezas quedan sin vehiculo y sin stock, listas para usarse en Ingresos.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inventario.servicios.catalogo import (
    PlanillaInvalidaError,
    importar_catalogo,
    leer_planilla,
)


class Command(BaseCommand):
    help = "Importa las piezas del catalogo desde una planilla Excel."

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo",
            nargs="?",
            default="VENTAS.xlsx",
            help="Ruta del archivo .xlsx (por defecto: VENTAS.xlsx).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que se importaria sin escribir en la base.",
        )

    def handle(self, *args, **options):
        archivo = Path(options["archivo"])
        if not archivo.exists():
            raise CommandError(f"No existe el archivo: {archivo}")

        try:
            with archivo.open("rb") as contenido:
                lectura = leer_planilla(contenido)
        except PlanillaInvalidaError as error:
            raise CommandError(str(error)) from error

        simular = options["dry_run"]
        resumen = importar_catalogo(lectura.piezas, simular=simular)

        self.stdout.write(
            f"Planilla: {archivo}  ({lectura.total_piezas} piezas en "
            f"{len(lectura.categorias)} categorias)"
        )
        for fila in resumen.detalle:
            self.stdout.write(
                f"  {fila.categoria:<30} {fila.nuevas:>4} nuevas   "
                f"{fila.existentes:>4} ya existian"
            )
        for aviso in lectura.avisos:
            self.stdout.write(self.style.WARNING(f"  Aviso: {aviso}"))

        mensaje = (
            f"{resumen.piezas_creadas} piezas nuevas y "
            f"{resumen.categorias_creadas} categorias nuevas"
        )
        if simular:
            self.stdout.write(
                self.style.WARNING(f"Simulacion: se crearian {mensaje}. Nada se guardo.")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Importacion completada: {mensaje}."))
