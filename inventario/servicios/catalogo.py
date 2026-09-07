"""Carga masiva del catalogo de piezas desde una planilla Excel.

La planilla tiene una categoria por columna: el encabezado es el nombre de la
categoria y las filas de abajo son las piezas.

    MECANICA        | Columna 1 | CARROCERIA                   | ...
    cremallera...   |           | funda de parachoque delantero| ...
    palier izquierdo|           | mascara inferior...          | ...

Lo que entra son piezas PLANTILLA (producto sin vehiculo ni costo): el stock
real se registra despues por el modulo de Ingresos.

El mismo servicio lo usan el comando `importar_catalogo` y la pantalla web,
para que las reglas de lectura y de escritura sean exactamente las mismas.
"""

from dataclasses import dataclass, field
from zipfile import BadZipFile

from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from ..models import Categoria, Producto, normalizar_texto

# Topes defensivos: acotan el trabajo ante un archivo enorme o manipulado.
MAX_FILAS = 20000
MAX_COLUMNAS = 100

# Largo de los campos de destino (models.Categoria / models.Producto).
LARGO_MAX_CATEGORIA = 50
LARGO_MAX_PIEZA = 100

PREFIJO_COLUMNA_VACIA = "COLUMNA"


class PlanillaInvalidaError(Exception):
    """El archivo no se puede leer como planilla de catalogo."""


@dataclass
class Lectura:
    """Resultado de interpretar la planilla, antes de tocar la base."""

    piezas: list = field(default_factory=list)  # [(categoria, nombre)]
    categorias: list = field(default_factory=list)
    avisos: list = field(default_factory=list)

    @property
    def total_piezas(self):
        return len(self.piezas)


@dataclass
class ResumenCategoria:
    categoria: str
    nuevas: int = 0
    existentes: int = 0

    @property
    def total(self):
        return self.nuevas + self.existentes


