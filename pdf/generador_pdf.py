# Genera el PDF final del plan de trabajo usando reportlab.
# reportlab trabaja con un canvas o con un SimpleDocTemplate + lista de Flowables.
# Usamos SimpleDocTemplate: vamos apilando elementos (Paragraph, Spacer, Table)
# en una lista y al final llamamos a build(), que los coloca en las páginas.

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generar_pdf(datos_curso, ruta_salida):
    """
    Genera un PDF con portada y tabla de asignaturas.

    Parámetros:
        datos_curso : dict con las claves:
                        'fecha_inicio'  — string dd/mm/aaaa
                        'fecha_fin'     — string dd/mm/aaaa (día amarillo)
                        'fecha_examen'  — string dd/mm/aaaa (día verde)
                        'asignaturas'   — lista de dicts con 'codigo', 'nombre', 'horas'
        ruta_salida : string con la ruta completa donde guardar el PDF
    """
    # Configuramos el documento: página A4 con márgenes de 2,5 cm
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    estilos = getSampleStyleSheet()

    # Estilo para el título principal — grande, negrita, centrado
    estilo_titulo = ParagraphStyle(
        "titulo",
        parent=estilos["Title"],
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=0.5 * cm,
    )

    # Estilo para los datos del curso — tamaño normal, centrado
    estilo_datos = ParagraphStyle(
        "datos",
        parent=estilos["Normal"],
        fontSize=11,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=0.3 * cm,
    )

    # Lista de elementos (Flowables) que reportlab apilará en orden
    elementos = []

    # ── PORTADA ───────────────────────────────────────────────────────────────

    elementos.append(Spacer(1, 1.5 * cm))
    elementos.append(Paragraph("HORARIO CURSO CAP", estilo_titulo))
    elementos.append(Spacer(1, 0.8 * cm))

    # Datos del curso: cada línea es un Paragraph independiente
    elementos.append(Paragraph(f"Fecha de inicio: {datos_curso['fecha_inicio']}", estilo_datos))
    elementos.append(Paragraph(f"Último día (amarillo): {datos_curso['fecha_fin']}", estilo_datos))
    elementos.append(Paragraph(f"Fecha del examen (verde): {datos_curso['fecha_examen']}", estilo_datos))

    elementos.append(Spacer(1, 1.5 * cm))

    # ── TABLA DE ASIGNATURAS ──────────────────────────────────────────────────

    # La primera fila es la cabecera; el resto son las asignaturas
    filas = [["Código", "Asignatura", "Horas"]]
    for a in datos_curso["asignaturas"]:
        filas.append([a["codigo"], a["nombre"], str(a["horas"])])

    # Anchos de columna: código estrecho, nombre ancho, horas estrecho
    ancho_pagina = A4[0] - 5 * cm   # ancho A4 menos márgenes
    anchos = [2.5 * cm, ancho_pagina - 5 * cm, 2.5 * cm]

    tabla = Table(filas, colWidths=anchos, repeatRows=1)

    # Estilo de la tabla: bordes, cabecera gris, alternancia suave
    tabla.setStyle(TableStyle([
        # Cabecera: fondo gris oscuro, texto blanco, negrita
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#404040")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  10),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        # Filas de datos
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ALIGN",       (2, 1), (2, -1),  "CENTER"),   # columna Horas centrada
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F0F0")]),
        # Bordes visibles en toda la tabla
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#AAAAAA")),
        # Relleno interior de las celdas
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    elementos.append(tabla)

    # reportlab recorre la lista y va colocando cada elemento en la página
    doc.build(elementos)
