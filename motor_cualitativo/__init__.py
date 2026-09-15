# motor_cualitativo/__init__.py
"""
Motor de Análisis Cualitativo
=============================
Módulo independiente para análisis de texto utilizando modelos Transformers en español.

Funcionalidades:
- Análisis de sentimiento
- Extracción de palabras clave con TF-IDF
- Clasificación automática de temas (LDA)
- Preprocesamiento de texto
- Lectura de CSV del sistema de encuestas

Uso básico:
    from motor_cualitativo import AnalizadorCualitativo
    
    analizador = AnalizadorCualitativo()
    resultados = analizador.analizar_completo(textos)

Uso con CSV del sistema de encuestas:
    from motor_cualitativo import cargar_desde_csv_encuestas
    
    df = cargar_desde_csv_encuestas('exports/cualitativo_1.csv')
"""

from .analizador import AnalizadorCualitativo
from .modelos import ModeloAnalisis
from .procesador import ProcesadorTexto
from .lector_csv import leer_csv_encuestas, leer_csv_agrupado_por_pregunta
from .utils import (
    cargar_modelo,
    guardar_resultados,
    crear_dataset_prueba,
    cargar_desde_excel,
    cargar_desde_csv,
    cargar_desde_csv_encuestas,
    procesar_csv_completo
)

__version__ = "1.1.0"
__all__ = [
    'AnalizadorCualitativo',
    'ModeloAnalisis',
    'ProcesadorTexto',
    'leer_csv_encuestas',
    'leer_csv_agrupado_por_pregunta',
    'cargar_modelo',
    'guardar_resultados',
    'crear_dataset_prueba',
    'cargar_desde_excel',
    'cargar_desde_csv',
    'cargar_desde_csv_encuestas',
    'procesar_csv_completo'
]