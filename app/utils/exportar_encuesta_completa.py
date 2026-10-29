# app/utils/exportar_encuesta_completa.py
import os
import re
import json
import unicodedata
from datetime import datetime
import pandas as pd
from app import db
from app.models import Encuesta, Pregunta, Respuesta, Opcion

def limpiar_nombre_archivo(texto, max_length=30):
    if not texto:
        return "sin_titulo"
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'[^a-zA-Z0-9_-]', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    if len(texto) > max_length:
        texto = texto[:max_length].rstrip('_')
    return texto or "sin_titulo"

def extraer_textos_otro(campo_libre):
    """
    Extrae los textos del formato [OTRO P1] texto [OTRO P6] otro texto.
    """
    if not campo_libre or pd.isna(campo_libre):
        return {}
    
    texto = str(campo_libre)
    resultado = {}
    patron = r'\[OTRO P(\d+)\]\s*(.*?)(?=\[OTRO P\d+\]|$)'
    matches = re.finditer(patron, texto, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        p_id = match.group(1)
        respuesta = match.group(2).strip().strip('"').strip("'")
        if respuesta and respuesta != '.':
            resultado[p_id] = respuesta
            
    return resultado

def _tiene_otro(pregunta):
    return pregunta.tiene_opcion_otro()

def exportar_encuesta_completa(encuesta_id):
    encuesta = Encuesta.query.get(encuesta_id)
    if not encuesta:
        return {'ruta': None, 'mensaje': 'Encuesta no encontrada'}

    preguntas = Pregunta.query.filter(
        Pregunta.encuesta_id == encuesta_id
    ).order_by(Pregunta.orden).all()

    if not preguntas:
        return {'ruta': None, 'mensaje': 'No hay preguntas en esta encuesta'}

    # ============================================
    # 1. METADATA
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
            'valores': [o.valor if o.valor else None for o in opciones],
        })

        if p.tipo in ('opcion_unica', 'opcion_multiple') and _tiene_otro(p):
            preguntas_meta.append({
                'id': f"{p.id}_otro",
                'tipo': 'texto_libre',
                'texto': f"{p.texto} (Otro)",
                'requerida': False,
                'opciones': [],
                'valores': [],
            })

    total_encuestados = db.session.query(
        Respuesta.identificador_respuesta
    ).filter(Respuesta.encuesta_id == encuesta_id).distinct().count()

    metadata = {
        'encuesta_id': encuesta.id,
        'titulo': encuesta.titulo,
        'descripcion': encuesta.descripcion or '',
        'fecha_exportacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_encuestados': total_encuestados,
        'preguntas': preguntas_meta,
    }

    # ============================================
    # 2. DATOS (¡AQUÍ ESTÁ EL ARREGLO!)
    # ============================================
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    cache_opciones = {o.id: o for o in Opcion.query.all()}

    # Primero, agrupamos todo el texto libre (comentarios y campo_libre) por identificador
    # para poder buscar patrones [OTRO Px]
    textos_por_identificador = {}
    for r in respuestas:
        ident = r.identificador_respuesta
        if ident not in textos_por_identificador:
            textos_por_identificador[ident] = ""
        
        if r.texto_libre:
            # Si es un campo libre con prefijo [OTRO Px], lo acumulamos
            if "[OTRO P" in str(r.texto_libre).upper() or "[COMENTARIO P" in str(r.texto_libre).upper():
                textos_por_identificador[ident] += " " + str(r.texto_libre)
            # Si es la columna campo_libre directa, también
            elif r.pregunta.texto.lower() == 'campo libre' or r.pregunta.texto.lower() == 'campo_libre':
                 textos_por_identificador[ident] += " " + str(r.texto_libre)

    # Ahora extraemos los textos de "Otro" de cada identificador
    otros_extraidos = {ident: extraer_textos_otro(txt) for ident, txt in textos_por_identificador.items()}

    datos_por_identificador = {}
    for r in respuestas:
        ident = r.identificador_respuesta
        if ident not in datos_por_identificador:
            datos_por_identificador[ident] = {}

        pregunta = r.pregunta
        col_pid = f"P{pregunta.id}"
        col_otro = f"P{pregunta.id}_otro"

        # ---- Texto libre puro ----
        if pregunta.tipo == 'texto_libre':
            texto = str(r.texto_libre).strip() if r.texto_libre else ''
            # Limpiamos prefijos técnicos para el campo general
            texto = re.sub(r'\[COMENTARIO P\d+\]', '', texto).strip()
            if texto and texto != '.':
                datos_por_identificador[ident][col_pid] = texto

        # ---- Opción múltiple ----
        elif pregunta.tipo == 'opcion_multiple':
            textos = []
            tiene_otro_seleccionado = False
            if r.opciones_ids:
                ids = [int(x) for x in r.opciones_ids.split(',') if x.strip()]
                for id_op in ids:
                    op = cache_opciones.get(id_op)
                    if op:
                        textos.append(op.texto)
                        if op.es_otro():
                            tiene_otro_seleccionado = True

            datos_por_identificador[ident][col_pid] = ';'.join(textos)

            if tiene_otro_seleccionado:
                # Buscamos el texto extraído del identificador
                texto_real = otros_extraidos.get(ident, {}).get(str(pregunta.id), '')
                if texto_real:
                    datos_por_identificador[ident][col_otro] = texto_real

        # ---- Opción única / Likert ----
        elif r.opcion:
            datos_por_identificador[ident][col_pid] = r.opcion.texto

            if r.opcion.es_otro():
                # Buscamos el texto extraído del identificador
                texto_real = otros_extraidos.get(ident, {}).get(str(pregunta.id), '')
                if texto_real:
                    datos_por_identificador[ident][col_otro] = texto_real

        else:
            datos_por_identificador[ident][col_pid] = ''

    # ============================================
    # 3. CONSTRUIR DATAFRAME
    # ============================================
    columnas = ['Identificador']
    for p in preguntas:
        columnas.append(f"P{p.id}")
        if p.tipo in ('opcion_unica', 'opcion_multiple') and _tiene_otro(p):
            columnas.append(f"P{p.id}_otro")

    filas = []
    for ident, valores in datos_por_identificador.items():
        fila = {'Identificador': ident}
        for col in columnas[1:]:
            fila[col] = valores.get(col, '')
        filas.append(fila)

    if not filas:
        return {'ruta': None, 'mensaje': 'No hay respuestas para exportar'}

    df = pd.DataFrame(filas, columns=columnas)

    # ============================================
    # 4. GUARDAR
    # ============================================
    titulo_limpio = limpiar_nombre_archivo(encuesta.titulo)
    nombre_archivo = f"completo_{encuesta_id}_{titulo_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    ruta_archivo = os.path.join(exports_dir, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(f"# METADATA: {json.dumps(metadata, ensure_ascii=False)}\n")
        df.to_csv(f, index=False)

    cuantitativas = sum(1 for p in preguntas if p.tipo != 'texto_libre')
    cualitativas = sum(1 for p in preguntas if p.tipo == 'texto_libre')
    
    return {
        'ruta': ruta_archivo,
        'nombre_archivo': nombre_archivo,
        'total_registros': len(df),
        'total_preguntas': len(preguntas),
        'cuantitativas': cuantitativas,
        'cualitativas': cualitativas,
        'mensaje': f'✅ {len(df)} respuestas exportadas exitosamente',
    }