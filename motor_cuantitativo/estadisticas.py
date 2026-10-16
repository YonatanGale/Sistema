# motor_cuantitativo/estadisticas.py
"""
Módulo de estadísticas para análisis cuantitativo.
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


# ============================================
# ESTADÍSTICAS DESCRIPTIVAS
# ============================================

def calcular_estadisticas_descriptivas(df_numerico, metadata):
    """
    Calcula estadísticas descriptivas para cada pregunta.
    
    Returns:
        pd.DataFrame con columnas:
        - Pregunta_ID, Tipo, Total_Respuestas, Media, Mediana, Moda,
          Desv_Est, Min, Max, Q1, Q3, Rango_Intercuartil
    """
    resultados = []
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        tipo = pregunta['tipo']
        
        if col not in df_numerico.columns:
            continue
        
        # Obtener valores numéricos no nulos
        valores = pd.to_numeric(df_numerico[col], errors='coerce').dropna()
        
        fila = {
            'Pregunta_ID': pregunta['id'],
            'Pregunta': pregunta['texto'],
            'Tipo': tipo,
            'Total_Respuestas': len(valores)
        }
        
        if len(valores) > 0 and tipo in ['escala_likert', 'seleccion_si_no', 'opcion_unica']:
            fila['Media'] = round(valores.mean(), 3)
            fila['Mediana'] = round(valores.median(), 3)
            try:
                fila['Moda'] = valores.mode().iloc[0]
            except (IndexError, KeyError):
                fila['Moda'] = None
            fila['Desv_Est'] = round(valores.std(), 3) if len(valores) > 1 else 0
            fila['Min'] = valores.min()
            fila['Max'] = valores.max()
            fila['Q1'] = round(valores.quantile(0.25), 3)
            fila['Q3'] = round(valores.quantile(0.75), 3)
            fila['Rango_Intercuartil'] = round(fila['Q3'] - fila['Q1'], 3)
        else:
            for k in ['Media', 'Mediana', 'Moda', 'Desv_Est', 'Min', 'Max', 'Q1', 'Q3', 'Rango_Intercuartil']:
                fila[k] = None
        
        resultados.append(fila)
    
    return pd.DataFrame(resultados)


def calcular_frecuencias(df_categorico, metadata):
    """
    Calcula la frecuencia y porcentaje de cada opción por pregunta.
    
    Returns:
        pd.DataFrame con columnas:
        - Pregunta_ID, Pregunta, Opcion, Frecuencia, Porcentaje
    """
    resultados = []
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        tipo = pregunta['tipo']
        
        if col not in df_categorico.columns:
            continue
        
        if tipo == 'opcion_multiple':
            # Contar apariciones individuales de cada opción
            conteo = {op: 0 for op in pregunta['opciones']}
            for valor in df_categorico[col].dropna():
                if not valor:
                    continue
                opciones_marcadas = [o.strip() for o in str(valor).split(';') if o.strip()]
                for op in opciones_marcadas:
                    if op in conteo:
                        conteo[op] += 1
            
            total = sum(conteo.values())
            
            for opcion, freq in conteo.items():
                resultados.append({
                    'Pregunta_ID': pregunta['id'],
                    'Pregunta': pregunta['texto'],
                    'Tipo': tipo,
                    'Opcion': opcion,
                    'Frecuencia': freq,
                    'Porcentaje': round((freq / total * 100), 2) if total > 0 else 0
                })
        else:
            # Opción única / Likert / Sí-No
            conteo = df_categorico[col].value_counts(dropna=True).to_dict()
            total = sum(conteo.values())
            
            for opcion in pregunta['opciones']:
                freq = conteo.get(opcion, 0)
                resultados.append({
                    'Pregunta_ID': pregunta['id'],
                    'Pregunta': pregunta['texto'],
                    'Tipo': tipo,
                    'Opcion': opcion,
                    'Frecuencia': freq,
                    'Porcentaje': round((freq / total * 100), 2) if total > 0 else 0
                })
    
    return pd.DataFrame(resultados)


# ============================================
# CORRELACIONES
# ============================================

def calcular_correlaciones(df_numerico, metadata, metodo='spearman'):
    """
    Calcula la matriz de correlaciones entre preguntas numéricas.
    
    Args:
        df_numerico: DataFrame con valores numéricos
        metadata: dict con info de las preguntas
        metodo: 'spearman' o 'pearson'
    
    Returns:
        dict con:
        - 'matriz': DataFrame con la matriz de correlación
        - 'pares_significativos': DataFrame con pares de correlación alta
    """
    # Filtrar solo columnas que sean numéricas y de tipo Likert/opción única
    columnas_numericas = []
    nombres_columnas = {}
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        if col not in df_numerico.columns:
            continue
        
        if pregunta['tipo'] in ['escala_likert', 'seleccion_si_no', 'opcion_unica']:
            valores = pd.to_numeric(df_numerico[col], errors='coerce')
            if valores.notna().sum() >= 3:
                columnas_numericas.append(col)
                nombres_columnas[col] = pregunta['texto'][:40]
    
    if len(columnas_numericas) < 2:
        logger.warning("Se necesitan al menos 2 preguntas numéricas para calcular correlaciones")
        return {
            'matriz': pd.DataFrame(),
            'pares_significativos': pd.DataFrame()
        }
    
    # Calcular matriz de correlación
    df_corr = df_numerico[columnas_numericas].apply(pd.to_numeric, errors='coerce')
    matriz = df_corr.corr(method=metodo)
    
    # Renombrar para mostrar textos
    matriz.columns = [nombres_columnas[c] for c in matriz.columns]
    matriz.index = [nombres_columnas[c] for c in matriz.index]
    
    # Extraer pares con correlación significativa (|r| >= 0.3)
    pares = []
    for i, col1 in enumerate(columnas_numericas):
        for col2 in columnas_numericas[i+1:]:
            r = df_corr[col1].corr(df_corr[col2], method=metodo)
            if pd.notna(r) and abs(r) >= 0.3:
                # Calcular p-value con Spearman
                try:
                    valores_comunes = df_corr[[col1, col2]].dropna()
                    if len(valores_comunes) >= 3:
                        _, p_value = stats.spearmanr(valores_comunes[col1], valores_comunes[col2])
                    else:
                        p_value = None
                except Exception:
                    p_value = None
                
                pares.append({
                    'Pregunta_1': nombres_columnas[col1],
                    'Pregunta_2': nombres_columnas[col2],
                    'Correlacion': round(r, 3),
                    'P_Value': round(p_value, 4) if p_value is not None else None,
                    'Interpretacion': interpretar_correlacion(r)
                })
    
    df_pares = pd.DataFrame(pares)
    if not df_pares.empty:
        df_pares = df_pares.sort_values('Correlacion', key=lambda x: x.abs(), ascending=False)
    
    return {
        'matriz': matriz,
        'pares_significativos': df_pares
    }


def interpretar_correlacion(r):
    """Interpreta el valor de correlación"""
    abs_r = abs(r)
    if abs_r >= 0.7:
        fuerza = "Muy fuerte"
    elif abs_r >= 0.5:
        fuerza = "Fuerte"
    elif abs_r >= 0.3:
        fuerza = "Moderada"
    elif abs_r >= 0.1:
        fuerza = "Débil"
    else:
        fuerza = "Muy débil"
    
    direccion = "positiva" if r > 0 else "negativa"
    return f"{fuerza} {direccion}"


# ============================================
# ANÁLISIS POR GRUPOS
# ============================================

def analizar_grupos(df_numerico, df_categorico, metadata, pregunta_grupo_id=None):
    """
    Compara los resultados entre grupos definidos por una pregunta categórica.
    
    Si no se especifica pregunta_grupo_id, usa la primera pregunta de opción única
    o Sí/No disponible.
    
    Args:
        df_numerico: DataFrame con valores numéricos
        df_categorico: DataFrame con valores categóricos
        metadata: metadata de la encuesta
        pregunta_grupo_id: ID de la pregunta que define los grupos
    
    Returns:
        dict con:
        - 'grupo_pregunta': texto de la pregunta usada
        - 'resumen': DataFrame con estadísticas por grupo
        - 'df_comparacion': DataFrame con los datos usados
    """
    # Encontrar pregunta de agrupación
    if pregunta_grupo_id is None:
        for p in metadata['preguntas']:
            if p['tipo'] in ['opcion_unica', 'seleccion_si_no'] and len(p['opciones']) <= 5:
                pregunta_grupo_id = p['id']
                break
    
    if pregunta_grupo_id is None:
        return {
            'grupo_pregunta': None,
            'resumen': pd.DataFrame(),
            'df_comparacion': pd.DataFrame()
        }
    
    pregunta_grupo = next((p for p in metadata['preguntas'] if p['id'] == pregunta_grupo_id), None)
    if not pregunta_grupo:
        return {
            'grupo_pregunta': None,
            'resumen': pd.DataFrame(),
            'df_comparacion': pd.DataFrame()
        }
    
    col_grupo = f"P{pregunta_grupo_id}"
    
    # Preguntas numéricas a comparar (excluyendo la de grupo)
    preguntas_comparar = [
        p for p in metadata['preguntas']
        if p['tipo'] in ['escala_likert', 'seleccion_si_no']
        and p['id'] != pregunta_grupo_id
    ]
    
    if not preguntas_comparar:
        return {
            'grupo_pregunta': pregunta_grupo['texto'],
            'resumen': pd.DataFrame(),
            'df_comparacion': pd.DataFrame()
        }
    
    # Combinar datos
    df_comb = df_categorico[['Identificador', col_grupo]].copy()
    df_comb['Grupo'] = df_comb[col_grupo].fillna('Sin respuesta')
    
    for p in preguntas_comparar:
        col = f"P{p['id']}"
        if col in df_numerico.columns:
            df_comb[col] = pd.to_numeric(df_numerico[col], errors='coerce')
    
    # Calcular estadísticas por grupo
    resumen = []
    for p in preguntas_comparar:
        col = f"P{p['id']}"
        if col not in df_comb.columns:
            continue
        
        for grupo, subdf in df_comb.groupby('Grupo'):
            valores = subdf[col].dropna()
            if len(valores) == 0:
                continue
            
            resumen.append({
                'Pregunta': p['texto'],
                'Grupo': grupo,
                'N': len(valores),
                'Media': round(valores.mean(), 3),
                'Mediana': round(valores.median(), 3),
                'Desv_Est': round(valores.std(), 3) if len(valores) > 1 else 0
            })
    
    return {
        'grupo_pregunta': pregunta_grupo['texto'],
        'resumen': pd.DataFrame(resumen),
        'df_comparacion': df_comb
    }


# ============================================
# ÍNDICE DE SATISFACCIÓN
# ============================================

def calcular_indice_satisfaccion(df_numerico, metadata):
    """
    Calcula un índice de satisfacción global basado en preguntas Likert.
    
    El índice se normaliza a escala 0-100, donde:
    - 0 = Muy insatisfecho
    - 100 = Muy satisfecho
    
    Returns:
        dict con:
        - 'indice_global': float (0-100)
        - 'por_encuestado': DataFrame con índice por encuestado
        - 'por_pregunta': DataFrame con índice por pregunta
    """
    # Obtener preguntas Likert
    preguntas_likert = [
        p for p in metadata['preguntas']
        if p['tipo'] == 'escala_likert'
    ]
    
    if not preguntas_likert:
        return {
            'indice_global': None,
            'por_encuestado': pd.DataFrame(),
            'por_pregunta': pd.DataFrame()
        }
    
    # Construir DataFrame con solo estas preguntas
    df_likert = df_numerico[['Identificador']].copy()
    rangos = {}
    
    for p in preguntas_likert:
        col = f"P{p['id']}"
        if col not in df_numerico.columns:
            continue
        
        valores = pd.to_numeric(df_numerico[col], errors='coerce')
        df_likert[col] = valores
        
        # Calcular rango (min y max) para normalizar
        min_val = valores.min()
        max_val = valores.max()
        rangos[col] = {'min': min_val, 'max': max_val}
    
    columnas_likert = [c for c in df_likert.columns if c != 'Identificador']
    
    if not columnas_likert:
        return {
            'indice_global': None,
            'por_encuestado': pd.DataFrame(),
            'por_pregunta': pd.DataFrame()
        }
    
    # Normalizar cada pregunta a 0-100
    df_normalizado = df_likert[['Identificador']].copy()
    for col in columnas_likert:
        min_val = rangos[col]['min']
        max_val = rangos[col]['max']
        if max_val > min_val:
            df_normalizado[col] = (df_likert[col] - min_val) / (max_val - min_val) * 100
        else:
            df_normalizado[col] = 50  # Valor neutral si no hay variación
    
    # Índice por encuestado: promedio de sus respuestas normalizadas
    df_normalizado['Indice'] = df_normalizado[columnas_likert].mean(axis=1)
    
    # Índice global
    indice_global = df_normalizado['Indice'].mean()
    
    # Índice por pregunta
    por_pregunta = []
    for col in columnas_likert:
        pregunta = next((p for p in preguntas_likert if f"P{p['id']}" == col), None)
        if pregunta:
            por_pregunta.append({
                'Pregunta': pregunta['texto'],
                'Indice_Promedio': round(df_normalizado[col].mean(), 2),
                'Min': round(df_normalizado[col].min(), 2),
                'Max': round(df_normalizado[col].max(), 2)
            })
    
    return {
        'indice_global': round(indice_global, 2),
        'por_encuestado': df_normalizado[['Identificador', 'Indice']],
        'por_pregunta': pd.DataFrame(por_pregunta)
    }


# ============================================
# TABLA DE CONTINGENCIA
# ============================================

def calcular_tabla_contingencia(df_categorico, metadata, pregunta1_id, pregunta2_id):
    """
    Calcula la tabla de contingencia entre dos preguntas categóricas.
    
    Returns:
        dict con:
        - 'tabla': tabla cruzada
        - 'chi2': valor de Chi-cuadrado
        - 'p_value': p-value
        - 'significativo': bool
    """
    col1 = f"P{pregunta1_id}"
    col2 = f"P{pregunta2_id}"
    
    if col1 not in df_categorico.columns or col2 not in df_categorico.columns:
        return {
            'tabla': pd.DataFrame(),
            'chi2': None,
            'p_value': None,
            'significativo': False
        }
    
    # Crear tabla cruzada
    tabla = pd.crosstab(df_categorico[col1], df_categorico[col2])
    
    # Prueba Chi-cuadrado
    try:
        chi2, p_value, dof, expected = stats.chi2_contingency(tabla)
        significativo = p_value < 0.05
    except Exception as e:
        logger.warning(f"Error en Chi-cuadrado: {e}")
        chi2, p_value, significativo = None, None, False
    
    return {
        'tabla': tabla,
        'chi2': round(chi2, 3) if chi2 is not None else None,
        'p_value': round(p_value, 4) if p_value is not None else None,
        'significativo': significativo
    }