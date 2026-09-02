# motor_cualitativo/modelos.py
import os
import json
import pickle
import torch
from transformers import AutoTokenizer, AutoModel
import logging

logger = logging.getLogger(__name__)

class ModeloAnalisis:
    """
    Gestor de modelos para análisis cualitativo.
    """
    
    MODELS = {
        'bert': 'dccuchile/bert-base-spanish-wwm-uncased',
        'beto': 'dccuchile/bert-base-spanish-wwm-uncased',
        'sentiment': 'nlptown/bert-base-multilingual-uncased-sentiment',
        'sentiment_es': 'finiteautomata/bert-base-spanish-wwm-cased-finetuned-spa-sentiment'
    }
    
    def __init__(self, directorio_modelos='data/modelos'):
        self.directorio_modelos = directorio_modelos
        os.makedirs(directorio_modelos, exist_ok=True)
        
        self.modelos_cargados = {}
        
    def descargar_modelo(self, nombre_modelo):
        """
        Descarga un modelo preentrenado.
        
        Args:
            nombre_modelo: Clave del modelo en MODELS
            
        Returns:
            Ruta del modelo descargado
        """
        if nombre_modelo not in self.MODELS:
            raise ValueError(f"Modelo {nombre_modelo} no disponible. Opciones: {list(self.MODELS.keys())}")
        
        modelo_path = self.MODELS[nombre_modelo]
        ruta_local = os.path.join(self.directorio_modelos, nombre_modelo)
        
        if os.path.exists(ruta_local):
            logger.info(f"Modelo {nombre_modelo} ya existe en {ruta_local}")
            return ruta_local
        
        try:
            logger.info(f"Descargando modelo {nombre_modelo}...")
            
            tokenizer = AutoTokenizer.from_pretrained(modelo_path)
            tokenizer.save_pretrained(ruta_local)
            
            model = AutoModel.from_pretrained(modelo_path)
            model.save_pretrained(ruta_local)
            
            logger.info(f"✅ Modelo {nombre_modelo} descargado en {ruta_local}")
            return ruta_local
            
        except Exception as e:
            logger.error(f"❌ Error descargando modelo {nombre_modelo}: {e}")
            return None
    
    def cargar_modelo(self, nombre_modelo, device=None):
        """
        Carga un modelo desde el disco.
        
        Args:
            nombre_modelo: Clave del modelo
            device: 'cpu' o 'cuda'
            
        Returns:
            Modelo cargado
        """
        if nombre_modelo in self.modelos_cargados:
            return self.modelos_cargados[nombre_modelo]
        
        ruta_modelo = os.path.join(self.directorio_modelos, nombre_modelo)
        
        if not os.path.exists(ruta_modelo):
            ruta_modelo = self.descargar_modelo(nombre_modelo)
        
        if not ruta_modelo:
            return None
        
        try:
            logger.info(f"Cargando modelo {nombre_modelo} desde {ruta_modelo}")
            
            if device is None:
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            model = AutoModel.from_pretrained(ruta_modelo).to(device)
            tokenizer = AutoTokenizer.from_pretrained(ruta_modelo)
            
            self.modelos_cargados[nombre_modelo] = {
                'model': model,
                'tokenizer': tokenizer,
                'device': device
            }
            
            logger.info(f"✅ Modelo {nombre_modelo} cargado en {device}")
            return self.modelos_cargados[nombre_modelo]
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelo {nombre_modelo}: {e}")
            return None
    
    def guardar_analisis(self, resultados, nombre_archivo):
        """
        Guarda resultados de análisis en disco.
        
        Args:
            resultados: Dict con resultados
            nombre_archivo: Nombre del archivo
        """
        ruta = os.path.join(self.directorio_modelos, f"{nombre_archivo}.pkl")
        
        with open(ruta, 'wb') as f:
            pickle.dump(resultados, f)
        
        logger.info(f"Resultados guardados en {ruta}")
        return ruta
    
    def cargar_analisis(self, nombre_archivo):
        """
        Carga resultados de análisis desde disco.
        
        Args:
            nombre_archivo: Nombre del archivo
            
        Returns:
            Resultados cargados
        """
        ruta = os.path.join(self.directorio_modelos, f"{nombre_archivo}.pkl")
        
        if not os.path.exists(ruta):
            logger.error(f"Archivo {ruta} no encontrado")
            return None
        
        with open(ruta, 'rb') as f:
            resultados = pickle.load(f)
        
        logger.info(f"Resultados cargados desde {ruta}")
        return resultados