"""Generacion de PDFs del modulo Gastos. Separado de views.py para que las
vistas solo se ocupen de "que datos exportar" y este archivo de "como se ve
el PDF" (colores, fuentes, layout de la tabla)."""

from io import BytesIO

from django.contrib.staticfiles import finders
from django.utils import timezone
from django.utils.formats import number_format
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NOMBRE_EMPRESA = "Desarmaduría Puente Alto"

COLOR_PRIMARIO = colors.HexColor("#2f6690")
COLOR_PRIMARIO_OSCURO = colors.HexColor("#244f70")
COLOR_BORDE = colors.HexColor("#e2e4e9")
COLOR_FILA_ALT = colors.HexColor("#f4f5f7")
COLOR_TEXTO_MUTED = colors.HexColor("#6b7280")

ANCHO_PAGINA_COMPROBANTE = A4[0] - 2 * 1.8 * cm
# El listado de gastos se imprime en A4 horizontal: el encabezado necesita su
# propio ancho o el recuadro azul queda mas angosto que la tabla (bug previo).
ANCHO_PAGINA_LISTADO = landscape(A4)[0] - 2 * 1.8 * cm


def formato_monto(valor):
    return "$" + number_format(valor, decimal_pos=2, force_grouping=True)


def _logo_flowable(alto=1.3 * cm):
    """Busca el logo del proyecto entre los archivos estaticos (sirve tanto
    en desarrollo como despues de collectstatic) y lo devuelve como imagen
    de reportlab respetando su proporcion real."""
    ruta_logo = finders.find("imagen/logo.webp")
    if not ruta_logo:
        return None
    try:
        with PILImage.open(ruta_logo) as imagen_pil:
            ancho_original, alto_original = imagen_pil.size
    except OSError:
        return None
    ancho = alto * (ancho_original / alto_original)
    imagen = RLImage(ruta_logo, width=ancho, height=alto)
    imagen.hAlign = "LEFT"
    return imagen


