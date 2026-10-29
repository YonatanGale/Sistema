# app/utils/cruce_multimodal.py
"""
Análisis de correlación entre variables cuantitativas y cualitativas.

Para cada par (pregunta cerrada, pregunta de texto libre) evalúa si la
distribución de sentimientos del texto varía significativamente según la
opción elegida en la pregunta cerrada.
"""

import logging
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

SENTIMIENTOS = ['Positivo', 'Neutral', 'Negativo']

MIN_OPCIONES = 2
MAX_OPCIONES = 8
MIN_FILAS_POR_OPCION = 3
MIN_TOTAL = 10


def _normalizar_sentimiento(s):
    if not s:
        return 'Neutral'
    s = str(s).lower()
    if 'positiv' in s:
        return 'Positivo'
    if 'negativ' in s:
        return 'Negativo'
    return 'Neutral'


def _chi2_y_cramer(tabla):
    try:
        chi2, p, dof, expected = stats.chi2_contingency(tabla)
    except Exception as e:
        logger.warning(f"χ² falló: {e}")
        return None

    n = int(tabla.values.sum())
    if n == 0:
        return None

    k = min(tabla.shape[0] - 1, tabla.shape[1] - 1)
    cramers_v = float(np.sqrt(chi2 / (n * k))) if k > 0 else 0.0

    celdas_pequenas = int((expected < 5).sum())
    advertencia = None
    if celdas_pequenas > 0.2 * expected.size:
        advertencia = (
            f'{celdas_pequenas} celdas con frecuencia esperada < 5. '
            'El χ² puede no ser fiable.'
        )

    return {
        'chi2': round(float(chi2), 3),
        'p_value': round(float(p), 4),
        'dof': int(dof),
        'n': n,
        'cramers_v': round(cramers_v, 3),
        'significativo': bool(p < 0.05),
        'advertencia': advertencia,
    }


def _interpretar_cramers_v(v):
    if v < 0.1:
        return 'Muy débil'
    if v < 0.2:
        return 'Débil'
    if v < 0.3:
        return 'Moderada'
    if v < 0.5:
        return 'Fuerte'
    return 'Muy fuerte'


def _precalcular_sentimientos(df, cualis, analizador):
    cache = {}
    for p in cualis:
        col = f"P{p['id']}"
        if col not in df.columns:
            continue
        textos = df[col].astype(str)
        
        # ✅ FILTRO: ignorar nulos, "nan", vacíos y puntos
        mask = (
            textos.str.strip().ne('') & 
            textos.str.lower().ne('nan') & 
            textos.str.lower().ne('none') & 
            textos.str.strip().ne('.')
        )
        
        if not mask.any():
            continue
        try:
            logger.info(f"  Sentimiento para {col} ({mask.sum()} textos)...")
            sent_df = analizador.analizar_sentimiento(textos[mask].tolist())
            if sent_df.empty:
                continue
            sent_norm = sent_df['sentimiento'].apply(_normalizar_sentimiento).tolist()
            cache[col] = dict(zip(df.index[mask].tolist(), sent_norm))
        except Exception as e:
            logger.warning(f"  Fallo en {col}: {e}")
            continue
    return cache


def _filtrar_cuanti_categoricas(df, metadata):
    resultado = []
    for p in metadata.get('preguntas', []):
        if p['tipo'] not in ('opcion_unica', 'opcion_multiple',
                             'seleccion_si_no', 'escala_likert'):
            continue
        col = f"P{p['id']}"
        if col not in df.columns:
            continue
        vals = df[col].dropna().astype(str)
        vals = vals[vals.str.strip().ne('')]
        if p['tipo'] == 'opcion_multiple':
            opciones = set()
            for v in vals:
                for o in str(v).split(';'):
                    o = o.strip()
                    if o:
                        opciones.add(o)
        else:
            opciones = set(vals.tolist())
        if MIN_OPCIONES <= len(opciones) <= MAX_OPCIONES:
            resultado.append(p)
    return resultado


def _expandir_multiple(df, col):
    filas = []
    for idx, val in df[col].items():
        if pd.isna(val) or str(val).strip() == '':
            continue
        for op in str(val).split(';'):
            op = op.strip()
            if op:
                filas.append((idx, op))
    if not filas:
        return pd.DataFrame(columns=['idx', 'opcion'])
    return pd.DataFrame(filas, columns=['idx', 'opcion'])


