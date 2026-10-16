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
    """Lee el CSV cuantitativo y devuelve metadata + DataFrame."""
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_csv}")

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

    df = pd.read_csv(ruta_csv, encoding='utf-8-sig', skiprows=1)

    logger.info(f"✅ {len(df)} filas cargadas")

    if 'Identificador' not in df.columns:
        raise ValueError("El CSV no tiene la columna 'Identificador'")

    columnas_esperadas = ['Identificador'] + [f"P{p['id']}" for p in metadata['preguntas']]
    columnas_faltantes = [c for c in columnas_esperadas if c not in df.columns]

    if columnas_faltantes:
        logger.warning(f"⚠️ Columnas faltantes: {columnas_faltantes}")

    return {
        'metadata': metadata,
        'df': df,
        'ruta': ruta_csv
    }


# ============================================
# ✅ FIX P5: búsqueda robusta en el mapeo
# ============================================
def _buscar_en_mapeo(valor, mapeo):
    """
    Busca un valor en un mapeo {texto: numero} probando distintas
    representaciones. Resuelve el bug de P5 (año) donde el CSV trae
    enteros (2007) pero el mapeo tiene strings ("2007").

    Prueba en orden:
      1. Valor tal cual
      2. str(valor).strip()
      3. String sin ".0" (por si pandas leyó como float)
      4. int(float(str))  y  str(int(...))
    """
    if pd.isna(valor):
        return None

    # 1. Directo
    try:
        if valor in mapeo:
            return mapeo[valor]
    except (TypeError, KeyError):
        pass

    # 2. Como string limpio
    s = str(valor).strip()
    if s in mapeo:
        return mapeo[s]

    # 3. Sin .0
    if s.endswith('.0'):
        s2 = s[:-2]
        if s2 in mapeo:
            return mapeo[s2]

    # 4. Como entero
    try:
        i = int(float(s))
        if i in mapeo:
            return mapeo[i]
        if str(i) in mapeo:
            return mapeo[str(i)]
    except (ValueError, TypeError):
        pass

    return None


def convertir_a_numerico(df, metadata):
    """
    Convierte las respuestas de texto a valores numéricos según los
    valores definidos en cada opción.

    ✅ FIX: usa _buscar_en_mapeo() en lugar de .map() directo,
    lo que resuelve el caso de columnas numéricas (P5 = años).
    """
    df_numerico = df[['Identificador']].copy()
    df_categorico = df[['Identificador']].copy()
    mapeos = {}

    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"

        if col not in df.columns:
            continue

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
                    mapeo[opcion] = i + 1
            else:
                if tipo in ['escala_likert', 'opcion_unica']:
                    mapeo[opcion] = i + 1

        mapeos[pregunta['id']] = mapeo

        # ✅ FIX: búsqueda robusta en el mapeo
        if tipo in ['escala_likert', 'seleccion_si_no', 'opcion_unica'] and mapeo:
            df_numerico[col] = df[col].apply(lambda x: _buscar_en_mapeo(x, mapeo))
        else:
            df_numerico[col] = df[col]

    return {
        'df_numerico': df_numerico,
        'df_categorico': df_categorico,
        'mapeos': mapeos
    }