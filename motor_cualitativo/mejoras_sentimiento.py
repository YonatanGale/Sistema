# motor_cualitativo/mejoras_sentimiento.py
"""
Reglas heurísticas para mejorar la clasificación de sentimiento de BETO
en respuestas cortas, contextuales o con jerga local.

BETO afinado (finiteautomata/beto-sentiment-analysis) clasifica en 3 clases:
POS / NEG / NEU. Estas reglas permiten:
  - Promover a 'Muy Positivo'/'Muy Negativo' cuando el texto lo justifica.
  - Corregir casos donde BETO falla por falta de contexto (respuestas de 1-3 palabras).
  - Interpretar frases coloquiales ("nada, todo bien", "sigan así", etc.).
"""

# ============================================
# FRASES QUE INDICAN SENTIMIENTO POSITIVO
# ============================================
FRASES_POSITIVAS = [
    # Nada + positivo
    "nada, seguir así", "nada, todo bien", "nada, todo perfecto",
    "nada, todo excelente", "nada que mejorar", "nada que cambiar",
    "nada, está perfecto", "nada, muy bien", "nada, muy conforme",
    "nada, excelente", "nada, perfecto", "nada, siga así",
    "nada, continúen así", "nada, está bien",
    # Todo + positivo
    "todo perfecto", "todo bien", "todo excelente", "todo muy bien",
    "todo está bien", "todo está perfecto",
    # Cumplidos
    "excelente", "perfecto", "muy bueno", "muy bien",
    "excelente servicio", "muy satisfecho", "muy contento",
    "muy conforme", "muy agradecido", "recomendado",
    "los felicito", "felicitaciones", "sigan así", "sigan adelante",
    # Satisfacción
    "satisfecho", "contento", "conforme", "encantado",
    "me encanta", "me gusta mucho",
]

# ============================================
# FRASES QUE INDICAN SENTIMIENTO NEGATIVO
# ============================================
FRASES_NEGATIVAS = [
    "nada funciona", "todo mal", "todo está mal", "todo es un desastre",
    "pésimo", "horrible", "terrible", "muy malo", "muy mal",
    "no me gusta", "no sirve", "una porquería", "un desastre",
    "deficiente", "no me ayudó", "no sirvió", "una pérdida de tiempo",
]


def ajustar_sentimiento(texto, sentimiento_original, score_original):
    """
    Ajusta el sentimiento aplicando reglas heurísticas.

    Args:
        texto: Texto analizado.
        sentimiento_original: Sentimiento devuelto por BETO
                              ('Positivo' | 'Negativo' | 'Neutral').
        score_original: Score de confianza del modelo.

    Returns:
        Tupla (sentimiento_ajustado, score_ajustado).
    """
    if not texto:
        return sentimiento_original, score_original

    texto_lower = texto.lower().strip()

    # 1. Frases positivas explícitas
    for frase in FRASES_POSITIVAS:
        if frase in texto_lower:
            return 'Muy Positivo', 0.95

    # 2. Frases negativas explícitas
    for frase in FRASES_NEGATIVAS:
        if frase in texto_lower:
            return 'Muy Negativo', 0.95

    # 3. "Nada, ..." con contexto positivo
    if texto_lower.startswith('nada'):
        palabras_positivas = ['bien', 'perfecto', 'excelente', 'así',
                              'igual', 'cambiar', 'mejorar', 'conforme']
        if any(p in texto_lower for p in palabras_positivas):
            return 'Muy Positivo', 0.90

    # 4. Respuestas muy cortas (1-3 palabras)
    palabras = texto_lower.split()
    if len(palabras) <= 3:
        if any(p in texto_lower for p in ['excelente', 'perfecto', 'bueno', 'bien']):
            return 'Muy Positivo', 0.85
        if any(p in texto_lower for p in ['malo', 'mal', 'pésimo', 'horrible']):
            return 'Muy Negativo', 0.85

    return sentimiento_original, score_original


def aplicar_ajustes(df_resultados):
    """
    Aplica ajustes de sentimiento a un DataFrame completo.

    Args:
        df_resultados: DataFrame con columnas 'texto' y 'sentimiento'.

    Returns:
        DataFrame con columnas adicionales 'sentimiento_ajustado' y 'score_ajustado'.
    """
    df = df_resultados.copy()
    ajustes = df.apply(
        lambda row: ajustar_sentimiento(
            row['texto'],
            row.get('sentimiento', 'Neutral'),
            row.get('score_confianza', row.get('score', 0.5)),
        ),
        axis=1,
    )
    df['sentimiento_ajustado'] = [a[0] for a in ajustes]
    df['score_ajustado'] = [a[1] for a in ajustes]
    return df