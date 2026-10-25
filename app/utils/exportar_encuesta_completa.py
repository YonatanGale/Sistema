# app/utils/exportar_encuesta_completa.py
"""
Exporta TODAS las respuestas de una encuesta (cuantitativas + cualitativas)
a un único CSV con metadata que marca el tipo de cada pregunta.

Además, para preguntas con opción "Otro", añade una columna P{id}_otro
que contiene el texto libre escrito por el encuestado. Esa columna se
marca como 'texto_libre' en la metadata para que el motor cualitativo
la analice por separado.

Formato:
    # METADATA: {...JSON...}
    Identificador,P5,P6,P10,P10_otro,P30
    R0001,2007,Femenino,Otro,"Soy estudiante de...",...
"""

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


def _tiene_otro(pregunta):
    """True si la pregunta tiene una opción que sea 'Otro'."""
    return pregunta.tiene_opcion_otro()


def exportar_encuesta_completa(encuesta_id):
    """Exporta TODAS las preguntas (cuantitativas + cualitativas) en un CSV único."""
    encuesta = Encuesta.query.get(encuesta_id)

    if not encuesta:
        return {'ruta': None, 'nombre_archivo': None,
                'mensaje': 'Encuesta no encontrada'}

    preguntas = Pregunta.query.filter(
        Pregunta.encuesta_id == encuesta_id
    ).order_by(Pregunta.orden).all()

    if not preguntas:
        return {'ruta': None, 'nombre_archivo': None,
                'mensaje': 'No hay preguntas en esta encuesta'}

    # ============================================
    # 1. METADATA (con entradas extra para "Otro")
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

        # ✅ Si la pregunta tiene "Otro", añadir una entrada extra
        #    para el texto libre de esa opción (solo aplica a opción única/múltiple)
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
    # 2. CONSTRUIR DATOS (formato ancho)
    # ============================================
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()

    # Cache de opciones para no hacer N queries
    cache_opciones = {o.id: o for o in Opcion.query.all()}

    datos_por_identificador = {}
    for r in respuestas:
        ident = r.identificador_respuesta
        if ident not in datos_por_identificador:
            datos_por_identificador[ident] = {}

        pregunta = r.pregunta
        col_pid = f"P{pregunta.id}"
        col_otro = f"P{pregunta.id}_otro"

        # ---- Texto libre ----
        if pregunta.tipo == 'texto_libre':
            datos_por_identificador[ident][col_pid] = (
                str(r.texto_libre) if r.texto_libre else ''
            )

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

            # Si eligió "Otro" y escribió texto, guardarlo en P{id}_otro
            if tiene_otro_seleccionado and r.texto_libre:
                datos_por_identificador[ident][col_otro] = str(r.texto_libre)

        # ---- Opción única / Likert / Sí-No ----
        elif r.opcion:
            datos_por_identificador[ident][col_pid] = r.opcion.texto

            # Si la opción elegida es "Otro" y hay texto, guardarlo aparte
            if r.opcion.es_otro() and r.texto_libre:
                datos_por_identificador[ident][col_otro] = str(r.texto_libre)

        else:
            datos_por_identificador[ident][col_pid] = ''

    # ============================================
    # 3. CONSTRUIR COLUMNAS DEL DATAFRAME
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
        return {'ruta': None, 'nombre_archivo': None,
                'mensaje': 'No hay respuestas para exportar'}

    df = pd.DataFrame(filas, columns=columnas)

    # ============================================
    # 4. GUARDAR CSV
    # ============================================
    titulo_limpio = limpiar_nombre_archivo(encuesta.titulo)
    nombre_archivo = (
        f"completo_{encuesta_id}_{titulo_limpio}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    exports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'exports'
    )
    os.makedirs(exports_dir, exist_ok=True)

    ruta_archivo = os.path.join(exports_dir, nombre_archivo)

    with open(ruta_archivo, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(f"# METADATA: {json.dumps(metadata, ensure_ascii=False)}\n")
        df.to_csv(f, index=False)

    # ---- Contadores ----
    cuantitativas = sum(1 for p in preguntas if p.tipo != 'texto_libre')
    cualitativas = sum(1 for p in preguntas if p.tipo == 'texto_libre')
    con_otro = sum(
        1 for p in preguntas
        if p.tipo in ('opcion_unica', 'opcion_multiple') and _tiene_otro(p)
    )

    return {
        'ruta': ruta_archivo,
        'nombre_archivo': nombre_archivo,
        'total_registros': len(df),
        'total_preguntas': len(preguntas),
        'cuantitativas': cuantitativas,
        'cualitativas': cualitativas,
        'columnas_otro': con_otro,
        'mensaje': (
            f'✅ {len(df)} respuestas exportadas '
            f'({cuantitativas} cuantitativas + {cualitativas} texto libre'
            + (f' + {con_otro} textos de "Otro"' if con_otro else '')
            + ')'
        ),
    }