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
# DETECCIÓN DE ESCALAS ORDENADAS
# ============================================

# Patrones comunes de escalas ordenadas en español
PATRONES_ESCALAS_ORDENADAS = [
    # Escala Likert clásica
    ['muy malo', 'malo', 'regular', 'bueno', 'muy bueno'],
    ['muy mal', 'mal', 'regular', 'bien', 'muy bien'],
    ['pésimo', 'malo', 'regular', 'bueno', 'excelente'],
    # Escala de frecuencia
    ['nunca', 'rara vez', 'a veces', 'frecuentemente', 'siempre'],
    ['nunca', 'casi nunca', 'a veces', 'casi siempre', 'siempre'],
    # Escala de satisfacción
    ['muy insatisfecho', 'insatisfecho', 'neutral', 'satisfecho', 'muy satisfecho'],
    ['muy insatisfecho', 'insatisfecho', 'ni satisfecho ni insatisfecho', 'satisfecho', 'muy satisfecho'],
    # Escala de nivel
    ['muy bajo', 'bajo', 'medio', 'alto', 'muy alto'],
    ['muy bajo', 'bajo', 'regular', 'alto', 'muy alto'],
    ['ninguno', 'poco', 'moderado', 'bastante', 'mucho'],
    # Escala de acuerdo
    ['totalmente en desacuerdo', 'en desacuerdo', 'neutral', 'de acuerdo', 'totalmente de acuerdo'],
    ['muy en desacuerdo', 'en desacuerdo', 'ni de acuerdo ni en desacuerdo', 'de acuerdo', 'muy de acuerdo'],
    # Escala de importancia
    ['nada importante', 'poco importante', 'neutral', 'importante', 'muy importante'],
]


def _normalizar_texto_opcion(texto):
    """Normaliza un texto para comparar (sin tildes, minúsculas)."""
    import unicodedata
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


def es_escala_ordenada(pregunta):
    """
    Detecta si una pregunta de opción única representa una escala ordenada.
    
    Args:
        pregunta: dict con 'tipo', 'opciones'
    
    Returns:
        bool: True si parece ser una escala ordenada
    """
    if pregunta['tipo'] == 'escala_likert':
        return True
    
    if pregunta['tipo'] != 'opcion_unica':
        return False
    
    opciones = pregunta.get('opciones', [])
    
    if len(opciones) < 3 or len(opciones) > 7:
        return False
    
    # Normalizar opciones
    opciones_norm = [_normalizar_texto_opcion(o) for o in opciones]
    
    # Comparar con patrones conocidos
    for patron in PATRONES_ESCALAS_ORDENADAS:
        if len(patron) != len(opciones_norm):
            continue
        
        # Verificar coincidencia (>=80% de las opciones coinciden)
        coincidencias = sum(
            1 for i, op in enumerate(opciones_norm)
            if i < len(patron) and op == patron[i]
        )
        
        if coincidencias >= len(patron) * 0.8:
            return True
    
    return False


# ============================================
# ESTADÍSTICAS DESCRIPTIVAS
# ============================================

