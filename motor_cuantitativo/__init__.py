# motor_cuantitativo/__init__.py
"""
Motor de Análisis Cuantitativo
==============================
Módulo independiente para análisis estadístico de respuestas de encuestas.

Funcionalidades:
- Estadísticas descriptivas (media, mediana, moda, desv. est., percentiles)
- Correlaciones entre preguntas (Spearman)
- Análisis por grupos
- Índice de satisfacción
- Visualizaciones (barras, pastel, histograma, heatmap, boxplot)
- Exportación a Excel, PNG, JSON

Uso básico:
    from motor_cuantitativo import AnalizadorCuantitativo
    
    analizador = AnalizadorCuantitativo()
    resultados = analizador.analizar_completo('exports/cuantitativo_1.csv')
"""

from .analizador_cuantitativo import AnalizadorCuantitativo
from .lector_datos import leer_csv_cuantitativo, convertir_a_numerico
from .estadisticas import (
    calcular_estadisticas_descriptivas,
    calcular_frecuencias,
    calcular_correlaciones,
    analizar_grupos,
    calcular_indice_satisfaccion,
    calcular_tabla_contingencia
)

__version__ = "1.0.0"
__all__ = [
    'AnalizadorCuantitativo',
    'leer_csv_cuantitativo',
    'convertir_a_numerico',
    'calcular_estadisticas_descriptivas',
    'calcular_frecuencias',
    'calcular_correlaciones',
    'analizar_grupos',
    'calcular_indice_satisfaccion',
    'calcular_tabla_contingencia'
]