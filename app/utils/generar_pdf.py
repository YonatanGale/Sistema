# app/utils/generar_pdf.py
"""
Genera un PDF con los resultados del análisis cualitativo usando ReportLab.
Compatible con Windows sin dependencias externas (GTK, etc).
"""

import os
from io import BytesIO
from datetime import datetime


def generar_pdf_analisis(resultados):
    """
    Genera un PDF con los resultados del análisis cualitativo usando ReportLab.
    
    Args:
        resultados (dict): Resultados del análisis
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        raise ImportError(
            "ReportLab no está instalado. Ejecuta: pip install reportlab"
        )
    
    # ============================================
    # DATOS
    # ============================================
    total_respuestas = resultados.get('total_respuestas', 0)
    total_preguntas = resultados.get('total_preguntas', 0)
    sentimientos = resultados.get('sentimientos', {})
    palabras_frecuentes = resultados.get('palabras_frecuentes', [])
    temas = resultados.get('temas', [])
    resultados_por_pregunta = resultados.get('resultados_por_pregunta', {})
    
    # Sentimiento predominante
    max_sent = max(
        sentimientos.get('positivo', 0),
        sentimientos.get('neutral', 0),
        sentimientos.get('negativo', 0)
    )
    if max_sent == sentimientos.get('positivo', 0):
        predominante = 'Positivo'
        color_pred = colors.HexColor('#198754')
    elif max_sent == sentimientos.get('negativo', 0):
        predominante = 'Negativo'
        color_pred = colors.HexColor('#dc3545')
    else:
        predominante = 'Neutral'
        color_pred = colors.HexColor('#6c757d')
    
    # ============================================
    # CREAR PDF
    # ============================================
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title='Análisis Cualitativo'
    )
    
    # ============================================
    # ESTILOS
    # ============================================
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#0d6efd'),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    estilo_fecha = ParagraphStyle(
        'Fecha',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    estilo_seccion = ParagraphStyle(
        'Seccion',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0d6efd'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#212529'),
        spaceBefore=10,
        spaceAfter=8
    )
    
    estilo_texto = ParagraphStyle(
        'Texto',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    
    estilo_label = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER
    )
    
    estilo_valor = ParagraphStyle(
        'Valor',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#0d6efd'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # ============================================
    # CONTENIDO
    # ============================================
    story = []
    
    # ENCABEZADO
    story.append(Paragraph("Análisis Cualitativo de Encuesta", estilo_titulo))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        estilo_fecha
    ))
    
    # ============================================
    # RESUMEN GENERAL
    # ============================================
    story.append(Paragraph("Resumen General", estilo_seccion))
    
    # Tabla de resumen
    resumen_data = [
        [
            Paragraph(f'<b>{total_respuestas}</b>', estilo_valor),
            Paragraph(f'<b>{total_preguntas}</b>', estilo_valor),
            Paragraph(f'<b>{predominante}</b>', estilo_valor),
            Paragraph(f'<b>{sentimientos.get("promedio", 0)}</b>', estilo_valor),
        ],
        [
            Paragraph('Respuestas analizadas', estilo_label),
            Paragraph('Preguntas analizadas', estilo_label),
            Paragraph('Sentimiento predominante', estilo_label),
            Paragraph('Score (-1 a 1)', estilo_label),
        ]
    ]
    
    tabla_resumen = Table(resumen_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 15))
    
    # ============================================
    # ANÁLISIS DE SENTIMIENTO
    # ============================================
    story.append(Paragraph("Análisis de Sentimiento", estilo_seccion))
    
    sent_data = [
        [
            Paragraph(f'<b>{sentimientos.get("positivo", 0)}</b>', 
                     ParagraphStyle('Pos', parent=estilo_valor, textColor=colors.HexColor('#198754'))),
            Paragraph(f'<b>{sentimientos.get("neutral", 0)}</b>', 
                     ParagraphStyle('Neu', parent=estilo_valor, textColor=colors.HexColor('#6c757d'))),
            Paragraph(f'<b>{sentimientos.get("negativo", 0)}</b>', 
                     ParagraphStyle('Neg', parent=estilo_valor, textColor=colors.HexColor('#dc3545'))),
        ],
        [
            Paragraph('Positivo', estilo_label),
            Paragraph('Neutral', estilo_label),
            Paragraph('Negativo', estilo_label),
        ]
    ]
    
    tabla_sent = Table(sent_data, colWidths=[5.3*cm, 5.3*cm, 5.3*cm])
    tabla_sent.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d1e7dd')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#e2e3e5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f8d7da')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(tabla_sent)
    story.append(Spacer(1, 15))
    
    # ============================================
    # TEMAS IDENTIFICADOS
    # ============================================
    if temas:
        story.append(Paragraph("Temas Identificados", estilo_seccion))
        
        for tema in temas:
            nombre = tema.get('nombre', 'Tema')
            palabras = tema.get('palabras_clave', [])[:10]
            
            tema_texto = f'<b>{nombre}</b><br/>'
            tema_texto += ' | '.join(palabras)
            
            tema_style = ParagraphStyle(
                f'Tema_{nombre}',
                parent=estilo_texto,
                backColor=colors.HexColor('#e7f1ff'),
                borderColor=colors.HexColor('#0d6efd'),
                borderWidth=0,
                borderPadding=8,
                leftIndent=10,
                spaceAfter=8
            )
            story.append(Paragraph(tema_texto, tema_style))
        
        story.append(Spacer(1, 10))
    
    # ============================================
    # PALABRAS FRECUENTES
    # ============================================
    if palabras_frecuentes:
        story.append(Paragraph("Palabras más Frecuentes", estilo_seccion))
        
        # Crear tabla de palabras (4 columnas)
        palabras_lista = palabras_frecuentes[:20]
        filas = []
        fila_actual = []
        
        for palabra, freq in palabras_lista:
            fila_actual.append(f'{palabra} ({freq})')
            if len(fila_actual) == 4:
                filas.append(fila_actual)
                fila_actual = []
        
        if fila_actual:
            while len(fila_actual) < 4:
                fila_actual.append('')
            filas.append(fila_actual)
        
        if filas:
            tabla_palabras = Table(filas, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            tabla_palabras.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(tabla_palabras)
        
        story.append(Spacer(1, 15))
    
    # ============================================
    # ANÁLISIS POR PREGUNTA
    # ============================================
    if resultados_por_pregunta:
        story.append(PageBreak())
        story.append(Paragraph("Análisis por Pregunta", estilo_seccion))
        
        for idx, (pregunta, datos) in enumerate(resultados_por_pregunta.items(), 1):
            total = datos.get('total_respuestas', 1) or 1
            pos = datos.get('sentimientos', {}).get('positivo', 0)
            neu = datos.get('sentimientos', {}).get('neutral', 0)
            neg = datos.get('sentimientos', {}).get('negativo', 0)
            
            pct_pos = (pos / total * 100) if total > 0 else 0
            pct_neu = (neu / total * 100) if total > 0 else 0
            pct_neg = (neg / total * 100) if total > 0 else 0
            
            # Título de pregunta
            story.append(Paragraph(f"#{idx}. {pregunta}", estilo_subtitulo))
            
            # Tabla de estadísticas
            stats_data = [
                [
                    Paragraph(f'<b>{datos.get("total_respuestas", 0)}</b>', estilo_valor),
                    Paragraph(f'<b>{pct_pos:.0f}%</b>', 
                             ParagraphStyle('P', parent=estilo_valor, textColor=colors.HexColor('#198754'))),
                    Paragraph(f'<b>{pct_neu:.0f}%</b>', 
                             ParagraphStyle('N', parent=estilo_valor, textColor=colors.HexColor('#6c757d'))),
                    Paragraph(f'<b>{pct_neg:.0f}%</b>', 
                             ParagraphStyle('Ng', parent=estilo_valor, textColor=colors.HexColor('#dc3545'))),
                ],
                [
                    Paragraph('Respuestas', estilo_label),
                    Paragraph('Positivo', estilo_label),
                    Paragraph('Neutral', estilo_label),
                    Paragraph('Negativo', estilo_label),
                ]
            ]
            
            tabla_stats = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            tabla_stats.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(tabla_stats)
            story.append(Spacer(1, 8))
            
            # Palabras frecuentes de esta pregunta
            palabras_preg = datos.get('palabras_frecuentes', [])
            if palabras_preg:
                palabras_texto = ' | '.join([f'{p} ({f})' for p, f in palabras_preg[:10]])
                story.append(Paragraph(
                    f'<b>Palabras frecuentes:</b> {palabras_texto}',
                    estilo_texto
                ))
                story.append(Spacer(1, 8))
            
            # Ejemplos
            ejemplos = datos.get('textos_ejemplo', [])
            if ejemplos:
                story.append(Paragraph('<b>Ejemplos de respuestas:</b>', estilo_texto))
                for ejemplo in ejemplos[:5]:
                    ejemplos_texto = f'&bull; "{ejemplo}"'
                    story.append(Paragraph(ejemplos_texto, 
                                         ParagraphStyle('Ej', parent=estilo_texto, leftIndent=15)))
            
            story.append(Spacer(1, 20))
    
    # ============================================
    # PIE DE PÁGINA
    # ============================================
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        '<i>Generado por el Sistema de Análisis de Encuestas</i>',
        ParagraphStyle('Footer', parent=estilo_texto, 
                      alignment=TA_CENTER, textColor=colors.HexColor('#999999'), fontSize=9)
    ))
    
    # ============================================
    # GENERAR PDF
    # ============================================
    doc.build(story)
    buffer.seek(0)
    return buffer