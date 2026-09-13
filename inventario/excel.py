"""Generacion de archivos Excel de reportes que necesitan varias secciones
en una misma hoja. Separado de views.py por el mismo motivo que pdf.py: la
vista solo decide "que datos exportar", este modulo decide "como se ve la
planilla" (titulos, formato de moneda, anchos de columna)."""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

COLOR_HEADER = "244F70"
COLOR_FILA_ALT = "F4F5F7"
# Formato contable con signo "$" (positivo;negativo;cero) en vez de
# "#,##0" plano: a diferencia de los demas exports Excel de la app, aca el
# usuario pidio ver el simbolo de moneda igual que en el PDF/pantalla, y
# un IVA en $0 se ve como "$ -" en vez de "$ 0".
FORMATO_MONEDA = '"$" #,##0;"$" -#,##0;"$" -'

RELLENO_HEADER = PatternFill("solid", fgColor=COLOR_HEADER)
RELLENO_ALT = PatternFill("solid", fgColor=COLOR_FILA_ALT)
FUENTE_HEADER = Font(bold=True, color="FFFFFF")

ENCABEZADOS_MOVIMIENTOS = [
    "Fecha", "Movimiento", "Concepto", "Producto/Motivo", "N.° Documento", "Neto", "Iva", "Total",
]


def _escribir_bloque_periodo(ws, fila, etiqueta, saldo_anterior, subtotal_ingresos, subtotal_gastos, saldo_en_caja, movimientos):
    """Un bloque = saldo anterior/subtotales/saldo en caja de un periodo,
    mas el detalle cronologico de sus movimientos (una fila por producto
    vendido o por gasto). Se repite una vez por cada periodo del rango,
    como una cartola bancaria mes a mes."""
    resumen = [
        ("Saldo Anterior", saldo_anterior),
        ("Subtotal Ingresos Período", subtotal_ingresos),
        ("Subtotal Gastos Período", -subtotal_gastos),
        ("Saldo en caja", saldo_en_caja),
    ]
    for etiqueta_resumen, valor in resumen:
        ws.cell(row=fila, column=1, value=etiqueta_resumen).font = Font(bold=True)
        ws.cell(row=fila, column=2, value=valor).number_format = FORMATO_MONEDA
        fila += 1

    fila += 1
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=len(ENCABEZADOS_MOVIMIENTOS))
    titulo = ws.cell(row=fila, column=1, value=f"Movimientos del Período {etiqueta}")
    titulo.font = Font(bold=True)
    titulo.alignment = Alignment(horizontal="center")
    fila += 1

    for col, texto in enumerate(ENCABEZADOS_MOVIMIENTOS, start=1):
        celda = ws.cell(row=fila, column=col, value=texto)
        celda.font = FUENTE_HEADER
        celda.fill = RELLENO_HEADER
        celda.alignment = Alignment(horizontal="center")
    fila += 1

    if not movimientos:
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=len(ENCABEZADOS_MOVIMIENTOS))
        ws.cell(row=fila, column=1, value="Sin movimientos en este período.")
        fila += 1
    for i, mov in enumerate(movimientos):
        if i % 2:
            for col in range(1, len(ENCABEZADOS_MOVIMIENTOS) + 1):
                ws.cell(row=fila, column=col).fill = RELLENO_ALT
        ws.cell(row=fila, column=1, value=mov["fecha"].strftime("%d-%m-%Y"))
        ws.cell(row=fila, column=2, value=mov["movimiento"])
        ws.cell(row=fila, column=3, value=mov["concepto"])
        ws.cell(row=fila, column=4, value=mov["producto_motivo"])
        ws.cell(row=fila, column=5, value=mov["numero_documento"])
        ws.cell(row=fila, column=6, value=mov["neto"]).number_format = FORMATO_MONEDA
        ws.cell(row=fila, column=7, value=mov["iva"]).number_format = FORMATO_MONEDA
        ws.cell(row=fila, column=8, value=mov["total"]).number_format = FORMATO_MONEDA
        fila += 1

    return fila + 2


def caja_excel_bytes(datos):
    """Libro de caja: por cada periodo del rango, su bloque de
    saldos (Saldo Anterior/Subtotal Ingresos/Subtotal Gastos/Saldo en
    caja) seguido del detalle linea a linea de sus movimientos, igual que
    una cartola bancaria. El PDF y la pantalla usan otro formato (desglose
    agregado por forma de pago/tipo de documento/concepto); este Excel es
    el unico que muestra el detalle transaccion por transaccion."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Flujo de caja"

    fila = 1
    saldo_anterior = datos["saldo_antes_del_periodo"]
    for periodo in datos["filas"]:
        movimientos = datos["movimientos_por_periodo"].get(periodo["mes"], [])
        fila = _escribir_bloque_periodo(
            ws, fila, periodo["etiqueta"], saldo_anterior,
            periodo["ventas"], periodo["gastos"], periodo["saldo_acumulado"], movimientos,
        )
        saldo_anterior = periodo["saldo_acumulado"]

    for columna, ancho in {
        "A": 16, "B": 12, "C": 18, "D": 30, "E": 14, "F": 14, "G": 14, "H": 14,
    }.items():
        ws.column_dimensions[columna].width = ancho
    return wb
