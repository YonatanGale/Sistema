# app/utils/exportar_cuantitativo_csv.py
"""
Exporta los datos cuantitativos a un CSV con metadata embebida en la primera línea.
Formato:
    # METADATA: {...JSON...}
    Identificador,P8,P9,P10
    R0001,Bueno,Talleres;Retiros,Sí
"""

import os
import re
import json
import unicodedata
import pandas as pd
from datetime import datetime
from app import db
from app.models import Encuesta, Pregunta, Respuesta, Opcion


def limpiar_nombre_archivo(texto, max_length=30):
    """Limpia un texto para usarlo como nombre de archivo"""
    if not texto:
        return "sin_titulo"
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'[^a-zA-Z0-9_-]', '_', texto)
    texto = re.sub(r'_+', '_', texto)
    texto = texto.strip('_')
    if len(texto) > max_length:
        texto = texto[:max_length].rstrip('_')
    return texto if texto else "sin_titulo"


def exportar_respuestas_cuantitativas(encuesta_id):
    """
    Exporta las respuestas cuantitativas a un CSV con metadata embebida.
    
    Retorna:
        dict con:
        - ruta: path al archivo CSV generado
        - nombre_archivo: nombre del archivo
        - total_registros: cantidad de encuestados
        - mensaje: mensaje descriptivo
    """
    encuesta = Encuesta.query.get(encuesta_id)
    
    if not encuesta:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'Encuesta no encontrada'}
    
    # Obtener preguntas cuantitativas (todo excepto texto_libre)
    preguntas = Pregunta.query.filter(
        Pregunta.encuesta_id == encuesta_id,
        Pregunta.tipo != 'texto_libre'
    ).order_by(Pregunta.orden).all()
    
    if not preguntas:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'No hay preguntas cuantitativas'}
    
    # ============================================
    # 1. CONSTRUIR METADATA
    # ============================================
    preguntas_meta = []
    for p in preguntas:
        opciones = Opcion.query.filter_by(pregunta_id=p.id).order_by(Opcion.orden).all()
        preguntas_meta.append({
            'id': p.id,
            'tipo': p.tipo,
            'texto': p.texto,
            'requerida': bool(p.requerida),
            'opciones': [o.texto for o in opciones],
            'valores': [o.valor if o.valor else None for o in opciones]
        })
    
    # Contar encuestados únicos
    total_encuestados = db.session.query(
        Respuesta.identificador_respuesta
    ).filter(Respuesta.encuesta_id == encuesta_id).distinct().count()
    
    metadata = {
        'encuesta_id': encuesta.id,
        'titulo': encuesta.titulo,
        'descripcion': encuesta.descripcion or '',
        'fecha_exportacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_encuestados': total_encuestados,
        'preguntas': preguntas_meta
    }
    
    # ============================================
    # 2. CONSTRUIR DATOS EN FORMATO ANCHO
    # ============================================
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    # Agrupar por identificador
    datos_por_identificador = {}
    for r in respuestas:
        ident = r.identificador_respuesta
        if ident not in datos_por_identificador:
            datos_por_identificador[ident] = {}
        
        pregunta = r.pregunta
        
        # Solo procesar preguntas cuantitativas
        if pregunta.tipo == 'texto_libre':
            continue
        
        # ==========================================
        # VALOR SEGÚN TIPO DE PREGUNTA
        # ==========================================
        if pregunta.tipo == 'opcion_multiple':
            # Usar opciones_ids para obtener los textos de las opciones
            if r.opciones_ids:
                ids = [int(x) for x in r.opciones_ids.split(',') if x]
                textos = []
                for id_op in ids:
                    op = Opcion.query.get(id_op)
                    if op:
                        textos.append(op.texto)
                datos_por_identificador[ident][f"P{pregunta.id}"] = ';'.join(textos)
            else:
                datos_por_identificador[ident][f"P{pregunta.id}"] = ''
        
        elif r.opcion:
            # Opción única, Likert, Sí/No
            datos_por_identificador[ident][f"P{pregunta.id}"] = r.opcion.texto
        
        else:
            datos_por_identificador[ident][f"P{pregunta.id}"] = ''
    
    # Crear DataFrame
    columnas = ['Identificador'] + [f"P{p.id}" for p in preguntas]
    filas = []
    for ident, valores in datos_por_identificador.items():
        fila = {'Identificador': ident}
        for p in preguntas:
            fila[f"P{p.id}"] = valores.get(f"P{p.id}", '')
        filas.append(fila)
    
    if not filas:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'No hay respuestas cuantitativas'}
    
    df = pd.DataFrame(filas, columns=columnas)
    
    # ============================================
    # 3. GUARDAR CSV CON METADATA EMBEBIDA
    # ============================================
    titulo_limpio = limpiar_nombre_archivo(encuesta.titulo)
    nombre_archivo = f"cuantitativo_{encuesta_id}_{titulo_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    ruta_archivo = os.path.join(exports_dir, nombre_archivo)
    
    with open(ruta_archivo, 'w', encoding='utf-8-sig', newline='') as f:
        # Primera línea: metadata como JSON
        f.write(f"# METADATA: {json.dumps(metadata, ensure_ascii=False)}\n")
        # Datos
        df.to_csv(f, index=False)
    
    return {
        'ruta': ruta_archivo,
        'nombre_archivo': nombre_archivo,
        'total_registros': len(df),
        'mensaje': f'✅ {len(df)} respuestas exportadas exitosamente'
    }