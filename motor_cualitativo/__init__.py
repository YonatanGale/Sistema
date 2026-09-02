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

Uso básico:
    from motor_cualitativo import AnalizadorCualitativo
    
    analizador = AnalizadorCualitativo()
    resultados = analizador.analizar_completo(textos)
"""

from .analizador import AnalizadorCualitativo
from .modelos import ModeloAnalisis
from .procesador import ProcesadorTexto
from .utils import (
    cargar_modelo,
    guardar_resultados,
    crear_dataset_prueba,
    cargar_desde_excel,
    cargar_desde_csv
)

__version__ = "1.0.0"
__all__ = [
    'AnalizadorCualitativo',
    'ModeloAnalisis',
    'ProcesadorTexto',
    'cargar_modelo',
    'guardar_resultados',
    'crear_dataset_prueba',
    'cargar_desde_excel',
    'cargar_desde_csv'
]