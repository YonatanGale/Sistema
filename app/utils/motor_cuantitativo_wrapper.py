# app/utils/motor_cuantitativo_wrapper.py
"""
Wrapper para ejecutar el motor cuantitativo desde Flask.
Convierte todos los valores NaN a None para que el JSON sea válido.
Auto-limpieza: elimina análisis anteriores antes de ejecutar uno nuevo.
"""

import os
import sys
import json
import base64
import math
import shutil
import logging
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Ruta al motor
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOTOR_DIR = os.path.join(BASE_DIR, 'motor_cuantitativo')

if MOTOR_DIR not in sys.path:
    sys.path.insert(0, MOTOR_DIR)


# ============================================
# AUTO-LIMPIEZA DE ANÁLISIS ANTERIORES
# ============================================

def _limpiar_analisis_anteriores(directorio_padre):
    """
    Elimina TODOS los análisis anteriores en el directorio padre.
    Solo mantiene el análisis más reciente.
    
    Args:
        directorio_padre: ruta a motor_cuantitativo/data/resultados/
    """
    if not os.path.exists(directorio_padre):
        logger.info(f"📁 Directorio no existe aún: {directorio_padre}")
        return
    
    try:
        # Listar solo carpetas que empiecen con 'motor_' o 'encuesta_'
        carpetas_analisis = [
            d for d in os.listdir(directorio_padre)
            if (d.startswith('motor_') or d.startswith('encuesta_'))
            and os.path.isdir(os.path.join(directorio_padre, d))
        ]
        
        if not carpetas_analisis:
            logger.info("🧹 No hay análisis anteriores que limpiar")
            return
        
        logger.info(f"🧹 Limpiando {len(carpetas_analisis)} análisis anteriores...")
        
        for carpeta in carpetas_analisis:
            ruta = os.path.join(directorio_padre, carpeta)
            try:
                shutil.rmtree(ruta)
                logger.info(f"  🗑️ Eliminado: {carpeta}")
            except Exception as e:
                logger.warning(f"  ⚠️ No se pudo eliminar {carpeta}: {e}")
        
        logger.info(f"✅ Limpieza completada")
        
    except Exception as e:
        logger.error(f"❌ Error en limpieza: {e}")


def _limpiar_temporales(directorio_temp):
    """
    Elimina archivos temporales del directorio temp.
    """
    if not os.path.exists(directorio_temp):
        return
    
    try:
        for archivo in os.listdir(directorio_temp):
            ruta = os.path.join(directorio_temp, archivo)
            if os.path.isfile(ruta) and not archivo.startswith('.gitkeep'):
                try:
                    os.remove(ruta)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar temporal {archivo}: {e}")
    except Exception as e:
        logger.warning(f"Error limpiando temporales: {e}")


# ============================================
# SERIALIZACIÓN JSON SEGURA
# ============================================

def _es_nan(valor):
    """Detecta si un valor es NaN/NaT/None de forma segura."""
    if valor is None:
        return True
    try:
        resultado = pd.isna(valor)
        if isinstance(resultado, (bool, np.bool_)):
            return bool(resultado)
        return False
    except (TypeError, ValueError):
        return False


def _limpiar_valor(valor):
    """Convierte cualquier valor a un tipo serializable en JSON."""
    if _es_nan(valor):
        return None
    
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        f = float(valor)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(valor, (np.bool_,)):
        return bool(valor)
    if isinstance(valor, np.ndarray):
        return [_limpiar_valor(x) for x in valor.tolist()]
    
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    
    if isinstance(valor, float):
        if math.isnan(valor) or math.isinf(valor):
            return None
        return valor
    
    return valor


def _df_a_lista(df):
    """Convierte DataFrame a lista de dicts con JSON válido (sin NaN)."""
    if df is None or df.empty:
        return []
    
    resultado = []
    for record in df.to_dict('records'):
        fila_limpia = {k: _limpiar_valor(v) for k, v in record.items()}
        resultado.append(fila_limpia)
    
    return resultado