def calcular_estadisticas_descriptivas(df_numerico, metadata):
    """
    Calcula estadísticas descriptivas para cada pregunta.
    """
    resultados = []
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        tipo = pregunta['tipo']
        
        if col not in df_numerico.columns:
            continue
        
        valores = pd.to_numeric(df_numerico[col], errors='coerce').dropna()
        
        fila = {
            'Pregunta_ID': pregunta['id'],
            'Pregunta': pregunta['texto'],
            'Tipo': tipo,
            'Total_Respuestas': len(valores)
        }
        
        # ✅ AMPLIAR: Incluir opcion_unica si parece escala ordenada
        es_calculable = (
            tipo in ['escala_likert', 'seleccion_si_no'] or
            es_escala_ordenada(pregunta)
        )
        
        if len(valores) > 0 and es_calculable:
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
    ✅ CORREGIDO: Convierte valores a string para evitar problemas con int/str.
    """
    resultados = []
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        tipo = pregunta['tipo']
        
        if col not in df_categorico.columns:
            continue
        
        # ✅ CONVERTIR COLUMNA A STRING (evita problemas con 2007 vs "2007")
        columna_str = df_categorico[col].apply(
            lambda x: str(x).strip() if pd.notna(x) else None
        )
        
        if tipo == 'opcion_multiple':
            conteo = {op: 0 for op in pregunta['opciones']}
            for valor in columna_str.dropna():
                if not valor:
                    continue
                opciones_marcadas = [o.strip() for o in str(valor).split(';') if o.strip()]
                for op in opciones_marcadas:
                    # ✅ Buscar coincidencia exacta o normalizada
                    for opcion_real in conteo.keys():
                        if op == opcion_real or _normalizar_texto_opcion(op) == _normalizar_texto_opcion(opcion_real):
                            conteo[opcion_real] += 1
                            break
            
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
            # ✅ Opción única / Likert / Sí-No
            conteo = columna_str.value_counts(dropna=True).to_dict()
            total = sum(conteo.values())
            
            for opcion in pregunta['opciones']:
                opcion_str = str(opcion).strip()
                freq = conteo.get(opcion_str, 0)
                
                # ✅ Fallback: buscar con normalización si no encontró
                if freq == 0:
                    opcion_norm = _normalizar_texto_opcion(opcion_str)
                    for key, val in conteo.items():
                        if _normalizar_texto_opcion(key) == opcion_norm:
                            freq = val
                            break
                
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
    """Calcula la matriz de correlaciones entre preguntas numéricas."""
    columnas_numericas = []
    nombres_columnas = {}
    
    for pregunta in metadata['preguntas']:
        col = f"P{pregunta['id']}"
        if col not in df_numerico.columns:
            continue
        
        # ✅ AMPLIAR: incluir opcion_unica con escala ordenada
        tipo_ok = (
            pregunta['tipo'] in ['escala_likert', 'seleccion_si_no'] or
            es_escala_ordenada(pregunta)
        )
        
        if tipo_ok:
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
    
    df_corr = df_numerico[columnas_numericas].apply(pd.to_numeric, errors='coerce')
    matriz = df_corr.corr(method=metodo)
    
    matriz.columns = [nombres_columnas[c] for c in matriz.columns]
    matriz.index = [nombres_columnas[c] for c in matriz.index]
    
    pares = []
    for i, col1 in enumerate(columnas_numericas):
        for col2 in columnas_numericas[i+1:]:
            try:
                r = df_corr[col1].corr(df_corr[col2], method=metodo)
                if pd.notna(r) and abs(r) >= 0.3:
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
            except Exception as e:
                logger.warning(f"Error correlación {col1} vs {col2}: {e}")
    
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
    ✅ CORREGIDO: Ahora incluye opcion_unica como posible grupo.
    """
    # Encontrar pregunta de agrupación: la primera con pocas opciones
    if pregunta_grupo_id is None:
        for p in metadata['preguntas']:
            if p['tipo'] in ['opcion_unica', 'seleccion_si_no'] and 2 <= len(p['opciones']) <= 6:
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
    
    # ✅ CORREGIDO: Ampliar tipos de pregunta a comparar
    preguntas_comparar = []
    for p in metadata['preguntas']:
        if p['id'] == pregunta_grupo_id:
            continue
        
        tipo_ok = (
            p['tipo'] in ['escala_likert', 'seleccion_si_no'] or
            es_escala_ordenada(p)
        )
        
        if tipo_ok:
            preguntas_comparar.append(p)
    
    if not preguntas_comparar:
        logger.warning("No hay preguntas comparables para análisis de grupos")
        return {
            'grupo_pregunta': pregunta_grupo['texto'],
            'resumen': pd.DataFrame(),
            'df_comparacion': pd.DataFrame()
        }
    
    # Combinar datos
    df_comb = df_categorico[['Identificador', col_grupo]].copy()
    df_comb['Grupo'] = df_comb[col_grupo].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else 'Sin respuesta'
    )
    
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
    Calcula un índice de satisfacción global basado en preguntas Likert
    y también en opcion_unica con escala ordenada.
    ✅ CORREGIDO: Detección automática de escalas ordenadas.
    """
    # ✅ Buscar preguntas con escala ordenada (Likert + opcion_unica detectada)
    preguntas_escala = []
    for p in metadata['preguntas']:
        if p['tipo'] == 'escala_likert' or es_escala_ordenada(p):
            preguntas_escala.append(p)
    
    if not preguntas_escala:
        logger.warning("No hay preguntas con escala ordenada para índice de satisfacción")
        return {
            'indice_global': None,
            'por_encuestado': pd.DataFrame(),
            'por_pregunta': pd.DataFrame()
        }
    
    # Construir DataFrame con solo estas preguntas
    df_escala = df_numerico[['Identificador']].copy()
    rangos = {}
    
    for p in preguntas_escala:
        col = f"P{p['id']}"
        if col not in df_numerico.columns:
            continue
        
        valores = pd.to_numeric(df_numerico[col], errors='coerce')
        df_escala[col] = valores
        
        min_val = valores.min()
        max_val = valores.max()
        rangos[col] = {'min': min_val, 'max': max_val}
    
    columnas_escala = [c for c in df_escala.columns if c != 'Identificador']
    
    if not columnas_escala:
        return {
            'indice_global': None,
            'por_encuestado': pd.DataFrame(),
            'por_pregunta': pd.DataFrame()
        }
    
    # Normalizar cada pregunta a 0-100
    df_normalizado = df_escala[['Identificador']].copy()
    for col in columnas_escala:
        min_val = rangos[col]['min']
        max_val = rangos[col]['max']
        if max_val > min_val:
            df_normalizado[col] = (df_escala[col] - min_val) / (max_val - min_val) * 100
        else:
            df_normalizado[col] = 50
    
    # Índice por encuestado
    df_normalizado['Indice'] = df_normalizado[columnas_escala].mean(axis=1)
    
    # Índice global
    indice_global = df_normalizado['Indice'].mean()
    
    # Índice por pregunta
    por_pregunta = []
    for col in columnas_escala:
        pregunta = next((p for p in preguntas_escala if f"P{p['id']}" == col), None)
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
    """Calcula la tabla de contingencia entre dos preguntas categóricas."""
    col1 = f"P{pregunta1_id}"
    col2 = f"P{pregunta2_id}"
    
    if col1 not in df_categorico.columns or col2 not in df_categorico.columns:
        return {
            'tabla': pd.DataFrame(),
            'chi2': None,
            'p_value': None,
            'significativo': False
        }
    
    tabla = pd.crosstab(df_categorico[col1], df_categorico[col2])
    
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