# app/utils/generar_pdf_cuantitativo.py
"""
Generador de PDF para el análisis cuantitativo.
Incluye: KPIs, estadísticas, gráficos, correlaciones, grupos e índice de satisfacción.
"""

import os
import json
import logging
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage, KeepTogether
)

logger = logging.getLogger(__name__)


# ============================================
# ESTILOS
# ============================================

def _get_estilos():
    """Define los estilos de texto del PDF."""
    estilos = getSampleStyleSheet()
    
    estilos.add(ParagraphStyle(
        name='TituloPrincipal',
        parent=estilos['Title'],
        fontSize=26,
        textColor=colors.HexColor('#8e44ad'),
        spaceAfter=20,
        alignment=TA_CENTER
    ))
    
    estilos.add(ParagraphStyle(
        name='Subtitulo',
        parent=estilos['Normal'],
        fontSize=13,
        textColor=colors.HexColor('#555555'),
        spaceAfter=15,
        alignment=TA_CENTER
    ))
    
    estilos.add(ParagraphStyle(
        name='Seccion',
        parent=estilos['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#8e44ad'),
        spaceBefore=20,
        spaceAfter=12,
        borderPadding=5
    ))
    
    estilos.add(ParagraphStyle(
        name='Subseccion',
        parent=estilos['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=10,
        spaceAfter=8
    ))
    
    estilos.add(ParagraphStyle(
        name='TextoNormal',
        parent=estilos['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#333333')
    ))
    
    estilos.add(ParagraphStyle(
        name='TextoPequeno',
        parent=estilos['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#666666')
    ))
    
    return estilos


# ============================================
# HELPERS
# ============================================

def _fmt(valor, decimales=2):
    """Formatea un valor numérico o devuelve '-' si es None."""
    if valor is None or valor == '':
        return '-'
    try:
        return f"{float(valor):.{decimales}f}"
    except (ValueError, TypeError):
        return str(valor)


def _imagen_a_flowable(ruta_png, ancho_max=17*cm):
    """Convierte un PNG en un flowable de reportlab ajustado al ancho."""
    if not os.path.exists(ruta_png):
        return None
    
    try:
        img = RLImage(ruta_png)
        # Escalar proporcionalmente para no superar el ancho máximo
        ratio = img.imageHeight / img.imageWidth
        img.drawWidth = ancho_max
        img.drawHeight = ancho_max * ratio
        return img
    except Exception as e:
        logger.warning(f"Error cargando imagen {ruta_png}: {e}")
        return None


def _tabla_con_estilo(data, col_widths=None):
    """Crea una tabla con estilo consistente."""
    if not data or len(data) < 2:
        return None
    
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    return tabla


# ============================================
# SECCIONES DEL PDF
# ============================================

def _portada(estilos, metadata):
    """Genera la portada."""
    elementos = []
    elementos.append(Spacer(1, 4*cm))
    elementos.append(Paragraph("📊", estilos['TituloPrincipal']))
    elementos.append(Paragraph(
        "Análisis Cuantitativo de Encuesta",
        estilos['TituloPrincipal']
    ))
    elementos.append(Spacer(1, 0.5*cm))
    elementos.append(Paragraph(
        metadata.get('titulo', 'Encuesta sin título'),
        estilos['Subtitulo']
    ))
    if metadata.get('descripcion'):
        elementos.append(Paragraph(
            metadata['descripcion'],
            estilos['TextoPequeno']
        ))
    elementos.append(Spacer(1, 3*cm))
    
    # Info de pie
    info_data = [
        ['Fecha de análisis:', datetime.now().strftime('%d/%m/%Y %H:%M')],
        ['Total encuestados:', str(metadata.get('total_encuestados', 0))],
        ['Preguntas analizadas:', str(len(metadata.get('preguntas', [])))],
    ]
    info_tabla = Table(info_data, colWidths=[5*cm, 8*cm])
    info_tabla.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#8e44ad')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(info_tabla)
    elementos.append(PageBreak())
    return elementos


def _seccion_resumen(estilos, metadata, resultados):
    """KPIs principales."""
    elementos = []
    elementos.append(Paragraph("1. Resumen General", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    # Tabla de KPIs
    correlaciones_num = len(resultados.get('correlaciones', {}).get('pares_significativos', []))
    indice = resultados.get('indice_satisfaccion', {}).get('indice_global')
    
    kpis_data = [
        ['Métrica', 'Valor'],
        ['Total de encuestados', str(metadata.get('total_encuestados', 0))],
        ['Preguntas analizadas', str(len(metadata.get('preguntas', [])))],
        ['Índice de satisfacción global', _fmt(indice) + ' / 100' if indice is not None else 'N/A'],
        ['Correlaciones significativas', str(correlaciones_num)],
    ]
    tabla = _tabla_con_estilo(kpis_data, col_widths=[8*cm, 8*cm])
    if tabla:
        elementos.append(tabla)
    
    elementos.append(Spacer(1, 0.5*cm))
    
    # Lista de preguntas analizadas
    elementos.append(Paragraph("Preguntas analizadas", estilos['Subseccion']))
    
    preguntas_data = [['ID', 'Pregunta', 'Tipo', 'Opciones']]
    for p in metadata.get('preguntas', []):
        tipo_label = {
            'escala_likert': 'Likert',
            'opcion_unica': 'Única',
            'opcion_multiple': 'Múltiple',
            'seleccion_si_no': 'Sí/No'
        }.get(p.get('tipo', ''), p.get('tipo', ''))
        
        preguntas_data.append([
            f"P{p.get('id', '')}",
            str(p.get('texto', ''))[:60],
            tipo_label,
            str(len(p.get('opciones', [])))
        ])
    
    tabla_preguntas = _tabla_con_estilo(
        preguntas_data,
        col_widths=[1.5*cm, 9*cm, 2.5*cm, 2*cm]
    )
    if tabla_preguntas:
        elementos.append(tabla_preguntas)
    
    elementos.append(PageBreak())
    return elementos


def _seccion_graficos(estilos, graficos, directorio_graficos):
    """
    Todos los gráficos, dos por página.
    
    ✅ CORREGIDO: Ahora lista los PNGs directamente del directorio
    (no depende del dict 'graficos' que puede venir vacío del JSON).
    """
    elementos = []
    elementos.append(Paragraph("2. Gráficos del Análisis", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    # ✅ Solo verificar el directorio, no el dict
    if not os.path.exists(directorio_graficos):
        logger.warning(f"Directorio de gráficos no existe: {directorio_graficos}")
        elementos.append(Paragraph("No se generaron gráficos.", estilos['TextoNormal']))
        elementos.append(PageBreak())
        return elementos
    
    # Listar todos los PNGs del directorio
    archivos_png = sorted([f for f in os.listdir(directorio_graficos) if f.endswith('.png')])
    
    logger.info(f"📊 Gráficos encontrados: {len(archivos_png)} en {directorio_graficos}")
    
    if not archivos_png:
        elementos.append(Paragraph("No se generaron gráficos.", estilos['TextoNormal']))
        elementos.append(PageBreak())
        return elementos
    
    for i, archivo in enumerate(archivos_png):
        ruta = os.path.join(directorio_graficos, archivo)
        
        # Nombre amigable
        nombre_amigable = archivo.replace('.png', '').replace('_', ' ').title()
        
        img = _imagen_a_flowable(ruta, ancho_max=16*cm)
        if img:
            bloque = [
                Paragraph(f"Gráfico {i+1}: {nombre_amigable}", estilos['Subseccion']),
                Spacer(1, 0.2*cm),
                img,
                Spacer(1, 0.5*cm)
            ]
            elementos.append(KeepTogether(bloque))
            
            # Salto de página cada 2 gráficos
            if (i + 1) % 2 == 0 and (i + 1) < len(archivos_png):
                elementos.append(PageBreak())
        else:
            logger.warning(f"No se pudo cargar la imagen: {ruta}")
    
    elementos.append(PageBreak())
    return elementos


def _seccion_estadisticas(estilos, resultados):
    """Tabla de estadísticas descriptivas."""
    elementos = []
    elementos.append(Paragraph("3. Estadísticas Descriptivas", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    est = resultados.get('estadisticas_descriptivas', [])
    if not est:
        elementos.append(Paragraph("Sin datos disponibles.", estilos['TextoNormal']))
        elementos.append(PageBreak())
        return elementos
    
    data = [['Pregunta', 'N', 'Media', 'Mediana', 'Moda', 'Desv. Est.', 'Min', 'Max']]
    for row in est:
        data.append([
            str(row.get('Pregunta', ''))[:45],
            str(row.get('Total_Respuestas', 0)),
            _fmt(row.get('Media')),
            _fmt(row.get('Mediana')),
            _fmt(row.get('Moda')),
            _fmt(row.get('Desv_Est')),
            _fmt(row.get('Min')),
            _fmt(row.get('Max')),
        ])
    
    tabla = _tabla_con_estilo(
        data,
        col_widths=[6*cm, 1.2*cm, 1.5*cm, 1.5*cm, 1.2*cm, 1.5*cm, 1.2*cm, 1.2*cm]
    )
    if tabla:
        elementos.append(tabla)
    
    elementos.append(PageBreak())
    return elementos


def _seccion_correlaciones(estilos, resultados):
    """Tabla de correlaciones significativas."""
    elementos = []
    elementos.append(Paragraph("4. Correlaciones Significativas", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    pares = resultados.get('correlaciones', {}).get('pares_significativos', [])
    if not pares:
        elementos.append(Paragraph(
            "No se encontraron correlaciones significativas (|r| ≥ 0.3).",
            estilos['TextoNormal']
        ))
        elementos.append(PageBreak())
        return elementos
    
    data = [['Pregunta 1', 'Pregunta 2', 'r', 'Interpretación']]
    for par in pares[:30]:  # Limitar a 30
        data.append([
            str(par.get('Pregunta_1', ''))[:35],
            str(par.get('Pregunta_2', ''))[:35],
            _fmt(par.get('Correlacion')),
            str(par.get('Interpretacion', ''))[:30]
        ])
    
    tabla = _tabla_con_estilo(
        data,
        col_widths=[4.5*cm, 4.5*cm, 1.5*cm, 4.5*cm]
    )
    if tabla:
        elementos.append(tabla)
    
    elementos.append(PageBreak())
    return elementos


def _seccion_grupos(estilos, resultados):
    """Análisis por grupos."""
    elementos = []
    elementos.append(Paragraph("5. Análisis por Grupos", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    grupos = resultados.get('grupos', {})
    grupo_pregunta = grupos.get('grupo_pregunta')
    resumen = grupos.get('resumen', [])
    
    if not resumen:
        elementos.append(Paragraph(
            "No hay datos de grupos disponibles.",
            estilos['TextoNormal']
        ))
        elementos.append(PageBreak())
        return elementos
    
    if grupo_pregunta:
        elementos.append(Paragraph(
            f"Grupo de comparación: <b>{grupo_pregunta}</b>",
            estilos['TextoNormal']
        ))
        elementos.append(Spacer(1, 0.3*cm))
    
    data = [['Pregunta', 'Grupo', 'N', 'Media', 'Mediana', 'Desv. Est.']]
    for row in resumen[:40]:  # Limitar
        data.append([
            str(row.get('Pregunta', ''))[:40],
            str(row.get('Grupo', ''))[:20],
            str(row.get('N', 0)),
            _fmt(row.get('Media')),
            _fmt(row.get('Mediana')),
            _fmt(row.get('Desv_Est')),
        ])
    
    tabla = _tabla_con_estilo(
        data,
        col_widths=[5.5*cm, 3*cm, 1.5*cm, 2*cm, 2*cm, 2*cm]
    )
    if tabla:
        elementos.append(tabla)
    
    elementos.append(PageBreak())
    return elementos


def _seccion_satisfaccion(estilos, resultados):
    """Índice de satisfacción."""
    elementos = []
    elementos.append(Paragraph("6. Índice de Satisfacción", estilos['Seccion']))
    elementos.append(Spacer(1, 0.3*cm))
    
    indice = resultados.get('indice_satisfaccion', {})
    indice_global = indice.get('indice_global')
    por_pregunta = indice.get('por_pregunta', [])
    
    if indice_global is None:
        elementos.append(Paragraph(
            "No hay índice de satisfacción disponible.",
            estilos['TextoNormal']
        ))
        elementos.append(PageBreak())
        return elementos
    
    # Índice global grande
    color = '#2ecc71' if indice_global >= 70 else ('#f39c12' if indice_global >= 50 else '#e74c3c')
    etiqueta = 'Satisfactorio' if indice_global >= 70 else ('Neutral' if indice_global >= 50 else 'Necesita Mejora')
    
    elementos.append(Paragraph(
        f"<font color='{color}' size='36'><b>{indice_global}</b></font>"
        f"<font size='16'> / 100</font>",
        estilos['TextoNormal']
    ))
    elementos.append(Paragraph(
        f"Clasificación: <b>{etiqueta}</b>",
        estilos['TextoNormal']
    ))
    elementos.append(Spacer(1, 0.5*cm))
    
    # Tabla por pregunta
    if por_pregunta:
        elementos.append(Paragraph("Índice por pregunta", estilos['Subseccion']))
        data = [['Pregunta', 'Índice', 'Min', 'Max']]
        for row in por_pregunta:
            data.append([
                str(row.get('Pregunta', ''))[:60],
                _fmt(row.get('Indice_Promedio')),
                _fmt(row.get('Min')),
                _fmt(row.get('Max')),
            ])
        
        tabla = _tabla_con_estilo(data, col_widths=[9*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        if tabla:
            elementos.append(tabla)
    
    return elementos


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def generar_pdf_analisis_cuantitativo(directorio_resultados):
    """
    Genera un PDF completo con todos los resultados del análisis.
    
    Args:
        directorio_resultados: ruta al directorio con los resultados
    
    Returns:
        BytesIO con el PDF generado
    """
    # ============================================
    # 1. CARGAR DATOS
    # ============================================
    ruta_json = None
    for archivo in os.listdir(directorio_resultados):
        if archivo.startswith('analisis_cuantitativo_') and archivo.endswith('.json'):
            ruta_json = os.path.join(directorio_resultados, archivo)
            break
    
    if not ruta_json or not os.path.exists(ruta_json):
        raise FileNotFoundError("No se encontró el JSON del análisis")
    
    with open(ruta_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    resultados = data.get('resultados', {})
    
    directorio_graficos = os.path.join(directorio_resultados, 'graficos')
    
    logger.info(f"📄 Generando PDF desde: {directorio_resultados}")
    logger.info(f"📁 Directorio de gráficos: {directorio_graficos}")
    
    # ============================================
    # 2. CONFIGURAR DOCUMENTO
    # ============================================
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=f"Análisis Cuantitativo - {metadata.get('titulo', 'Encuesta')}"
    )
    
    estilos = _get_estilos()
    
    # ============================================
    # 3. CONSTRUIR CONTENIDO
    # ============================================
    elementos = []
    
    elementos += _portada(estilos, metadata)
    elementos += _seccion_resumen(estilos, metadata, resultados)
    elementos += _seccion_graficos(estilos, resultados.get('graficos', {}), directorio_graficos)
    elementos += _seccion_estadisticas(estilos, resultados)
    elementos += _seccion_correlaciones(estilos, resultados)
    elementos += _seccion_grupos(estilos, resultados)
    elementos += _seccion_satisfaccion(estilos, resultados)
    
    # ============================================
    # 4. NUMERACIÓN DE PÁGINAS
    # ============================================
    def _add_numero_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#888888'))
        texto = f"Página {doc.page}"
        canvas.drawRightString(
            A4[0] - 2*cm,
            1*cm,
            texto
        )
        canvas.drawString(
            2*cm,
            1*cm,
            f"Análisis Cuantitativo - {metadata.get('titulo', '')[:40]}"
        )
        canvas.restoreState()
    
    # ============================================
    # 5. GENERAR PDF
    # ============================================
    doc.build(elementos, onFirstPage=_add_numero_pagina, onLaterPages=_add_numero_pagina)
    
    buffer.seek(0)
    return buffer