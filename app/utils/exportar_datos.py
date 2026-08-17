# app/utils/exportar_datos.py
from sqlalchemy import distinct, func
import pandas as pd
from io import BytesIO
from app import db
from app.models import Encuesta, Pregunta, Opcion, Respuesta
from datetime import datetime


def exportar_datos_cualitativos(encuesta_id):
    """
    Exporta las preguntas cualitativas (texto libre) y sus respuestas.
    Retorna un objeto BytesIO con el archivo Excel.
    """
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    # Obtener preguntas de tipo texto_libre
    preguntas_cualitativas = Pregunta.query.filter_by(
        encuesta_id=encuesta_id,
        tipo='texto_libre'
    ).order_by(Pregunta.orden).all()
    
    if not preguntas_cualitativas:
        return None
    
    # Obtener respuestas agrupadas por identificador
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    # Agrupar respuestas por identificador
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        # Solo guardar respuestas de preguntas cualitativas
        if r.pregunta.tipo == 'texto_libre':
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre or ''
    
    # Crear DataFrame
    data = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas_cualitativas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Si no hay datos, devolver None
    if df.empty:
        return None
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Cualitativas', index=False)
        
        # Agregar metadatos
        total_encuestados = len(datos_agrupados)
        metadata = pd.DataFrame({
            'Encuesta': [encuesta.titulo],
            'Fecha_exportacion': [datetime.now().strftime('%Y-%m-%d %H:%M')],
            'Total_encuestados': [total_encuestados],
            'Total_preguntas_cualitativas': [len(preguntas_cualitativas)]
        })
        metadata.to_excel(writer, sheet_name='Metadatos', index=False)
    
    output.seek(0)
    return output


