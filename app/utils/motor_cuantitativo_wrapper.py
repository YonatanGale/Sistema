# app/utils/motor_cuantitativo_wrapper.py
"""
Wrapper para ejecutar el motor cuantitativo desde Flask.
- Devuelve PNG (base64) + plotly_json para render en el navegador.
- Incluye datos crudos para drill-down.
- Persiste las figuras JSON en _graficos_plotly.json para el dashboard.
"""

import os
import sys
import json
import base64
import math
import shutil
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOTOR_DIR = os.path.join(BASE_DIR, 'motor_cuantitativo')

if MOTOR_DIR not in sys.path:
    sys.path.insert(0, MOTOR_DIR)


# ============================================
# LIMPIEZA
# ============================================
def _limpiar_analisis_anteriores(directorio_padre):
    if not os.path.exists(directorio_padre):
        return
    try:
        for d in os.listdir(directorio_padre):
            if (d.startswith('motor_') or d.startswith('encuesta_')) \
                    and os.path.isdir(os.path.join(directorio_padre, d)):
                try:
                    shutil.rmtree(os.path.join(directorio_padre, d))
                    logger.info(f"  🗑️  Eliminado: {d}")
                except Exception as e:
                    logger.warning(f"  ⚠️ No se pudo eliminar {d}: {e}")
    except Exception as e:
        logger.error(f"❌ Error limpieza: {e}")


def _limpiar_temporales(directorio_temp):
    if not os.path.exists(directorio_temp):
        return
    for a in os.listdir(directorio_temp):
        ruta = os.path.join(directorio_temp, a)
        if os.path.isfile(ruta) and not a.startswith('.gitkeep'):
            try:
                os.remove(ruta)
            except Exception:
                pass


# ============================================
# SERIALIZACIÓN JSON SEGURA
# ============================================
def _es_nan(v):
    if v is None:
        return True
    try:
        r = pd.isna(v)
        return bool(r) if isinstance(r, (bool, np.bool_)) else False
    except (TypeError, ValueError):
        return False


def _limpiar_valor(v):
    if _es_nan(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.ndarray):
        return [_limpiar_valor(x) for x in v.tolist()]
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    return v


def _df_a_lista(df):
    if df is None or df.empty:
        return []
    return [
        {k: _limpiar_valor(v) for k, v in rec.items()}
        for rec in df.to_dict('records')
    ]


