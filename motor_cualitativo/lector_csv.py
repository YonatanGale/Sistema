# motor_cualitativo/lector_csv.py
"""
Lector de CSV generados por el sistema de encuestas.
NO se conecta a la base de datos, solo lee el archivo CSV.
"""
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def leer_csv_encuestas(ruta_csv, usar_texto_analisis=True):
    """
    Lee un CSV generado por el sistema de encuestas y lo prepara para el motor.
    
    Args:
        ruta_csv (str): Ruta al archivo CSV
        usar_texto_analisis (bool): Si True, usa la columna 'texto_analisis'
                                     (que ya incluye pregunta + respuesta).
                                     Si False, usa solo 'respuesta_texto'.
    
    Returns:
        pd.DataFrame: DataFrame con columnas para el análisis
    """
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_csv}")
    
    # Leer el CSV con UTF-8
    df = pd.read_csv(ruta_csv, encoding='utf-8-sig')
    
    logger.info(f"📂 CSV cargado: {len(df)} filas")
    logger.info(f"📋 Columnas: {list(df.columns)}")
    
    # Validar columnas requeridas
    columnas_requeridas = ['id_pregunta', 'pregunta_texto', 'respuesta_texto']
    columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
    
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas en el CSV: {columnas_faltantes}")
    
    # Elegir la columna de texto para analizar
    if usar_texto_analisis and 'texto_analisis' in df.columns:
        columna_texto = 'texto_analisis'
        logger.info("🎯 Usando columna 'texto_analisis' (pregunta + respuesta)")
    else:
        # Construir el texto con pregunta + respuesta
        df['texto_analisis'] = df.apply(
            lambda row: f"Pregunta: {row['pregunta_texto']} Respuesta: {row['respuesta_texto']}",
            axis=1
        )
        columna_texto = 'texto_analisis'
        logger.info("🎯 Construyendo texto con pregunta + respuesta")
    
    # Eliminar filas con texto vacío o nulo
    df = df[df[columna_texto].notna()]
    df = df[df[columna_texto].astype(str).str.strip() != '']
    
    logger.info(f"✅ {len(df)} registros válidos tras limpieza")
    
    # Normalizar la columna para el motor
    df['texto'] = df[columna_texto].astype(str)
    
    return df


def leer_csv_agrupado_por_pregunta(ruta_csv):
    """
    Lee el CSV y agrupa las respuestas por pregunta.
    
    Returns:
        dict: {id_pregunta: {'pregunta': str, 'respuestas': list, 'df': DataFrame}}
    """
    df = leer_csv_encuestas(ruta_csv)
    
    grupos = {}
    for pregunta_id, grupo in df.groupby('id_pregunta'):
        pregunta_texto = grupo['pregunta_texto'].iloc[0] if 'pregunta_texto' in grupo.columns else f'Pregunta {pregunta_id}'
        grupos[pregunta_id] = {
            'pregunta': pregunta_texto,
            'respuestas': grupo['respuesta_texto'].tolist(),
            'df': grupo
        }
    
    logger.info(f"📊 {len(grupos)} preguntas encontradas en el CSV")
    return grupos