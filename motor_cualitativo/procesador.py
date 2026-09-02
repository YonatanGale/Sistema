# motor_cualitativo/procesador.py
import re
import pandas as pd
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import unicodedata
import logging

logger = logging.getLogger(__name__)

class ProcesadorTexto:
    """
    Procesador de texto para preparar datos para el motor de análisis.
    """
    
    def __init__(self, idioma='spanish'):
        self.idioma = idioma
        self.stemmer = SnowballStemmer(idioma)
        self.stopwords = set(stopwords.words(idioma))
        
    def limpiar_texto(self, texto):
        """
        Limpia y normaliza texto.
        
        Args:
            texto: String a procesar
            
        Returns:
            String limpio
        """
        if not texto or not isinstance(texto, str):
            return ""
        
        texto = texto.lower()
        
        # Eliminar tildes
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join([c for c in texto if not unicodedata.combining(c)])
        
        # Eliminar URLs
        texto = re.sub(r'http\S+|www\S+', '', texto)
        
        # Eliminar menciones y hashtags
        texto = re.sub(r'@\w+', '', texto)
        texto = re.sub(r'#\w+', '', texto)
        
        # Eliminar números
        texto = re.sub(r'\d+', '', texto)
        
        # Eliminar puntuación
        texto = re.sub(r'[^\w\s]', ' ', texto)
        
        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def tokenizar(self, texto):
        """
        Tokeniza texto y elimina stopwords.
        
        Args:
            texto: String a tokenizar
            
        Returns:
            Lista de tokens
        """
        texto_limpio = self.limpiar_texto(texto)
        if not texto_limpio:
            return []
        
        try:
            # Intentar con word_tokenize de NLTK
            tokens = word_tokenize(texto_limpio, language='spanish')
        except LookupError:
            # Fallback si falta el tokenizador
            from nltk.tokenize import wordpunct_tokenize
            logger.warning("Usando wordpunct_tokenize como fallback")
            tokens = wordpunct_tokenize(texto_limpio)
        except Exception as e:
            # Fallback alternativo con split simple
            logger.warning(f"Error en tokenización: {e}. Usando split simple.")
            tokens = texto_limpio.split()
        
        # Filtrar stopwords y tokens cortos
        tokens = [t for t in tokens if t not in self.stopwords and len(t) > 2]
        
        return tokens
    
    def stemizar(self, tokens):
        """
        Aplica stemming a una lista de tokens.
        
        Args:
            tokens: Lista de tokens
            
        Returns:
            Lista de stems
        """
        return [self.stemmer.stem(t) for t in tokens]
    
    def procesar_lote(self, textos):
        """
        Procesa un lote de textos.
        
        Args:
            textos: Lista de strings o DataFrame
            
        Returns:
            DataFrame con textos procesados
        """
        if isinstance(textos, pd.DataFrame):
            if 'texto' in textos.columns:
                textos = textos['texto'].tolist()
            else:
                textos = textos.iloc[:, 0].tolist()
        elif isinstance(textos, str):
            textos = [textos]
        
        resultados = []
        for texto in textos:
            # Manejar valores nulos
            if texto is None or pd.isna(texto):
                texto = ""
            texto = str(texto)
            
            texto_limpio = self.limpiar_texto(texto)
            tokens = self.tokenizar(texto_limpio)
            stems = self.stemizar(tokens)
            
            resultados.append({
                'texto_original': texto,
                'texto_limpio': texto_limpio,
                'tokens': tokens,
                'stems': stems,
                'longitud_tokens': len(tokens)
            })
        
        return pd.DataFrame(resultados)
    
    def obtener_frecuencias(self, textos):
        """
        Obtiene frecuencia de palabras de un conjunto de textos.
        
        Args:
            textos: Lista de strings
            
        Returns:
            DataFrame con frecuencias
        """
        from collections import Counter
        
        todas_palabras = []
        for texto in textos:
            tokens = self.tokenizar(texto)
            todas_palabras.extend(tokens)
        
        if not todas_palabras:
            return pd.DataFrame({'palabra': [], 'frecuencia': [], 'porcentaje': []})
        
        frecuencia = Counter(todas_palabras)
        
        df_frecuencia = pd.DataFrame(
            frecuencia.most_common(),
            columns=['palabra', 'frecuencia']
        )
        
        df_frecuencia['porcentaje'] = (df_frecuencia['frecuencia'] / len(todas_palabras) * 100).round(2)
        
        return df_frecuencia