# app/utils/motor_integrado_wrapper.py
"""
Wrapper que integra AMBOS motores en un solo flujo + cruce multimodal.
"""

import os
import sys
import json
import io
import logging
from datetime import datetime

import pandas as pd
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# HELPERS
# ============================================
def _leer_csv_unificado(contenido_bytes):
    texto = contenido_bytes.decode('utf-8-sig')
    lineas = texto.split('\n', 1)

    if len(lineas) < 2 or not lineas[0].startswith('# METADATA:'):
        raise ValueError(
            "El CSV debe empezar con '# METADATA: {...}'. "
            "Usa el botón 'Exportar completo' del sistema."
        )

    metadata = json.loads(lineas[0].replace('# METADATA:', '').strip())
    df = pd.read_csv(io.StringIO(lineas[1]))
    return metadata, df


def _separar_preguntas(metadata):
    cuanti, cuali = [], []
    for p in metadata['preguntas']:
        if p['tipo'] == 'texto_libre':
            cuali.append(p)
        else:
            cuanti.append(p)
    return cuanti, cuali


def _construir_csv_cuantitativo(metadata, df, preguntas_cuanti):
    metadata_cuanti = dict(metadata)
    metadata_cuanti['preguntas'] = preguntas_cuanti
    cols = ['Identificador'] + [f"P{p['id']}" for p in preguntas_cuanti]
    cols = [c for c in cols if c in df.columns]
    df_cuanti = df[cols].copy()
    buffer = io.StringIO()
    buffer.write(f"# METADATA: {json.dumps(metadata_cuanti, ensure_ascii=False)}\n")
    df_cuanti.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8-sig')


def _construir_csv_cualitativo(df, preguntas_cuali):
    data = {'Identificador': df['Identificador'].tolist()}
    for p in preguntas_cuali:
        col = f"P{p['id']}"
        data[p['texto']] = df[col].tolist() if col in df.columns else [''] * len(df)
    df_cuali = pd.DataFrame(data)
    buffer = io.StringIO()
    df_cuali.to_csv(buffer, index=False)
    return buffer.getvalue().encode('utf-8-sig')


def _a_file_storage(bytes_data, filename):
    buffer = io.BytesIO(bytes_data)
    buffer.seek(0)
    return FileStorage(stream=buffer, filename=filename, content_type='text/csv')


# ============================================
# ANÁLISIS INTEGRADO
# ============================================
def analizar_con_motores_integrados(archivo):
    try:
        contenido = archivo.read()
        metadata, df = _leer_csv_unificado(contenido)

        total_cuanti = sum(1 for p in metadata['preguntas'] if p['tipo'] != 'texto_libre')
        total_cuali = sum(1 for p in metadata['preguntas'] if p['tipo'] == 'texto_libre')

        logger.info(f"📊 CSV integrado: {len(df)} filas")
        logger.info(f"   Cuantitativas: {total_cuanti} | Cualitativas: {total_cuali}")

        preguntas_cuanti, preguntas_cuali = _separar_preguntas(metadata)

        resultado_cuanti = None
        resultado_cuali = None
        cruces = []
        errores = []

        # ---------- 1. MOTOR CUANTITATIVO ----------
        if preguntas_cuanti:
            try:
                logger.info("▶️ Motor CUANTITATIVO...")
                csv_cuanti = _construir_csv_cuantitativo(metadata, df, preguntas_cuanti)
                fs_cuanti = _a_file_storage(csv_cuanti, 'cuantitativo_filtrado.csv')

                from app.utils.motor_cuantitativo_wrapper import analizar_con_motor_cuantitativo
                resultado_cuanti = analizar_con_motor_cuantitativo(fs_cuanti)

                if not resultado_cuanti.get('success'):
                    errores.append(f"Cuantitativo: {resultado_cuanti.get('message', 'error')}")
                    resultado_cuanti = None
                else:
                    logger.info("✅ Cuantitativo OK")
            except Exception as e:
                logger.error(f"❌ Cuantitativo: {e}")
                import traceback; traceback.print_exc()
                errores.append(f"Cuantitativo: {str(e)}")

        # ---------- 2. MOTOR CUALITATIVO ----------
        if preguntas_cuali:
            try:
                logger.info("▶️ Motor CUALITATIVO...")
                csv_cuali = _construir_csv_cualitativo(df, preguntas_cuali)
                fs_cuali = _a_file_storage(csv_cuali, 'cualitativo_filtrado.csv')

                from app.utils.motor_wrapper import analizar_con_motor
                resultado_cuali = analizar_con_motor(fs_cuali)

                if not resultado_cuali.get('success'):
                    errores.append(f"Cualitativo: {resultado_cuali.get('message', 'error')}")
                    resultado_cuali = None
                else:
                    logger.info("✅ Cualitativo OK")
            except Exception as e:
                logger.error(f"❌ Cualitativo: {e}")
                import traceback; traceback.print_exc()
                errores.append(f"Cualitativo: {str(e)}")

        # ---------- 3. CRUCES MULTIMODALES ----------
        if preguntas_cuanti and preguntas_cuali:
            try:
                logger.info("▶️ Cruces multimodales (cuantitativo × cualitativo)...")
                from app.utils.cruce_multimodal import analizar_cruces_multimodales
                from app.utils.motor_wrapper import obtener_analizador

                analizador = obtener_analizador()
                cruces = analizar_cruces_multimodales(
                    df=df,
                    metadata=metadata,
                    analizador=analizador,
                    solo_significativos=False,
                    max_pares=25,
                )
                logger.info(f"✅ {len(cruces)} cruces calculados")
            except Exception as e:
                logger.error(f"❌ Cruces: {e}")
                import traceback; traceback.print_exc()
                errores.append(f"Cruces: {str(e)}")

        if resultado_cuanti is None and resultado_cuali is None:
            return {
                'success': False,
                'message': 'No se pudo procesar ningún motor. ' + ' | '.join(errores),
            }

        return {
            'success': True,
            'metadata': {
                'titulo': metadata.get('titulo', ''),
                'descripcion': metadata.get('descripcion', ''),
                'total_encuestados': metadata.get('total_encuestados', len(df)),
                'total_preguntas': len(metadata.get('preguntas', [])),
                'cuantitativas': total_cuanti,
                'cualitativas': total_cuali,
                'preguntas': metadata.get('preguntas', []),
            },
            'cuantitativo': resultado_cuanti,
            'cualitativo': resultado_cuali,
            'cruces_multimodales': cruces,
            'advertencias': errores,
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Error al procesar CSV integrado: {str(e)}'}