def exportar_datos_cuantitativos(encuesta_id):
    """
    Exporta preguntas cuantitativas (cerradas) con:
    - Todas las opciones posibles (incluyendo las no seleccionadas)
    - Valores numéricos asociados
    - Estadísticas completas
    """
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    # Obtener preguntas cuantitativas (todo excepto texto_libre)
    preguntas_cuantitativas = Pregunta.query.filter(
        Pregunta.encuesta_id == encuesta_id,
        Pregunta.tipo != 'texto_libre'
    ).order_by(Pregunta.orden).all()
    
    if not preguntas_cuantitativas:
        return None
    
    # ============================================
    # 1. HOJA: CONTEXTO DE LA ENCUESTA
    # ============================================
    # Forma correcta de contar identificadores únicos
    total_encuestados = db.session.query(
        func.count(distinct(Respuesta.identificador_respuesta))
    ).filter(Respuesta.encuesta_id == encuesta_id).scalar()
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).count()
    
    contexto = pd.DataFrame({
        'Encuesta': [encuesta.titulo],
        'Descripcion': [encuesta.descripcion or 'Sin descripción'],
        'Fecha_creacion': [encuesta.fecha_creacion.strftime('%Y-%m-%d %H:%M')],
        'Fecha_exportacion': [datetime.now().strftime('%Y-%m-%d %H:%M')],
        'Total_encuestados': [total_encuestados],
        'Total_respuestas': [total_respuestas],
        'Total_preguntas_cuantitativas': [len(preguntas_cuantitativas)]
    })

    # ============================================
    # 2. HOJA: ESTRUCTURA DE PREGUNTAS
    # ============================================
    estructura = []
    for pregunta in preguntas_cuantitativas:
        opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).order_by(Opcion.orden).all()
        
        opciones_lista = []
        valores_lista = []
        for opcion in opciones:
            opciones_lista.append(opcion.texto)
            valores_lista.append(opcion.valor if opcion.valor else '')
        
        estructura.append({
            'Pregunta_ID': pregunta.id,
            'Texto': pregunta.texto,
            'Tipo': pregunta.tipo,
            'Requiere_respuesta': 'Sí' if pregunta.requerida else 'No',
            'Opciones': ' | '.join(opciones_lista),
            'Valores_asignados': ' | '.join(valores_lista),
            'Numero_de_opciones': len(opciones)
        })
    
    df_estructura = pd.DataFrame(estructura)

    # ============================================
    # 3. HOJA: RESPUESTAS INDIVIDUALES
    # ============================================
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        if r.pregunta.tipo != 'texto_libre':
            if r.opcion:
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.opcion.texto
                if r.opcion.valor:
                    datos_agrupados[r.identificador_respuesta][f"{r.pregunta.texto}_valor"] = r.opcion.valor
            else:
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = ''
    
    data_respuestas = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas_cuantitativas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
            opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).order_by(Opcion.orden).all()
            tiene_valores = any(o.valor for o in opciones)
            if tiene_valores:
                row[f"{pregunta.texto}_valor"] = respuestas_dict.get(f"{pregunta.texto}_valor", '')
        data_respuestas.append(row)
    
    df_respuestas = pd.DataFrame(data_respuestas)

    # ============================================
    # 4. HOJA: ESTADÍSTICAS COMPLETAS
    # ============================================
    estadisticas = []
    for pregunta in preguntas_cuantitativas:
        opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).order_by(Opcion.orden).all()
        
        todas_las_opciones = [o.texto for o in opciones]
        valores_opciones = [o.valor if o.valor else '' for o in opciones]
        
        conteo = {}
        for opcion in opciones:
            count = Respuesta.query.filter_by(
                pregunta_id=pregunta.id,
                opcion_id=opcion.id
            ).count()
            conteo[opcion.texto] = count
        
        total = sum(conteo.values())
        
        porcentajes = {}
        for opcion_texto in todas_las_opciones:
            count = conteo.get(opcion_texto, 0)
            porcentajes[opcion_texto] = round((count / total * 100), 2) if total > 0 else 0
        
        fila = {
            'Pregunta_ID': pregunta.id,
            'Pregunta': pregunta.texto,
            'Tipo': pregunta.tipo,
            'Total_respuestas': total,
        }
        
        for i, opcion_texto in enumerate(todas_las_opciones):
            count = conteo.get(opcion_texto, 0)
            fila[f'Opcion_{i+1}'] = opcion_texto
            fila[f'Valor_{i+1}'] = valores_opciones[i] if i < len(valores_opciones) else ''
            fila[f'Conteo_{i+1}'] = count
            fila[f'Porcentaje_{i+1}'] = porcentajes.get(opcion_texto, 0)
        
        if pregunta.tipo == 'escala_likert':
            valores_numericos = []
            for opcion in opciones:
                if opcion.valor and opcion.valor.isdigit():
                    count = Respuesta.query.filter_by(
                        pregunta_id=pregunta.id,
                        opcion_id=opcion.id
                    ).count()
                    valores_numericos.extend([int(opcion.valor)] * count)
            
            if valores_numericos:
                import statistics
                fila['Media'] = round(statistics.mean(valores_numericos), 2)
                fila['Mediana'] = statistics.median(valores_numericos)
                try:
                    fila['Moda'] = statistics.mode(valores_numericos)
                except statistics.StatisticsError:
                    fila['Moda'] = 'Multiple'
                fila['Desviacion_estandar'] = round(statistics.stdev(valores_numericos), 2) if len(valores_numericos) > 1 else 0
                fila['Minimo'] = min(valores_numericos)
                fila['Maximo'] = max(valores_numericos)
        
        estadisticas.append(fila)
    
    df_estadisticas = pd.DataFrame(estadisticas)

    # ============================================
    # CREAR ARCHIVO EXCEL
    # ============================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Asegurar que al menos una hoja tenga datos
        if not contexto.empty:
            contexto.to_excel(writer, sheet_name='Contexto', index=False)
        
        if not df_estructura.empty:
            df_estructura.to_excel(writer, sheet_name='Estructura_preguntas', index=False)
        
        if not df_respuestas.empty:
            df_respuestas.to_excel(writer, sheet_name='Respuestas_individuales', index=False)
        
        if not df_estadisticas.empty:
            df_estadisticas.to_excel(writer, sheet_name='Estadisticas', index=False)
    
    output.seek(0)
    return output