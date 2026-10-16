# motor_cuantitativo/lector_datos.py
"""
Lee el CSV cuantitativo exportado desde el sistema Flask.
El CSV tiene la metadata embebida en la primera línea con formato:
    # METADATA: {...JSON...}
"""

import os
import json
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def leer_csv_cuantitativo(ruta_csv):
    """
    Lee el CSV cuantitativo y devuelve:
    - metadata: dict con info de la encuesta y preguntas
    - df: DataFrame con las respuestas (formato ancho)
    
    Args:
        ruta_csv: Ruta al archivo CSV
    
    Returns:
        dict con keys: 'metadata', 'df', 'ruta'
    """
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_csv}")
    
    # ============================================
    # 1. LEER PRIMERA LÍNEA (METADATA)
    # ============================================
    with open(ruta_csv, 'r', encoding='utf-8-sig') as f:
        primera_linea = f.readline().strip()
    
    if not primera_linea.startswith('# METADATA:'):
        raise ValueError(
            "El archivo no tiene el formato esperado. "
            "La primera línea debe empezar con '# METADATA:'"
        )
    
    json_str = primera_linea.replace('# METADATA:', '').strip()
    metadata = json.loads(json_str)
    
    logger.info(f"📋 Encuesta: {metadata['titulo']}")
    logger.info(f"📊 Total encuestados: {metadata['total_encuestados']}")
    logger.info(f"❓ Preguntas cuantitativas: {len(metadata['preguntas'])}")
    
    # ============================================
    # 2. LEER EL RESTO COMO DATAFRAME
    # ============================================
    df = pd.read_csv(ruta_csv, encoding='utf-8-sig', skiprows=1)
    
    logger.info(f"✅ {len(df)} filas cargadas")
    
    # ============================================
    # 3. VALIDAR COLUMNAS
    # ============================================
    if 'Identificador' not in df.columns:
        raise ValueError("El CSV no tiene la columna 'Identificador'")
    
    # Validar que estén todas las columnas de preguntas
    columnas_esperadas = ['Identificador'] + [f"P{p['id']}" for p in metadata['preguntas']]
    columnas_faltantes = [c for c in columnas_esperadas if c not in df.columns]
    
    if columnas_faltantes:
        logger.warning(f"⚠️ Columnas faltantes: {columnas_faltantes}")
    
    return {
        'metadata': metadata,
        'df': df,
        'ruta': ruta_csv
    }


def convertir_a_numerico(df, metadata):
    """
    Convierte las respuestas de texto a valores numéricos según los valores
    definidos en cada opción.
    
    Para preguntas de opción múltiple, devuelve una columna de listas.
    
    Returns:
        dict con keys:
        - 'df_numerico': DataFrame con valores numéricos (solo escalas Likert/Sí-No)
        - 'df_categorico': DataFrame con valores de texto originales
        - 'mapeos': dict con mapeos {pregunta_id: {texto: valor}}
    """
    df_numerico = df[['Identificador']].copy()
    df_categorico = df[['Identificador']].copy()
    mapeos = {}
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        
        if col not in df.columns:
            continue
        
        # Guardar versión categórica
        df_categorico[col] = df[col]
        
        tipo = pregunta['tipo']
        opciones = pregunta['opciones']
        valores = pregunta['valores']
        
        # Crear mapeo texto → valor numérico
        mapeo = {}
        for i, opcion in enumerate(opciones):
            valor = valores[i] if i < len(valores) and valores[i] is not None else None
            if valor is not None:
                try:
                    mapeo[opcion] = float(valor)
                except (ValueError, TypeError):
                    # Si el valor no es numérico, usar índice + 1
                    mapeo[opcion] = i + 1
            else:
                # Si no hay valor asignado, usar índice + 1 (para Likert)
                if tipo in ['escala_likert', 'opcion_unica']:
                    mapeo[opcion] = i + 1
        
        mapeos[pregunta['id']] = mapeo
        
        # Convertir solo preguntas que tengan mapeo numérico
        if tipo in ['escala_likert', 'seleccion_si_no', 'opcion_unica'] and mapeo:
            df_numerico[col] = df[col].map(mapeo)
        else:
            # Para opción múltiple, dejar el texto (se procesará aparte)
            df_numerico[col] = df[col]
    
    return {
        'df_numerico': df_numerico,
        'df_categorico': df_categorico,
        'mapeos': mapeos
    }