def _encabezado(titulo, generado_en, ancho=ANCHO_PAGINA_COMPROBANTE):
    """Franja superior compartida por los dos reportes: logo + nombre de la
    empresa a la izquierda, titulo del reporte al centro y fecha de
    generacion a la derecha. Usa los mismos colores que el resto del sitio
    (base.css). `ancho` debe ser el ancho util real de la pagina del
    documento que la llama (vertical u horizontal), para que el recuadro
    azul quede del mismo porte que la tabla que va debajo."""
    estilos = getSampleStyleSheet()
    estilo_empresa = ParagraphStyle(
        "Empresa",
        parent=estilos["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    estilo_titulo = ParagraphStyle(
        "TituloReporte",
        parent=estilos["Normal"],
        fontSize=15,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=1,
    )
    estilo_fecha = ParagraphStyle(
        "FechaReporte",
        parent=estilos["Normal"],
        fontSize=8.5,
        textColor=colors.white,
        alignment=2,
    )

    logo = _logo_flowable()
    columna_izquierda = [logo, Spacer(1, 4)] if logo else []
    columna_izquierda.append(Paragraph(NOMBRE_EMPRESA, estilo_empresa))

    columna_centro = [Paragraph(titulo, estilo_titulo)]
    columna_derecha = [Paragraph(f"Fecha: {generado_en}", estilo_fecha)]

    ancho_izquierda = ancho * 0.38
    ancho_derecha = ancho * 0.3
    ancho_centro = ancho - ancho_izquierda - ancho_derecha

    tabla = Table(
        [[columna_izquierda, columna_centro, columna_derecha]],
        colWidths=[ancho_izquierda, ancho_centro, ancho_derecha],
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARIO_OSCURO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 16),
                ("RIGHTPADDING", (-1, 0), (-1, 0), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return tabla


def gastos_pdf_bytes(gastos, total):
    """PDF listado de gastos (con su fila de total); la vista lo llama."""
    encabezados = [
        "Fecha", "Concepto", "Forma de pago", "Monto",
        "Tipo Doc.", "N.° Documento", "Observaciones", "Usuario",
    ]
    filas = [encabezados]
    for gasto in gastos:
        filas.append(
            [
                gasto.fecha.strftime("%d-%m-%Y"),
                str(gasto.concepto),
                str(gasto.forma_pago),
                formato_monto(gasto.monto),
                str(gasto.tipo_documento) if gasto.tipo_documento else "—",
                gasto.numero_documento or "—",
                gasto.observaciones or "",
                str(gasto.usuario),
            ]
        )
    filas.append(["", "", "", formato_monto(total), "", "", "Total", ""])

    # Anchos proporcionales de columna: sin esto la tabla se autoajusta al
    # contenido y queda mas angosta que el encabezado (que si ocupa todo
    # ANCHO_PAGINA_LISTADO), rompiendo la alineacion visual entre ambos.
    proporciones = [0.08, 0.16, 0.11, 0.09, 0.09, 0.11, 0.24, 0.12]
    anchos_columnas = [ANCHO_PAGINA_LISTADO * p for p in proporciones]

    tabla = Table(filas, colWidths=anchos_columnas, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, COLOR_FILA_ALT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    generado_en = timezone.localtime().strftime("%d-%m-%Y %H:%M")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        title="Gastos",
        topMargin=0,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )
    doc.build(
        [
            _encabezado("Listado de gastos", generado_en, ANCHO_PAGINA_LISTADO),
            Spacer(1, 16),
            tabla,
        ]
    )
    buffer.seek(0)
    return buffer.getvalue()


def gasto_comprobante_pdf_bytes(gasto):
    """PDF de una pagina para UN gasto: sus datos principales y, si tiene,
    la foto del comprobante adjunta. Lo pide el boton "Guardar PDF" de la
    vista de comprobante individual."""
    estilos = getSampleStyleSheet()
    estilo_etiqueta = ParagraphStyle(
        "Etiqueta",
        parent=estilos["Normal"],
        fontSize=7.5,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    estilo_valor = ParagraphStyle(
        "Valor",
        parent=estilos["Normal"],
        fontSize=10.5,
        fontName="Helvetica-Bold",
    )
    estilo_pie = ParagraphStyle(
        "Pie",
        parent=estilos["Normal"],
        fontSize=8,
        textColor=COLOR_TEXTO_MUTED,
    )

    etiquetas = ["FECHA", "CONCEPTO", "MONTO", "TIPO DOC.", "N.° DOCUMENTO"]
    valores = [
        gasto.fecha.strftime("%d-%m-%Y"),
        str(gasto.concepto),
        formato_monto(gasto.monto),
        str(gasto.tipo_documento) if gasto.tipo_documento else "—",
        gasto.numero_documento or "—",
    ]
    ancho_columna = ANCHO_PAGINA_COMPROBANTE / len(etiquetas)

    tabla_datos = Table(
        [
            [Paragraph(etq, estilo_etiqueta) for etq in etiquetas],
            [Paragraph(val, estilo_valor) for val in valores],
        ],
        colWidths=[ancho_columna] * len(etiquetas),
    )
    tabla_datos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    contenido = [
        Paragraph(
            f"Comprobante de gasto #{gasto.pk}",
            ParagraphStyle("Titulo", parent=estilos["Heading2"], textColor=COLOR_PRIMARIO_OSCURO),
        ),
        Spacer(1, 8),
        tabla_datos,
        Spacer(1, 16),
    ]

    if gasto.observaciones:
        contenido.append(Paragraph(f"<b>Observaciones:</b> {gasto.observaciones}", estilos["Normal"]))
        contenido.append(Spacer(1, 16))

    if gasto.imagen:
        try:
            with PILImage.open(gasto.imagen.path) as imagen_pil:
                ancho_original, alto_original = imagen_pil.size
            alto_imagen = ANCHO_PAGINA_COMPROBANTE * (alto_original / ancho_original)
            alto_maximo = 18 * cm
            if alto_imagen > alto_maximo:
                alto_imagen = alto_maximo
            contenido.append(
                RLImage(
                    gasto.imagen.path,
                    width=ANCHO_PAGINA_COMPROBANTE,
                    height=alto_imagen,
                    kind="proportional",
                )
            )
        except (OSError, ValueError):
            contenido.append(Paragraph("No fue posible cargar la imagen adjunta.", estilo_pie))
    else:
        contenido.append(Paragraph("Este gasto no tiene una imagen adjunta.", estilo_pie))

    generado_en = timezone.localtime().strftime("%d-%m-%Y %H:%M")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Comprobante de gasto #{gasto.pk}",
        topMargin=0,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    doc.build(
        [
            _encabezado("Documento adjunto de gasto", generado_en),
            Spacer(1, 16),
            *contenido,
        ]
    )
    buffer.seek(0)
    return buffer.getvalue()
