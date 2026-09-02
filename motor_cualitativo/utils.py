# motor_cualitativo/utils.py
import pandas as pd
import json
import os
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)

def cargar_modelo(nombre_modelo):
    """
    Función helper para cargar modelos.
    
    Args:
        nombre_modelo: Nombre del modelo
        
    Returns:
        Modelo cargado
    """
    from .modelos import ModeloAnalisis
    gestor = ModeloAnalisis()
    return gestor.cargar_modelo(nombre_modelo)


def guardar_resultados(resultados, nombre_base, formato='json', directorio='data/resultados'):
    """
    Guarda resultados en diferentes formatos.
    
    Args:
        resultados: Dict con resultados
        nombre_base: Nombre base del archivo
        formato: 'json', 'csv', o 'excel'
        directorio: Directorio donde guardar
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_archivo = f"{nombre_base}_{timestamp}"
    
    os.makedirs(directorio, exist_ok=True)
    
    if formato == 'json':
        ruta = os.path.join(directorio, f"{nombre_archivo}.json")
        # Convertir DataFrames a dict
        resultados_serializables = {}
        for key, value in resultados.items():
            if isinstance(value, pd.DataFrame):
                resultados_serializables[key] = value.to_dict('records')
            elif isinstance(value, dict):
                resultados_serializables[key] = value
            else:
                resultados_serializables[key] = str(value)
        
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(resultados_serializables, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados guardados en {ruta}")
        return ruta
    
    elif formato == 'csv':
        rutas = []
        for key, value in resultados.items():
            if isinstance(value, pd.DataFrame):
                ruta = os.path.join(directorio, f"{nombre_archivo}_{key}.csv")
                value.to_csv(ruta, index=False, encoding='utf-8-sig')
                rutas.append(ruta)
                logger.info(f"CSV guardado en {ruta}")
        return rutas
    
    elif formato == 'excel':
        ruta = os.path.join(directorio, f"{nombre_archivo}.xlsx")
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            for key, value in resultados.items():
                if isinstance(value, pd.DataFrame):
                    value.to_excel(writer, sheet_name=key[:31], index=False)
                elif isinstance(value, dict) and value:
                    pd.DataFrame([value]).to_excel(writer, sheet_name=key[:31], index=False)
        logger.info(f"Excel guardado en {ruta}")
        return ruta
    
    else:
        raise ValueError(f"Formato {formato} no soportado")


def crear_dataset_prueba(n=10, semilla=42):
    """
    Crea un dataset de prueba para el motor de análisis.
    
    Args:
        n: Número de ejemplos
        semilla: Semilla para reproducibilidad
        
    Returns:
        DataFrame con textos de prueba
    """
    random.seed(semilla)
    
    textos = [
        "El servicio pastoral de la parroquia es excelente, muy comprometido con la comunidad.",
        "Me encanta la atención del párroco, siempre está disponible para los feligreses.",
        "Las actividades de la comunidad son muy buenas, pero podrían mejorar la comunicación.",
        "No me gusta cómo se manejan las finanzas de la parroquia, falta transparencia.",
        "Los grupos de oración son maravillosos, me siento muy acogido.",
        "La infraestructura de la iglesia necesita mejoras urgentes.",
        "El trabajo con los jóvenes es increíble, muy dinámico y participativo.",
        "Me siento parte de esta comunidad, es mi familia espiritual.",
        "Los horarios de misa deberían ser más flexibles para los trabajadores.",
        "La catequesis es muy completa y bien organizada.",
        "Excelente ambiente de hermandad y solidaridad.",
        "La música durante las misas es muy emotiva y espiritual.",
        "Necesitamos más actividades para niños y familias.",
        "El párroco da excelentes homilías, muy profundas.",
        "La comunidad es muy acogedora con los nuevos miembros.",
        "Los retiros espirituales son transformadores.",
        "Falta más participación de los jóvenes en la comunidad.",
        "La atención a los enfermos y ancianos es ejemplar.",
        "Las redes sociales de la parroquia están muy activas.",
        "Me encanta la labor social que realiza la comunidad."
    ]
    
    if n < len(textos):
        textos_seleccionados = random.sample(textos, n)
    else:
        textos_seleccionados = textos * (n // len(textos) + 1)
        textos_seleccionados = textos_seleccionados[:n]
    
    df = pd.DataFrame({
        'texto': textos_seleccionados,
        'id': range(1, n + 1)
    })
    
    return df


def cargar_desde_excel(ruta_archivo, columna_texto=None):
    """
    Carga textos desde un archivo Excel.
    
    Args:
        ruta_archivo: Ruta al archivo Excel
        columna_texto: Nombre de la columna que contiene los textos
        
    Returns:
        DataFrame con los textos
    """
    df = pd.read_excel(ruta_archivo)
    
    if columna_texto:
        if columna_texto not in df.columns:
            raise ValueError(f"Columna '{columna_texto}' no encontrada en el archivo")
        df = df[[columna_texto]]
        df.columns = ['texto']
    
    return df


def cargar_desde_csv(ruta_archivo, columna_texto=None, encoding='utf-8-sig'):
    """
    Carga textos desde un archivo CSV.
    
    Args:
        ruta_archivo: Ruta al archivo CSV
        columna_texto: Nombre de la columna que contiene los textos
        encoding: Codificación del archivo
        
    Returns:
        DataFrame con los textos
    """
    df = pd.read_csv(ruta_archivo, encoding=encoding)
    
    if columna_texto:
        if columna_texto not in df.columns:
            raise ValueError(f"Columna '{columna_texto}' no encontrada en el archivo")
        df = df[[columna_texto]]
        df.columns = ['texto']
    
    return df