@dataclass
class Resumen:
    """Resultado de la importacion (o de la simulacion)."""

    categorias_creadas: int = 0
    piezas_creadas: int = 0
    piezas_existentes: int = 0
    detalle: list = field(default_factory=list)  # [ResumenCategoria]
    simulado: bool = False


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
def _abrir_hoja(archivo):
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    # Un .xlsx es un ZIP: si el contenido no lo es, zipfile falla antes que
    # openpyxl y hay que capturarlo aparte de InvalidFileException.
    except (
        BadZipFile,
        InvalidFileException,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise PlanillaInvalidaError(
            "El archivo no es una planilla Excel (.xlsx) valida."
        ) from exc
    if not libro.sheetnames:
        raise PlanillaInvalidaError("La planilla no tiene hojas.")
    return libro[libro.sheetnames[0]]


def _filas_con_datos(hoja):
    """Filas no vacias de la hoja, hasta el tope defensivo.

    La planilla real empieza con dos filas en blanco y trae huecos entre las
    piezas, por eso se descartan las filas vacias en vez de asumir que los
    datos son contiguos.
    """
    filas = []
    for fila in hoja.iter_rows(values_only=True):
        if any(valor is not None and str(valor).strip() for valor in fila):
            filas.append(fila[:MAX_COLUMNAS])
        if len(filas) >= MAX_FILAS:
            break
    return filas


def _es_columna_ignorable(encabezado):
    return not encabezado or encabezado.startswith(PREFIJO_COLUMNA_VACIA)


def leer_planilla(archivo):
    """Interpreta la planilla y devuelve las piezas normalizadas.

    No escribe nada: separar lectura de escritura permite previsualizar el
    resultado antes de confirmarlo y probar el parseo sin base de datos.
    """
    hoja = _abrir_hoja(archivo)
    filas = _filas_con_datos(hoja)
    if not filas:
        raise PlanillaInvalidaError("La planilla no contiene datos.")

    encabezados = [normalizar_texto(valor) or "" for valor in filas[0]]
    lectura = Lectura()
    vistos = set()
    repetidos = 0
    largos = []

    for indice, encabezado in enumerate(encabezados):
        if _es_columna_ignorable(encabezado):
            continue
        if len(encabezado) > LARGO_MAX_CATEGORIA:
            lectura.avisos.append(
                f"Se ignoro la columna «{encabezado[:30]}…»: el nombre de la "
                f"categoria supera {LARGO_MAX_CATEGORIA} caracteres."
            )
            continue

        piezas_columna = 0
        for fila in filas[1:]:
            valor = fila[indice] if indice < len(fila) else None
            nombre = normalizar_texto(valor)
            if not nombre:
                continue
            if len(nombre) > LARGO_MAX_PIEZA:
                largos.append(nombre)
                continue
            clave = (encabezado, nombre)
            if clave in vistos:
                repetidos += 1
                continue
            vistos.add(clave)
            lectura.piezas.append(clave)
            piezas_columna += 1

        if piezas_columna:
            lectura.categorias.append(encabezado)

    if not lectura.piezas:
        raise PlanillaInvalidaError(
            "No se encontraron piezas. Revisa que la primera fila con datos "
            "sean los nombres de las categorias."
        )
    if repetidos:
        lectura.avisos.append(
            f"{repetidos} nombre(s) repetido(s) en la planilla: se importa "
            "una sola vez cada uno."
        )
    if largos:
        lectura.avisos.append(
            f"{len(largos)} pieza(s) omitida(s) por superar {LARGO_MAX_PIEZA} "
            f"caracteres (por ejemplo «{largos[0][:40]}…»)."
        )
    return lectura


# ---------------------------------------------------------------------------
# Importacion
# ---------------------------------------------------------------------------
def _categorias_por_nombre(nombres, crear):
    # Las claves se normalizan igual que la planilla: la colacion de MySQL
    # encuentra "Mecanica" al buscar "MECANICA", y sin normalizar la clave
    # del diccionario no coincidiria y se intentaria crear un duplicado.
    existentes = {
        normalizar_texto(categoria.nombre_categoria): categoria
        for categoria in Categoria.objects.filter(nombre_categoria__in=nombres)
    }
    creadas = 0
    for nombre in nombres:
        if nombre in existentes:
            continue
        if crear:
            existentes[nombre] = Categoria.objects.create(nombre_categoria=nombre)
        creadas += 1
    return existentes, creadas


@transaction.atomic
def importar_catalogo(piezas, simular=False):
    """Crea las piezas plantilla que falten. Nunca borra ni modifica.

    Con `simular=True` solo cuenta: sirve para el `--dry-run` del comando y
    para la vista previa de la pantalla web.

    Se resuelve con tres consultas fijas (categorias, piezas existentes y un
    `bulk_create`) en vez de un `get_or_create` por fila: la planilla real
    trae 332 piezas y eso serian ~660 consultas.
    """
    nombres_categoria = []
    for categoria, _ in piezas:
        if categoria not in nombres_categoria:
            nombres_categoria.append(categoria)

    categorias, categorias_creadas = _categorias_por_nombre(
        nombres_categoria, crear=not simular
    )

    # Se consideran existentes tambien las piezas eliminadas logicamente: asi
    # una reimportacion nunca deja dos filas con el mismo nombre. Para
    # recuperar una pieza eliminada se edita desde el modulo de Productos.
    ids = [categoria.pk for categoria in categorias.values()]
    ya_existen = {
        (normalizar_texto(categoria), normalizar_texto(nombre))
        for categoria, nombre in Producto.objects.filter(
            categoria_id__in=ids, vehiculo__isnull=True
        ).values_list("categoria__nombre_categoria", "nombre")
    }

    resumen = Resumen(categorias_creadas=categorias_creadas, simulado=simular)
    detalle = {}
    nuevos = []
    for categoria, nombre in piezas:
        fila = detalle.setdefault(categoria, ResumenCategoria(categoria=categoria))
        if (categoria, nombre) in ya_existen:
            fila.existentes += 1
            resumen.piezas_existentes += 1
            continue
        fila.nuevas += 1
        resumen.piezas_creadas += 1
        if not simular:
            nuevos.append(
                Producto(
                    categoria=categorias[categoria], nombre=nombre, vehiculo=None
                )
            )

    if nuevos:
        # bulk_create no ejecuta save(), por eso los nombres ya vienen
        # normalizados desde leer_planilla().
        Producto.objects.bulk_create(nuevos)

    resumen.detalle = list(detalle.values())
    return resumen
