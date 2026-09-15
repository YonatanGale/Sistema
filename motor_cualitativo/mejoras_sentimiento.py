# motor_cualitativo/mejoras_sentimiento.py
"""
Reglas heurísticas para mejorar la clasificación de sentimiento
en respuestas cortas o contextuales de encuestas.
"""

# ============================================
# FRASES QUE INDICAN SENTIMIENTO POSITIVO
# ============================================
FRASES_POSITIVAS = [
    # Nada + positivo
    "nada, seguir así",
    "nada, todo bien",
    "nada, todo perfecto",
    "nada, todo excelente",
    "nada que mejorar",
    "nada que cambiar",
    "nada, está perfecto",
    "nada, muy bien",
    "nada, muy conforme",
    "nada, excelente",
    "nada, perfecto",
    "nada, siga así",
    "nada, continúen así",
    "nada, está bien",
    
    # Todo + positivo
    "todo perfecto",
    "todo bien",
    "todo excelente",
    "todo muy bien",
    "todo está bien",
    "todo está perfecto",
    "todo excelente",
    
    # Cumplidos
    "excelente",
    "perfecto",
    "muy bueno",
    "muy bien",
    "excelente servicio",
    "muy satisfecho",
    "muy contento",
    "muy conforme",
    "muy agradecido",
    "recomendado",
    "los felicito",
    "felicitaciones",
    "sigan así",
    "sigan adelante",
    
    # Satisfacción
    "satisfecho",
    "contento",
    "conforme",
    "encantado",
    "me encanta",
    "me gusta mucho",
]

# ============================================
# FRASES QUE INDICAN SENTIMIENTO NEGATIVO
# ============================================
FRASES_NEGATIVAS = [
    "nada funciona",
    "todo mal",
    "todo está mal",
    "todo es un desastre",
    "pésimo",
    "horrible",
    "terrible",
    "muy malo",
    "muy mal",
    "no me gusta",
    "no sirve",
    "una porquería",
    "un desastre",
    "deficiente",
]


def ajustar_sentimiento(texto, sentimiento_original, score_original):
    """
    Ajusta el sentimiento basándose en reglas heurísticas.
    
    Args:
        texto: Texto analizado
        sentimiento_original: Sentimiento que dio el modelo
        score_original: Score de confianza
        
    Returns:
        Tupla (sentimiento_ajustado, score_ajustado)
    """
    if not texto:
        return sentimiento_original, score_original
    
    texto_lower = texto.lower().strip()
    
    # ============================================
    # 1. VERIFICAR FRASES POSITIVAS
    # ============================================
    for frase in FRASES_POSITIVAS:
        if frase in texto_lower:
            return 'Muy Positivo', 0.95
    
    # ============================================
    # 2. VERIFICAR FRASES NEGATIVAS
    # ============================================
    for frase in FRASES_NEGATIVAS:
        if frase in texto_lower:
            return 'Muy Negativo', 0.95
    
    # ============================================
    # 3. REGLA ESPECIAL: "NADA, ..." CON CONTEXTO POSITIVO
    # ============================================
    if texto_lower.startswith('nada'):
        # Si después de "nada" hay algo positivo o neutral
        palabras_positivas = ['bien', 'perfecto', 'excelente', 'así', 'igual', 'cambiar', 'mejorar', 'conforme']
        if any(p in texto_lower for p in palabras_positivas):
            return 'Muy Positivo', 0.90
    
    # ============================================
    # 4. RESPUESTAS MUY CORTAS (1-3 palabras)
    # ============================================
    palabras = texto_lower.split()
    if len(palabras) <= 3:
        # Si es una palabra positiva
        if any(p in texto_lower for p in ['excelente', 'perfecto', 'bueno', 'bien']):
            return 'Muy Positivo', 0.85
        # Si es una palabra negativa
        if any(p in texto_lower for p in ['malo', 'mal', 'pésimo', 'horrible']):
            return 'Muy Negativo', 0.85
    
    return sentimiento_original, score_original


def aplicar_ajustes(df_resultados):
    """
    Aplica los ajustes de sentimiento a un DataFrame.
    
    Args:
        df_resultados: DataFrame con columna 'texto' y 'sentimiento'
        
    Returns:
        DataFrame con sentimientos ajustados
    """
    df_resultados = df_resultados.copy()
    
    # Aplicar ajustes
    ajustes = df_resultados.apply(
        lambda row: ajustar_sentimiento(
            row['texto'],
            row.get('sentimiento', 'Neutral'),
            row.get('score_confianza', 0.5)
        ),
        axis=1
    )
    
    df_resultados['sentimiento_ajustado'] = [a[0] for a in ajustes]
    df_resultados['score_ajustado'] = [a[1] for a in ajustes]
    
    return df_resultados