def _codificar_imagen_base64(ruta_png):
    """Convierte un PNG a base64 para embeber en JSON."""
    if not os.path.exists(ruta_png):
        return None
    with open(ruta_png, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def analizar_con_motor_cuantitativo(archivo):
    """
    Ejecuta el análisis cuantitativo sobre el archivo CSV subido.
    
    Args:
        archivo: FileStorage de Flask
    
    Returns:
        dict con los resultados (listo para jsonify)
    """
    try:
        from motor_cuantitativo import AnalizadorCuantitativo
    except ImportError as e:
        logger.error(f"Error importando el motor: {e}")
        return {'success': False, 'message': f'Error al cargar el motor: {str(e)}'}
    
    # ============================================
    # 1. AUTO-LIMPIEZA DE ANÁLISIS ANTERIORES
    # ============================================
    directorio_padre = os.path.join(
        BASE_DIR, 'motor_cuantitativo', 'data', 'resultados'
    )
    directorio_temp = os.path.join(
        BASE_DIR, 'motor_cuantitativo', 'data', 'temp'
    )
    
    logger.info("=" * 60)
    logger.info("🧹 Auto-limpieza de análisis anteriores...")
    logger.info("=" * 60)
    
    _limpiar_analisis_anteriores(directorio_padre)
    _limpiar_temporales(directorio_temp)
    
    # ============================================
    # 2. GUARDAR ARCHIVO TEMPORAL
    # ============================================
    os.makedirs(directorio_temp, exist_ok=True)
    
    nombre_original = archivo.filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_temp = f"temp_{timestamp}_{nombre_original}"
    ruta_temp = os.path.join(directorio_temp, nombre_temp)
    
    archivo.save(ruta_temp)
    
    # ============================================
    # 3. EJECUTAR ANÁLISIS
    # ============================================
    directorio_resultados = os.path.join(
        directorio_padre, f'motor_{timestamp}'
    )
    os.makedirs(directorio_resultados, exist_ok=True)
    
    try:
        analizador = AnalizadorCuantitativo(directorio_resultados=directorio_resultados)
        
        resultados = analizador.analizar_completo(
            ruta_csv=ruta_temp,
            generar_graficos=True,
            guardar_excel=True,
            guardar_json=True
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error en el análisis: {str(e)}'}
    finally:
        # Limpiar archivo temporal
        try:
            if os.path.exists(ruta_temp):
                os.remove(ruta_temp)
        except Exception:
            pass
    
    # ============================================
    # 4. PREPARAR RESPUESTA JSON
    # ============================================
    metadata = resultados['metadata']
    
    estadisticas = _df_a_lista(resultados.get('estadisticas_descriptivas'))
    frecuencias = _df_a_lista(resultados.get('frecuencias'))
    
    correlaciones_raw = resultados.get('correlaciones', {})
    correlaciones = {
        'matriz': _df_a_lista(correlaciones_raw.get('matriz')),
        'pares_significativos': _df_a_lista(correlaciones_raw.get('pares_significativos'))
    }
    
    grupos_raw = resultados.get('grupos', {})
    grupos = {
        'grupo_pregunta': grupos_raw.get('grupo_pregunta'),
        'resumen': _df_a_lista(grupos_raw.get('resumen'))
    }
    
    indice_raw = resultados.get('indice_satisfaccion', {})
    indice = {
        'indice_global': _limpiar_valor(indice_raw.get('indice_global')),
        'por_pregunta': _df_a_lista(indice_raw.get('por_pregunta'))
    }
    
    # ============================================
    # 5. GRÁFICOS COMO BASE64
    # ============================================
    graficos = {}
    archivos_graficos = resultados.get('archivos', {}).get('graficos', {})
    
    for nombre, ruta in archivos_graficos.items():
        b64 = _codificar_imagen_base64(ruta)
        if b64:
            nombre_limpio = nombre.replace('_', ' ').title()
            graficos[nombre] = {
                'nombre': nombre_limpio,
                'base64': b64
            }
    
    # ============================================
    # 6. GUARDAR RUTAS PARA PDF/EXCEL
    # ============================================
    archivo_excel = resultados.get('archivos', {}).get('excel')
    archivo_json = resultados.get('archivos', {}).get('json')
    
    rutas_meta = {
        'directorio': directorio_resultados,
        'excel': archivo_excel,
        'json': archivo_json,
        'timestamp': timestamp
    }
    
    with open(os.path.join(directorio_resultados, '_rutas.json'), 'w') as f:
        json.dump(rutas_meta, f)
    
    logger.info(f"✅ Análisis guardado en: {directorio_resultados}")
    
    # ============================================
    # 7. RESPUESTA FINAL
    # ============================================
    return {
        'success': True,
        'metadata': {
            'titulo': metadata.get('titulo', ''),
            'descripcion': metadata.get('descripcion', ''),
            'total_encuestados': metadata.get('total_encuestados', 0),
            'total_preguntas': len(metadata.get('preguntas', [])),
            'preguntas': metadata.get('preguntas', [])
        },
        'estadisticas_descriptivas': estadisticas,
        'frecuencias': frecuencias,
        'correlaciones': correlaciones,
        'grupos': grupos,
        'indice_satisfaccion': indice,
        'graficos': graficos,
        'directorio_resultados': directorio_resultados,
        'timestamp': timestamp,
        'archivo_excel': os.path.basename(archivo_excel) if archivo_excel else None
    }