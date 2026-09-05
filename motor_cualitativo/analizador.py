# motor_cualitativo/analizador.py
import torch
import pandas as pd
import numpy as np
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    pipeline,
    AutoModel
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalizadorCualitativo:
    """
    Motor de análisis cualitativo utilizando modelos Transformers en español.
    Soporta: Análisis de sentimiento, extracción de TF-IDF, clasificación de temas.
    """
    
    def __init__(self, modelo_sentimiento=None, modelo_temas=None, cache_dir=None):
        """
        Inicializa el motor con los modelos seleccionados.
        
        Args:
            modelo_sentimiento: Nombre del modelo para análisis de sentimiento
                              (default: 'dccuchile/bert-base-spanish-wwm-uncased')
            modelo_temas: Nombre del modelo para clasificación de temas
            cache_dir: Directorio para cache de modelos
        """
        self.modelo_sentimiento = modelo_sentimiento or 'dccuchile/bert-base-spanish-wwm-uncased'
        self.modelo_temas = modelo_temas or 'dccuchile/bert-base-spanish-wwm-uncased'
        self.cache_dir = cache_dir or 'data/modelos'
        
        # Crear directorio de cache
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.tokenizer_sentimiento = None
        self.model_sentimiento = None
        self.classifier = None
        self.tfidf_vectorizer = None
        self.lda_model = None
        
        self._cargar_modelos()
        self._descargar_recursos_nltk()
    
    def _descargar_recursos_nltk(self):
        """Descarga recursos de NLTK necesarios"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
    
    def _cargar_modelos(self):
        """Carga los modelos Transformers"""
        try:
            logger.info(f"Cargando tokenizer: {self.modelo_sentimiento}")
            self.tokenizer_sentimiento = AutoTokenizer.from_pretrained(
                self.modelo_sentimiento,
                cache_dir=self.cache_dir,
                use_fast=True
            )
            
            logger.info(f"Cargando modelo de sentimiento: {self.modelo_sentimiento}")
            self.model_sentimiento = AutoModel.from_pretrained(
                self.modelo_sentimiento,
                cache_dir=self.cache_dir
            )
            
            # Configurar pipeline para análisis de sentimiento
            self.classifier = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                tokenizer="nlptown/bert-base-multilingual-uncased-sentiment",
                device=0 if torch.cuda.is_available() else -1,
                model_kwargs={'cache_dir': self.cache_dir}
            )
            
            logger.info("✅ Modelos cargados exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error al cargar modelos: {e}")
            logger.info("Intentando cargar modelos alternativos...")
            self._cargar_modelos_fallback()
    
    def _cargar_modelos_fallback(self):
        """Modelos alternativos si falla la carga principal"""
        try:
            self.classifier = pipeline(
                "sentiment-analysis",
                model="finiteautomata/bert-base-spanish-wwm-cased-finetuned-spa-sentiment",
                device=0 if torch.cuda.is_available() else -1,
                model_kwargs={'cache_dir': self.cache_dir}
            )
            logger.info("✅ Modelos fallback cargados exitosamente")
        except Exception as e:
            logger.error(f"❌ Error en modelo fallback: {e}")
            self.classifier = None
    
    def _obtener_stopwords_espanol(self):
        """Obtiene stopwords en español"""
        try:
            spanish_stopwords = set(stopwords.words('spanish'))
        except:
            spanish_stopwords = set([
                'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
                'y', 'o', 'pero', 'porque', 'como', 'cuando', 'donde',
                'de', 'en', 'a', 'por', 'para', 'con', 'sin', 'sobre',
                'que', 'quien', 'cual', 'cuyo', 'su', 'sus', 'mi', 'tu'
            ])
        return spanish_stopwords
    
    # ============================================
    # ANÁLISIS DE SENTIMIENTO
    # ============================================
    
    def analizar_sentimiento(self, textos, batch_size=16):
        """
        Analiza el sentimiento de una lista de textos.
        
        Args:
            textos: Lista de strings o DataFrame con columna 'texto'
            batch_size: Tamaño del batch para procesamiento
            
        Returns:
            DataFrame con resultados de sentimiento
        """
        if isinstance(textos, pd.DataFrame):
            if 'texto' in textos.columns:
                textos = textos['texto'].tolist()
            else:
                textos = textos.iloc[:, 0].tolist()
        elif isinstance(textos, str):
            textos = [textos]
        
        # ============================================
        # FILTRAR VALORES NULOS Y CONVERTIR A STRING
        # ============================================
        textos_limpios = []
        for t in textos:
            if t is not None and pd.notna(t):
                t_str = str(t).strip()
                if t_str != '':
                    textos_limpios.append(t_str)
        
        textos = textos_limpios
        
        if not textos:
            return pd.DataFrame({'texto': [], 'sentimiento': [], 'score': []})
        
        resultados = []
        
        if self.classifier:
            try:
                for i in range(0, len(textos), batch_size):
                    batch = textos[i:i+batch_size]
                    batch_resultados = self.classifier(batch)
                    resultados.extend(batch_resultados)
            except Exception as e:
                logger.error(f"Error en análisis de sentimiento: {e}")
                resultados = self._analizar_sentimiento_fallback(textos)
        else:
            resultados = self._analizar_sentimiento_fallback(textos)
        
        df_resultados = pd.DataFrame(resultados)
        df_resultados['texto'] = textos
        
        if 'label' in df_resultados.columns:
            df_resultados['sentimiento'] = df_resultados['label'].map(
                lambda x: self._mapear_sentimiento(x)
            )
        
        return df_resultados
    
    def _mapear_sentimiento(self, label):
        """Mapea etiquetas de sentimiento a categorías"""
        mapping = {
            '1 star': 'Muy Negativo',
            '2 stars': 'Negativo',
            '3 stars': 'Neutral',
            '4 stars': 'Positivo',
            '5 stars': 'Muy Positivo',
            'NEGATIVE': 'Negativo',
            'POSITIVE': 'Positivo',
            'NEUTRAL': 'Neutral'
        }
        return mapping.get(label, 'Neutral')
    
    def _analizar_sentimiento_fallback(self, textos):
        """Análisis de sentimiento simple con NLTK"""
        resultados = []
        for texto in textos:
            # Asegurarse de que sea string
            texto = str(texto) if texto is not None else ""
            if not texto.strip():
                resultados.append({
                    'label': 'NEUTRAL',
                    'score': 0.5
                })
                continue
                
            texto_lower = texto.lower()
            palabras_positivas = ['bueno', 'excelente', 'genial', 'maravilloso', 'fantástico', 'mejor', 'gracias', 'encanta', 'satisfecho', 'feliz']
            palabras_negativas = ['malo', 'pésimo', 'terrible', 'horrible', 'peor', 'problema', 'queja', 'deficiente', 'negativo']
            
            pos_count = sum(1 for p in palabras_positivas if p in texto_lower)
            neg_count = sum(1 for n in palabras_negativas if n in texto_lower)
            
            if pos_count > neg_count:
                label = 'POSITIVE'
                score = min(0.9, 0.5 + (pos_count - neg_count) * 0.1)
            elif neg_count > pos_count:
                label = 'NEGATIVE'
                score = min(0.9, 0.5 + (neg_count - pos_count) * 0.1)
            else:
                label = 'NEUTRAL'
                score = 0.5
            
            resultados.append({
                'label': label,
                'score': score
            })
        
        return resultados
    
    # ============================================
    # EXTRACCIÓN DE PALABRAS CLAVE CON TF-IDF
    # ============================================
    
    def extraer_palabras_clave(self, textos, n_top=10, max_features=1000):
        """
        Extrae palabras clave usando TF-IDF.
        
        Args:
            textos: Lista de strings o DataFrame
            n_top: Número de palabras clave a extraer
            max_features: Máximo de características para TF-IDF
            
        Returns:
            DataFrame con palabras clave y sus puntuaciones
        """
        if isinstance(textos, pd.DataFrame):
            if 'texto' in textos.columns:
                textos = textos['texto'].tolist()
            else:
                textos = textos.iloc[:, 0].tolist()
        
        # ============================================
        # FILTRAR Y CONVERTIR A STRING
        # ============================================
        textos_limpios = []
        for t in textos:
            if t is not None and pd.notna(t):
                t_str = str(t).strip()
                if t_str != '':
                    textos_limpios.append(t_str)
        
        textos = textos_limpios
        
        if not textos:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        
        textos_procesados = self._preprocesar_textos(textos)
        
        stopwords_es = self._obtener_stopwords_espanol()
        
        # Ajustar parámetros para datasets pequeños
        n_docs = len(textos_procesados)
        
        if n_docs < 5:
            min_df = 1
        else:
            min_df = 2
        
        # Limitar max_features para datasets pequeños
        max_features = min(max_features, max(50, n_docs * 5))
        
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=list(stopwords_es),
            ngram_range=(1, 2),
            max_df=0.9,
            min_df=min_df
        )
        
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(textos_procesados)
        except ValueError as e:
            logger.warning(f"TF-IDF falló con parámetros ajustados: {e}")
            logger.info("Intentando con min_df=1 y max_df=1.0...")
            
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words=list(stopwords_es),
                ngram_range=(1, 1),
                max_df=1.0,
                min_df=1
            )
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(textos_procesados)
        
        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.toarray()
        promedio_scores = tfidf_scores.mean(axis=0)
        
        if len(feature_names) == 0 or len(promedio_scores) == 0:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        
        # ============================================
        # CORREGIDO: Ajustar n_top al número real de características
        # ============================================
        n_top = min(n_top, len(feature_names))
        
        if n_top == 0:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        
        indices = np.argsort(promedio_scores)[::-1][:n_top]
        
        palabras_clave = []
        for idx in indices:
            palabras_clave.append({
                'palabra': feature_names[idx],
                'tfidf_score': promedio_scores[idx],
                'frecuencia': len([doc for doc in tfidf_scores if doc[idx] > 0])
            })
        
        df_keywords = pd.DataFrame(palabras_clave)
        
        # ============================================
        # CORREGIDO: Asegurar que la longitud coincida
        # ============================================
        if len(df_keywords) > 0:
            palabras_por_documento = []
            for i, doc in enumerate(textos):
                doc_scores = tfidf_scores[i] if i < len(tfidf_scores) else []
                if len(doc_scores) > 0:
                    doc_indices = np.argsort(doc_scores)[::-1][:3]
                    palabras = [feature_names[idx] for idx in doc_indices if doc_scores[idx] > 0]
                else:
                    palabras = []
                palabras_por_documento.append(palabras)
            
            # ============================================
            # CORREGIDO: Asegurar que la longitud coincida exactamente
            # ============================================
            documentos_asociados = palabras_por_documento[:len(df_keywords)]
            # Si hay menos documentos, rellenar con listas vacías
            while len(documentos_asociados) < len(df_keywords):
                documentos_asociados.append([])
            df_keywords['documentos_asociados'] = documentos_asociados
        
        return df_keywords
    
    def _preprocesar_textos(self, textos):
        """Preprocesa textos para TF-IDF"""
        processed = []
        for texto in textos:
            texto = str(texto).lower()
            texto = re.sub(r'[^\w\s]', ' ', texto)
            texto = re.sub(r'\s+', ' ', texto).strip()
            processed.append(texto)
        return processed
    
    # ============================================
    # CLASIFICACIÓN DE TEMAS
    # ============================================
    
    def clasificar_temas(self, textos, n_temas=5, max_features=1000, n_top_words=10):
        """
        Clasifica textos en temas usando LDA.
        
        Args:
            textos: Lista de strings o DataFrame
            n_temas: Número de temas a identificar
            max_features: Máximo de características
            n_top_words: Número de palabras por tema
            
        Returns:
            Dict con temas y asignaciones
        """
        if isinstance(textos, pd.DataFrame):
            if 'texto' in textos.columns:
                textos = textos['texto'].tolist()
            else:
                textos = textos.iloc[:, 0].tolist()
        
        # ============================================
        # FILTRAR Y CONVERTIR A STRING
        # ============================================
        textos_limpios = []
        for t in textos:
            if t is not None and pd.notna(t):
                t_str = str(t).strip()
                if t_str != '':
                    textos_limpios.append(t_str)
        
        textos = textos_limpios
        
        if not textos or len(textos) < 3:
            return {
                'temas': [{'tema_id': i+1, 'nombre': f'Tema {i+1}', 'palabras_clave': [], 'pesos': []} for i in range(n_temas)],
                'asignaciones': pd.DataFrame({'documento': [], 'tema_id': [], 'confianza': [], 'tema_nombre': []}),
                'distribucion_temas': pd.DataFrame()
            }
        
        textos_procesados = self._preprocesar_textos(textos)
        
        stopwords_es = self._obtener_stopwords_espanol()
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=list(stopwords_es),
            max_df=0.9,
            min_df=1
        )
        
        tfidf_matrix = vectorizer.fit_transform(textos_procesados)
        feature_names = vectorizer.get_feature_names_out()
        
        # Ajustar número de temas al número de documentos
        n_temas = min(n_temas, len(textos))
        n_temas = max(n_temas, 2)
        
        self.lda_model = LatentDirichletAllocation(
            n_components=n_temas,
            random_state=42,
            max_iter=100,
            learning_method='batch'
        )
        
        doc_topic_dist = self.lda_model.fit_transform(tfidf_matrix)
        
        temas = []
        for topic_idx, topic in enumerate(self.lda_model.components_):
            top_indices = topic.argsort()[-n_top_words:][::-1]
            top_words = [feature_names[i] for i in top_indices if i < len(feature_names)]
            top_scores = [topic[i] for i in top_indices if i < len(feature_names)]
            
            temas.append({
                'tema_id': topic_idx + 1,
                'nombre': f"Tema {topic_idx + 1}",
                'palabras_clave': top_words,
                'pesos': top_scores
            })
        
        asignaciones = []
        for i, dist in enumerate(doc_topic_dist):
            tema_principal = np.argmax(dist) + 1
            confianza = np.max(dist)
            asignaciones.append({
                'documento': textos[i] if i < len(textos) else '',
                'tema_id': tema_principal,
                'confianza': confianza,
                'tema_nombre': f"Tema {tema_principal}"
            })
        
        return {
            'temas': temas,
            'asignaciones': pd.DataFrame(asignaciones),
            'distribucion_temas': pd.DataFrame(doc_topic_dist, 
                                              columns=[f'Tema_{i+1}' for i in range(n_temas)])
        }
    
    # ============================================
    # ANÁLISIS COMPLETO
    # ============================================
    
    def analizar_completo(self, textos, n_temas=5, n_keywords=10):
        """
        Realiza análisis completo: sentimiento, TF-IDF y temas.
        
        Args:
            textos: Lista de strings o DataFrame
            n_temas: Número de temas
            n_keywords: Número de palabras clave
            
        Returns:
            Dict con todos los resultados
        """
        if isinstance(textos, pd.DataFrame):
            if 'texto' in textos.columns:
                textos = textos['texto'].tolist()
            else:
                textos = textos.iloc[:, 0].tolist()
        
        # ============================================
        # FILTRAR Y CONVERTIR A STRING
        # ============================================
        textos_limpios = []
        for t in textos:
            if t is not None and pd.notna(t):
                t_str = str(t).strip()
                if t_str != '':
                    textos_limpios.append(t_str)
        
        textos = textos_limpios
        
        if not textos:
            return {
                'resultados': pd.DataFrame({'texto': [], 'sentimiento': [], 'score_confianza': [], 'tema': [], 'confianza_tema': []}),
                'sentimiento': pd.DataFrame({'texto': [], 'sentimiento': [], 'score': []}),
                'palabras_clave': pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []}),
                'temas': {'temas': [], 'asignaciones': pd.DataFrame(), 'distribucion_temas': pd.DataFrame()},
                'resumen': {'total_textos': 0, 'sentimiento_predominante': 'N/A', 'distribucion_sentimiento': {}, 'distribucion_temas': {}}
            }
        
        df_textos = pd.DataFrame({'texto': textos})
        
        logger.info("Analizando sentimiento...")
        df_sentimiento = self.analizar_sentimiento(df_textos)
        
        logger.info("Extrayendo palabras clave...")
        try:
            df_keywords = self.extraer_palabras_clave(df_textos, n_top=n_keywords)
            # ============================================
            # CORREGIDO: Si no hay palabras clave, devolver DataFrame vacío
            # ============================================
            if df_keywords is None or df_keywords.empty:
                df_keywords = pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        except Exception as e:
            logger.warning(f"Error en extracción de keywords: {e}")
            df_keywords = pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        
        logger.info("Clasificando temas...")
        try:
            temas_resultados = self.clasificar_temas(df_textos, n_temas=n_temas)
        except Exception as e:
            logger.warning(f"Error en clasificación de temas: {e}")
            temas_resultados = {
                'temas': [],
                'asignaciones': pd.DataFrame({'documento': [], 'tema_id': [], 'confianza': [], 'tema_nombre': []}),
                'distribucion_temas': pd.DataFrame()
            }
        
        df_resultados = df_textos.copy()
        df_resultados['sentimiento'] = df_sentimiento['sentimiento'] if 'sentimiento' in df_sentimiento.columns else 'Neutral'
        df_resultados['score_confianza'] = df_sentimiento['score'] if 'score' in df_sentimiento.columns else 0.5
        
        if 'asignaciones' in temas_resultados and not temas_resultados['asignaciones'].empty:
            df_resultados['tema'] = temas_resultados['asignaciones']['tema_nombre']
            df_resultados['confianza_tema'] = temas_resultados['asignaciones']['confianza']
        else:
            df_resultados['tema'] = 'Sin tema'
            df_resultados['confianza_tema'] = 0.0
        
        return {
            'resultados': df_resultados,
            'sentimiento': df_sentimiento,
            'palabras_clave': df_keywords,
            'temas': temas_resultados,
            'resumen': self._generar_resumen(df_resultados)
        }
    
    def _generar_resumen(self, df_resultados):
        """Genera un resumen estadístico de los resultados"""
        resumen = {}
        
        if 'sentimiento' in df_resultados.columns:
            resumen['distribucion_sentimiento'] = df_resultados['sentimiento'].value_counts().to_dict()
        else:
            resumen['distribucion_sentimiento'] = {}
        
        if 'tema' in df_resultados.columns:
            resumen['distribucion_temas'] = df_resultados['tema'].value_counts().to_dict()
        else:
            resumen['distribucion_temas'] = {}
        
        resumen['total_textos'] = len(df_resultados)
        
        if 'sentimiento' in df_resultados.columns and not df_resultados.empty:
            resumen['sentimiento_predominante'] = df_resultados['sentimiento'].mode()[0]
        else:
            resumen['sentimiento_predominante'] = 'N/A'
        
        return resumen