def analizar_cruces_multimodales(
    df,
    metadata,
    analizador,
    min_filas_por_opcion=MIN_FILAS_POR_OPCION,
    max_pares=25,
    solo_significativos=False,
):
    if df is None or df.empty:
        return []

    cuantis = _filtrar_cuanti_categoricas(df, metadata)
    cualis = [p for p in metadata.get('preguntas', []) if p['tipo'] == 'texto_libre']

    if not cuantis:
        logger.info("  Sin preguntas cuantitativas categóricas válidas para cruzar")
        return []
    if not cualis:
        logger.info("  Sin preguntas cualitativas para cruzar")
        return []

    logger.info(f"  Cruzando {len(cuantis)} cuantis × {len(cualis)} cualis")

    cache_sent = _precalcular_sentimientos(df, cualis, analizador)
    if not cache_sent:
        return []

    pares = []

    for p_cuanti in cuantis:
        col_cuanti = f"P{p_cuanti['id']}"
        es_multiple = (p_cuanti['tipo'] == 'opcion_multiple')

        for p_cuali in cualis:
            col_cuali = f"P{p_cuali['id']}"
            if col_cuali not in cache_sent:
                continue

            sent_map = cache_sent[col_cuali]
            indices_con_sent = set(sent_map.keys())

            mask_cuanti = df[col_cuanti].notna() & df[col_cuanti].astype(str).str.strip().ne('')
            df_base = df[mask_cuanti & df.index.isin(indices_con_sent)].copy()
            if df_base.empty:
                continue

            if es_multiple:
                expandido = _expandir_multiple(df_base, col_cuanti)
                if expandido.empty:
                    continue
                expandido['sentimiento'] = expandido['idx'].map(sent_map)
                tabla = pd.crosstab(expandido['opcion'], expandido['sentimiento'])
                df_para_ejemplos = expandido
                col_opcion = 'opcion'
                col_sent = 'sentimiento'
            else:
                df_base['_sentimiento'] = df_base.index.map(sent_map)
                tabla = pd.crosstab(df_base[col_cuanti], df_base['_sentimiento'])
                df_para_ejemplos = df_base
                col_opcion = col_cuanti
                col_sent = '_sentimiento'

            for s in SENTIMIENTOS:
                if s not in tabla.columns:
                    tabla[s] = 0
            tabla = tabla[SENTIMIENTOS]

            tabla = tabla[tabla.sum(axis=1) >= min_filas_por_opcion]
            if len(tabla) < 2:
                continue
            if int(tabla.values.sum()) < MIN_TOTAL:
                continue

            test = _chi2_y_cramer(tabla)
            if test is None:
                continue

            if solo_significativos and not test['significativo']:
                continue

            tabla_pct = tabla.div(tabla.sum(axis=1), axis=0) * 100
            distribucion = []
            for opcion in tabla.index:
                fila = tabla.loc[opcion]
                fila_pct = tabla_pct.loc[opcion]
                total_grupo = int(fila.sum())

                # ✅ LÓGICA MEJORADA DE EJEMPLOS (Filtra "nan" y vacíos)
                textos_grupo = (
                    df_para_ejemplos[df_para_ejemplos[col_opcion] == opcion]
                    .index.unique().tolist()
                )
                
                ejemplos = []
                for idx in textos_grupo:
                    t = df.loc[idx, col_cuali] if idx in df.index else ''
                    t_str = str(t).strip() if t else ""
                    
                    # Solo agregamos si el texto es real y no es basura
                    if t_str and t_str.lower() not in ['nan', 'none', 'null', 'n/a', ''] and t_str != '.':
                        ejemplos.append(t_str[:250])
                        
                    if len(ejemplos) >= 3:
                        break

                distribucion.append({
                    'opcion': str(opcion),
                    'total': total_grupo,
                    'positivo': int(fila['Positivo']),
                    'neutral': int(fila['Neutral']),
                    'negativo': int(fila['Negativo']),
                    'positivo_pct': round(float(fila_pct['Positivo']), 1),
                    'neutral_pct': round(float(fila_pct['Neutral']), 1),
                    'negativo_pct': round(float(fila_pct['Negativo']), 1),
                    'sentimiento_predominante': str(fila.idxmax()),
                    'ejemplos': ejemplos,
                })

            pares.append({
                'pregunta_cuanti': {
                    'id': p_cuanti['id'],
                    'texto': p_cuanti['texto'],
                    'tipo': p_cuanti['tipo'],
                },
                'pregunta_cuali': {
                    'id': p_cuali['id'],
                    'texto': p_cuali['texto'],
                },
                'distribucion': distribucion,
                'test': {
                    **test,
                    'interpretacion_v': _interpretar_cramers_v(test['cramers_v']),
                },
                'total_cruzado': int(tabla.values.sum()),
            })

    pares.sort(key=lambda x: (not x['test']['significativo'], -x['test']['cramers_v']))

    logger.info(f"  → {len(pares)} cruces calculados")
    return pares[:max_pares]