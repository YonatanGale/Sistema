# app/utils/exportar_datos.py

from sqlalchemy import distinct, func
import pandas as pd
from io import BytesIO
from app import db
from app.models import Encuesta, Pregunta, Opcion, Respuesta
from datetime import datetime


def exportar_datos_cualitativos(encuesta_id):
    """
    Exporta las preguntas cualitativas:
    - Texto libre
    - Texto ingresado en opción "Otro" (tanto en opción única como múltiple)
    Retorna un objeto BytesIO con el archivo Excel.
    """
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    # Obtener preguntas cualitativas (texto_libre + preguntas con opción "Otro")
    preguntas_cualitativas = []
    
    # 1. Preguntas de texto libre
    preguntas_texto = Pregunta.query.filter_by(
        encuesta_id=encuesta_id,
        tipo='texto_libre'
    ).order_by(Pregunta.orden).all()
    preguntas_cualitativas.extend(preguntas_texto)
    
    # 2. Preguntas que tienen opción "Otro" (aunque sean cuantitativas)
    preguntas_todas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    for p in preguntas_todas:
        if p.tiene_opcion_otro():
            preguntas_cualitativas.append(p)
    
    # Eliminar duplicados por ID
    preguntas_cualitativas = list({p.id: p for p in preguntas_cualitativas}.values())
    
    if not preguntas_cualitativas:
        return None
    
    # Obtener respuestas
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    # Agrupar respuestas por identificador
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        
        # Si es texto libre, guardar el texto
        if r.pregunta.tipo == 'texto_libre':
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre or ''
        
        # Si es "Otro" con texto (opción única o múltiple)
        elif r.pregunta.tiene_opcion_otro():
            # Para opción múltiple, el texto_libre contiene las opciones + "Otro: texto"
            # Extraer solo el texto después de "Otro:"
            if r.texto_libre and 'Otro:' in r.texto_libre:
                import re
                match = re.search(r'Otro:\s*(.+?)(?=,|$)', r.texto_libre)
                if match:
                    texto_otro = match.group(1).strip()
                    if texto_otro and texto_otro != 'Otro (sin especificar)':
                        datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = texto_otro
            # Para opción única, el texto está en texto_libre directamente
            elif r.opcion and r.opcion.es_otro() and r.texto_libre:
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre
    
    # Crear DataFrame
    data = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas_cualitativas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
        data.append(row)
    
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    if df.empty:
        return None
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Cualitativas', index=False)
        
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
    - Soporte para opción múltiple
    - La opción "Otro" aparece solo como opción (sin el texto ingresado)
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
    # 3. HOJA: RESPUESTAS INDIVIDUALES (CUANTITATIVO - SOLO NOMBRES DE OPCIONES)
    # ============================================
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        if r.pregunta.tipo != 'texto_libre':
            # Para opción múltiple, usar opciones_ids para obtener los nombres de las opciones
            if r.pregunta.tipo == 'opcion_multiple' and r.opciones_ids:
                # Obtener nombres de opciones desde opciones_ids
                ids = [int(x) for x in r.opciones_ids.split(',') if x]
                opciones_texto = []
                for id_opcion in ids:
                    opcion = Opcion.query.get(id_opcion)
                    if opcion:
                        opciones_texto.append(opcion.texto)
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = ', '.join(opciones_texto)
            elif r.opcion:
                # CUANTITATIVO: Solo mostrar el nombre de la opción "Otro", no el texto
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.opcion.texto
            else:
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = ''
    
    data_respuestas = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas_cuantitativas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
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
        
        if pregunta.tipo == 'opcion_multiple':
            # ============================================
            # CONTEO PARA OPCIÓN MÚLTIPLE (CON "OTRO")
            # ============================================
            conteo = {}
            for opcion in opciones:
                count = 0
                respuestas_multi = Respuesta.query.filter_by(
                    encuesta_id=encuesta_id,
                    pregunta_id=pregunta.id
                ).all()
                for r in respuestas_multi:
                    if r.opciones_ids:
                        ids = [int(x) for x in r.opciones_ids.split(',') if x]
                        if opcion.id in ids:
                            count += 1
                conteo[opcion.texto] = count
            
            total = Respuesta.query.filter_by(
                encuesta_id=encuesta_id,
                pregunta_id=pregunta.id
            ).filter(
                db.or_(
                    Respuesta.opciones_ids.isnot(None),
                    Respuesta.opcion_id.isnot(None)
                )
            ).count()
            
            if total == 0:
                total = sum(conteo.values())
            
            porcentajes = {}
            for opcion_texto in todas_las_opciones:
                count = conteo.get(opcion_texto, 0)
                porcentajes[opcion_texto] = round((count / total * 100), 2) if total > 0 else 0
                
        else:
            # ============================================
            # CONTEO PARA OPCIÓN ÚNICA (incluye "Otro")
            # ============================================
            conteo = {}
            for opcion in opciones:
                count = Respuesta.query.filter_by(
                    encuesta_id=encuesta_id,
                    pregunta_id=pregunta.id,
                    opcion_id=opcion.id
                ).count()
                conteo[opcion.texto] = count
            
            total = sum(conteo.values())
            
            porcentajes = {}
            for opcion_texto in todas_las_opciones:
                count = conteo.get(opcion_texto, 0)
                porcentajes[opcion_texto] = round((count / total * 100), 2) if total > 0 else 0
        
        # Crear fila de estadísticas
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
        
        # Si la pregunta tiene "Otro", agregar el conteo de "Otro"
        if pregunta.tiene_opcion_otro():
            for opcion in opciones:
                if opcion.es_otro():
                    fila['Otro'] = conteo.get(opcion.texto, 0)
        
        estadisticas.append(fila)
    
    df_estadisticas = pd.DataFrame(estadisticas)

    # ============================================
    # CREAR ARCHIVO EXCEL
    # ============================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
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