def _codificar_imagen_base64(ruta_png):
    if not ruta_png or not os.path.exists(ruta_png):
        return None
    with open(ruta_png, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def _json_safe(obj):
    """Limpia un objeto anidado para asegurar que sea JSON-safe."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [_json_safe(x) for x in obj.tolist()]
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    return obj


# ============================================
# PRINCIPAL
# ============================================
def analizar_con_motor_cuantitativo(archivo):
    try:
        from motor_cuantitativo import AnalizadorCuantitativo
    except ImportError as e:
        logger.error(f"Error importando motor: {e}")
        return {'success': False, 'message': f'Error al cargar el motor: {str(e)}'}

    directorio_padre = os.path.join(BASE_DIR, 'motor_cuantitativo', 'data', 'resultados')
    directorio_temp = os.path.join(BASE_DIR, 'motor_cuantitativo', 'data', 'temp')

    logger.info("=" * 60)
    logger.info("🧹 Limpieza de análisis anteriores...")
    logger.info("=" * 60)
    _limpiar_analisis_anteriores(directorio_padre)
    _limpiar_temporales(directorio_temp)

    os.makedirs(directorio_temp, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_temp = f"temp_{timestamp}_{archivo.filename}"
    ruta_temp = os.path.join(directorio_temp, nombre_temp)
    archivo.save(ruta_temp)

    directorio_resultados = os.path.join(directorio_padre, f'motor_{timestamp}')
    os.makedirs(directorio_resultados, exist_ok=True)

    try:
        analizador = AnalizadorCuantitativo(directorio_resultados=directorio_resultados)
        resultados = analizador.analizar_completo(
            ruta_csv=ruta_temp,
            generar_graficos=True,
            guardar_excel=True,
            guardar_json=True,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error en el análisis: {str(e)}'}
    finally:
        try:
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)
        except Exception:
            pass

    metadata = resultados['metadata']

    # ============================================
    # SERIALIZAR TABLAS
    # ============================================
    estadisticas = _df_a_lista(resultados.get('estadisticas_descriptivas'))
    frecuencias = _df_a_lista(resultados.get('frecuencias'))

    corr_raw = resultados.get('correlaciones', {})
    correlaciones = {
        'matriz': _df_a_lista(corr_raw.get('matriz')),
        'pares_significativos': _df_a_lista(corr_raw.get('pares_significativos')),
    }

    grupos_raw = resultados.get('grupos', {})
    grupos = {
        'grupo_pregunta': grupos_raw.get('grupo_pregunta'),
        'resumen': _df_a_lista(grupos_raw.get('resumen')),
    }

    indice_raw = resultados.get('indice_satisfaccion', {})
    indice = {
        'indice_global': _limpiar_valor(indice_raw.get('indice_global')),
        'por_pregunta': _df_a_lista(indice_raw.get('por_pregunta')),
    }

    # ============================================
    # GRÁFICOS: {nombre: {nombre, base64, plotly_json}}
    # ============================================
    graficos = {}
    archivos_graficos = resultados.get('archivos', {}).get('graficos', {})

    for nombre, datos in archivos_graficos.items():
        if isinstance(datos, dict):
            ruta_png = datos.get('png')
            plotly_json = datos.get('plotly_json')
        else:
            ruta_png = datos
            plotly_json = None

        b64 = _codificar_imagen_base64(ruta_png)

        nombre_limpio = (
            nombre.replace('_', ' ')
            .replace('P ', 'P')
            .title()
        )

        graficos[nombre] = {
            'nombre': nombre_limpio,
            'base64': b64,
            'plotly_json': _json_safe(plotly_json) if plotly_json else None,
        }

    # ============================================
    # DATOS CRUDOS (para drill-down)
    # ============================================
    df_cat = resultados.get('df_categorico')
    datos_crudos = []
    if df_cat is not None and not df_cat.empty:
        datos_crudos = [
            {k: _limpiar_valor(v) for k, v in rec.items()}
            for rec in df_cat.to_dict('records')
        ]

    # ============================================
    # PERSISTIR plotly_json EN DISCO (para dashboard)
    # ============================================
    graficos_json_disk = {}
    for nombre, datos in archivos_graficos.items():
        if isinstance(datos, dict) and datos.get('plotly_json'):
            graficos_json_disk[nombre] = datos['plotly_json']

    if graficos_json_disk:
        try:
            ruta_json = os.path.join(directorio_resultados, '_graficos_plotly.json')
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(graficos_json_disk, f, ensure_ascii=False)
            logger.info(f"💾 Figuras Plotly persistidas: {len(graficos_json_disk)}")
        except Exception as e:
            logger.warning(f"No se pudieron persistir figuras: {e}")

    # ============================================
    # PERSISTIR RUTAS
    # ============================================
    preguntas_sin_datos = resultados.get('preguntas_sin_datos', [])
    archivo_excel = resultados.get('archivos', {}).get('excel')
    archivo_json_resultados = resultados.get('archivos', {}).get('json')

    rutas_meta = {
        'directorio': directorio_resultados,
        'excel': archivo_excel,
        'json': archivo_json_resultados,
        'timestamp': timestamp,
        'preguntas_sin_datos': preguntas_sin_datos,
    }

    with open(os.path.join(directorio_resultados, '_rutas.json'), 'w') as f:
        json.dump(rutas_meta, f)

    logger.info(f"✅ Análisis guardado en: {directorio_resultados}")

    return {
        'success': True,
        'metadata': {
            'titulo': metadata.get('titulo', ''),
            'descripcion': metadata.get('descripcion', ''),
            'total_encuestados': metadata.get('total_encuestados', 0),
            'total_preguntas': len(metadata.get('preguntas', [])),
            'preguntas': metadata.get('preguntas', []),
        },
        'metadata_preguntas': metadata.get('preguntas', []),
        'estadisticas_descriptivas': estadisticas,
        'frecuencias': frecuencias,
        'correlaciones': correlaciones,
        'grupos': grupos,
        'indice_satisfaccion': indice,
        'graficos': graficos,
        'datos_crudos': datos_crudos,
        'preguntas_sin_datos': preguntas_sin_datos,
        'directorio_resultados': directorio_resultados,
        'timestamp': timestamp,
        'archivo_excel': os.path.basename(archivo_excel) if archivo_excel else None,
    }