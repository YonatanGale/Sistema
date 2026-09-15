# app/utils/exportar_cualitativo_csv.py
import os
import re
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


def exportar_respuestas_cualitativas(encuesta_id):
    """
    Exporta las respuestas cualitativas (texto libre y opciones "Otro")
    a un archivo CSV compatible con el motor cualitativo.
    """
    encuesta = Encuesta.query.get(encuesta_id)
    
    if not encuesta:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'Encuesta no encontrada'}
    
    # Obtener preguntas cualitativas (texto libre + preguntas con opción "Otro")
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    preguntas_cualitativas = []
    for p in preguntas:
        if p.tipo == 'texto_libre' or p.tiene_opcion_otro():
            preguntas_cualitativas.append(p)
    
    if not preguntas_cualitativas:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'No hay preguntas cualitativas'}
    
    # Obtener respuestas
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    # Agrupar por identificador
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        
        # Texto libre
        if r.pregunta.tipo == 'texto_libre' and r.texto_libre:
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre
        
        # Opción "Otro"
        elif r.opcion and r.opcion.es_otro() and r.texto_libre:
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre
    
    if not datos_agrupados:
        return {'ruta': None, 'nombre_archivo': None, 'mensaje': 'No hay respuestas cualitativas'}
    
    # Crear DataFrame
    data = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas_cualitativas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # ============================================
    # ✅ NOMBRE LIMPIO (SIN TILDES NI CARACTERES ESPECIALES)
    # ============================================
    titulo_limpio = limpiar_nombre_archivo(encuesta.titulo)
    nombre_archivo = f"cualitativo_{encuesta_id}_{titulo_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Guardar en la carpeta exports
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    ruta_archivo = os.path.join(exports_dir, nombre_archivo)
    df.to_csv(ruta_archivo, index=False, encoding='utf-8-sig')
    
    return {
        'ruta': ruta_archivo,
        'nombre_archivo': nombre_archivo,
        'total_registros': len(df),
        'mensaje': f'✅ {len(df)} respuestas exportadas exitosamente'
    }