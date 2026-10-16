# motor_cualitativo/analizador.py
"""
Motor de análisis cualitativo basado en BETO (BERT en español).

Modelos utilizados:
  - finiteautomata/beto-sentiment-analysis
      BETO afinado para clasificación de sentimiento en español (POS/NEG/NEU).
      Referencia: Pérez et al. (2021). pysentimiento. arXiv:2106.09462.
  - dccuchile/bert-base-spanish-wwm-uncased
      BETO base, usado como modelo de representación contextual del español
      (embeddings) y tokenizador. Referencia: Cañete et al. (2020).

Soporta: análisis de sentimiento, extracción de palabras clave (TF-IDF)
y modelado de tópicos (LDA).
"""

import os
import re
import logging

import numpy as np
import pandas as pd
import torch

from transformers import (
    AutoTokenizer,
    AutoModel,
    pipeline,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

import nltk
from nltk.corpus import stopwords

# ============================================================
# IMPORTAR REGLAS HEURÍSTICAS
# ============================================================
try:
    from mejoras_sentimiento import aplicar_ajustes, ajustar_sentimiento
    MEJORAS_DISPONIBLES = True
except ImportError:
    try:
        from .mejoras_sentimiento import aplicar_ajustes, ajustar_sentimiento
        MEJORAS_DISPONIBLES = True
    except ImportError:
        MEJORAS_DISPONIBLES = False
        print("⚠️ No se encontró mejoras_sentimiento.py - "
              "Los ajustes heurísticos no están disponibles")

# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTES DE MODELOS BETO
# ============================================================
MODELO_BETO_SENTIMIENTO = "finiteautomata/beto-sentiment-analysis"
MODELO_BETO_BASE = "dccuchile/bert-base-spanish-wwm-uncased"

# Mapeo de etiquetas del modelo finiteautomata → categorías del sistema
MAPA_BETO_SENTIMIENTO = {
    "POS": "Positivo",
    "NEG": "Negativo",
    "NEU": "Neutral",
    # Compatibilidad con variantes que usan texto completo
    "POSITIVE": "Positivo",
    "NEGATIVE": "Negativo",
    "NEUTRAL": "Neutral",
    # Compatibilidad con modelos que usan LABEL_0/1/2
    "LABEL_0": "Negativo",
    "LABEL_1": "Neutral",
    "LABEL_2": "Positivo",
}


class AnalizadorCualitativo:
    """
    Motor de análisis cualitativo utilizando BETO (BERT en español).

    Pipeline:
      1. Análisis de sentimiento con BETO afinado (POS/NEG/NEU).
      2. Extracción de palabras clave con TF-IDF.
      3. Modelado de tópicos con LDA.
      4. Representación contextual opcional con BETO base.
    """

    def __init__(self, modelo_sentimiento=None, modelo_temas=None,
                 cache_dir=None, usar_mejoras=True):
        """
        Inicializa el motor con los modelos BETO.

        Args:
            modelo_sentimiento: Nombre del modelo BETO para sentimiento.
                                Por defecto: finiteautomata/beto-sentiment-analysis
            modelo_temas: Modelo base BETO para representación contextual.
                          Por defecto: dccuchile/bert-base-spanish-wwm-uncased
            cache_dir: Directorio de caché para modelos.
            usar_mejoras: Si True, aplica reglas heurísticas de sentimiento.
        """
        # Modelo principal: BETO afinado para sentimiento
        self.modelo_sentimiento = modelo_sentimiento or MODELO_BETO_SENTIMIENTO
        # Modelo base: BETO puro como encoder
        self.modelo_temas = modelo_temas or MODELO_BETO_BASE
        self.cache_dir = cache_dir or 'data/modelos'
        self.usar_mejoras = usar_mejoras and MEJORAS_DISPONIBLES

        os.makedirs(self.cache_dir, exist_ok=True)

        # Objetos de modelos
        self.classifier = None                    # pipeline BETO afinado
        self.tokenizer_beto = None                # tokenizer BETO base
        self.model_beto = None                    # encoder BETO base
        self.tfidf_vectorizer = None
        self.lda_model = None

        self._cargar_modelos()
        self._descargar_recursos_nltk()

        if self.usar_mejoras:
            logger.info("✅ Reglas heurísticas de sentimiento ACTIVADAS")
        else:
            logger.info("⚠️ Reglas heurísticas de sentimiento DESACTIVADAS")

    # --------------------------------------------------------
    # CARGA DE RECURSOS
    # --------------------------------------------------------
    def _descargar_recursos_nltk(self):
        """Descarga recursos NLTK necesarios (silencioso)."""
        for ruta, paquete in [('tokenizers/punkt', 'punkt'),
                              ('corpora/stopwords', 'stopwords')]:
            try:
                nltk.data.find(ruta)
            except LookupError:
                nltk.download(paquete, quiet=True)

    def _cargar_modelos(self):
        """Carga los modelos BETO: pipeline de sentimiento + encoder base."""
        try:
            # --- BETO afinado para sentimiento ---
            logger.info(f"Cargando pipeline BETO afinado: {self.modelo_sentimiento}")
            self.classifier = pipeline(
                "sentiment-analysis",
                model=self.modelo_sentimiento,
                tokenizer=self.modelo_sentimiento,
                device=0 if torch.cuda.is_available() else -1,
                truncation=True,
                max_length=512,
                model_kwargs={'cache_dir': self.cache_dir},
            )
            logger.info("✅ Pipeline de sentimiento BETO cargado")

            # --- BETO base como encoder contextual ---
            logger.info(f"Cargando tokenizer BETO base: {self.modelo_temas}")
            self.tokenizer_beto = AutoTokenizer.from_pretrained(
                self.modelo_temas,
                cache_dir=self.cache_dir,
                use_fast=True,
            )
            logger.info(f"Cargando encoder BETO base: {self.modelo_temas}")
            self.model_beto = AutoModel.from_pretrained(
                self.modelo_temas,
                cache_dir=self.cache_dir,
            )
            self.model_beto.eval()
            logger.info("✅ Encoder BETO base cargado")

        except Exception as e:
            logger.error(f"❌ Error al cargar modelos BETO: {e}")
            logger.info("Activando modo fallback (heurísticas NLTK)...")
            self._cargar_modelos_fallback()

    def _cargar_modelos_fallback(self):
        """Modo de emergencia: sin modelo, solo heurísticas NLTK."""
        self.classifier = None
        self.tokenizer_beto = None
        self.model_beto = None
        logger.warning("⚠️ Modo fallback activo: se usarán reglas heurísticas NLTK")

    def _obtener_stopwords_espanol(self):
        """Obtiene el conjunto de stopwords en español."""
        try:
            return set(stopwords.words('spanish'))
        except Exception:
            return {
                'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
                'y', 'o', 'pero', 'porque', 'como', 'cuando', 'donde',
                'de', 'en', 'a', 'por', 'para', 'con', 'sin', 'sobre',
                'que', 'quien', 'cual', 'cuyo', 'su', 'sus', 'mi', 'tu',
            }

    # --------------------------------------------------------
    # EMBEDDINGS CONTEXTUALES (BETO base)
    # --------------------------------------------------------
    def obtener_embeddings(self, textos, batch_size=16, pooling='mean'):
        """
        Devuelve los embeddings contextuales de BETO base para una lista
        de textos. Se pueden usar para similitud semántica, clustering o
        como características para modelos supervisados.

        Args:
            textos: Lista de strings o DataFrame con columna 'texto'.
            batch_size: Tamaño del batch.
            pooling: 'mean' (promedio de tokens) o 'cls' (token [CLS]).

        Returns:
            np.ndarray de forma (n_textos, dim_oculta).
        """
        if self.model_beto is None or self.tokenizer_beto is None:
            raise RuntimeError("Encoder BETO base no disponible")

        if isinstance(textos, pd.DataFrame):
            col = 'texto' if 'texto' in textos.columns else textos.columns[0]
            textos = textos[col].tolist()

        textos = [str(t).strip() for t in textos
                  if t is not None and str(t).strip()]
        if not textos:
            return np.zeros((0, 768))

        embeddings = []
        self.model_beto.eval()
        with torch.no_grad():
            for i in range(0, len(textos), batch_size):
                batch = textos[i:i + batch_size]
                encoded = self.tokenizer_beto(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors='pt',
                )
                outputs = self.model_beto(**encoded)
                hidden = outputs.last_hidden_state  # (B, T, H)

                if pooling == 'cls':
                    vec = hidden[:, 0, :]
                else:
                    mask = encoded['attention_mask'].unsqueeze(-1)
                    summed = (hidden * mask).sum(dim=1)
                    counts = mask.sum(dim=1).clamp(min=1e-9)
                    vec = summed / counts

                embeddings.append(vec.cpu().numpy())

        return np.vstack(embeddings)

    # ========================================================
    # ANÁLISIS DE SENTIMIENTO
    # ========================================================
    def analizar_sentimiento(self, textos, batch_size=16, aplicar_mejoras=None):
        """
        Analiza el sentimiento de una lista de textos con BETO afinado.

        Args:
            textos: Lista de strings o DataFrame con columna 'texto'.
            batch_size: Tamaño del batch.
            aplicar_mejoras: Si None, usa el valor por defecto del analizador.

        Returns:
            DataFrame con columnas: texto, sentimiento, score [, sentimiento_original].
        """
        if aplicar_mejoras is None:
            aplicar_mejoras = self.usar_mejoras

        # Normalizar entrada
        if isinstance(textos, pd.DataFrame):
            col = 'texto' if 'texto' in textos.columns else textos.columns[0]
            textos = textos[col].tolist()
        elif isinstance(textos, str):
            textos = [textos]

        # Limpiar valores nulos / vacíos
        textos = [str(t).strip() for t in textos
                  if t is not None and pd.notna(t) and str(t).strip() != '']

        if not textos:
            return pd.DataFrame({'texto': [], 'sentimiento': [], 'score': []})

        # Ejecutar clasificador (pipeline BETO afinado)
        resultados = []
        if self.classifier is not None:
            try:
                for i in range(0, len(textos), batch_size):
                    batch = textos[i:i + batch_size]
                    resultados.extend(self.classifier(batch))
            except Exception as e:
                logger.error(f"Error en pipeline BETO: {e}")
                resultados = self._analizar_sentimiento_fallback(textos)
        else:
            resultados = self._analizar_sentimiento_fallback(textos)

        df = pd.DataFrame(resultados)
        df['texto'] = textos

        if 'label' in df.columns:
            df['sentimiento'] = df['label'].map(self._mapear_sentimiento)

        # Aplicar reglas heurísticas (upgrade a Muy Positivo/Negativo si aplica)
        if aplicar_mejoras and MEJORAS_DISPONIBLES:
            logger.info("Aplicando reglas heurísticas de sentimiento...")
            sent_ajustados = []
            scores_ajustados = []
            for _, row in df.iterrows():
                s, sc = ajustar_sentimiento(
                    row.get('texto', ''),
                    row.get('sentimiento', 'Neutral'),
                    row.get('score', 0.5),
                )
                sent_ajustados.append(s)
                scores_ajustados.append(sc)

            df['sentimiento_original'] = df['sentimiento']
            df['sentimiento'] = sent_ajustados
            df['score'] = scores_ajustados

        return df

    def _mapear_sentimiento(self, label):
        """Mapea etiquetas del modelo BETO a categorías del sistema."""
        return MAPA_BETO_SENTIMIENTO.get(label, 'Neutral')

    def _analizar_sentimiento_fallback(self, textos):
        """Fallback NLTK: heurística léxica simple cuando no hay modelo."""
        positivas = ['bueno', 'excelente', 'genial', 'maravilloso', 'fantástico',
                     'mejor', 'gracias', 'encanta', 'satisfecho', 'feliz']
        negativas = ['malo', 'pésimo', 'terrible', 'horrible', 'peor',
                     'problema', 'queja', 'deficiente', 'negativo']

        resultados = []
        for texto in textos:
            texto = str(texto or '').lower()
            if not texto.strip():
                resultados.append({'label': 'NEU', 'score': 0.5})
                continue

            pos = sum(1 for p in positivas if p in texto)
            neg = sum(1 for n in negativas if n in texto)

            if pos > neg:
                label, score = 'POS', min(0.9, 0.5 + (pos - neg) * 0.1)
            elif neg > pos:
                label, score = 'NEG', min(0.9, 0.5 + (neg - pos) * 0.1)
            else:
                label, score = 'NEU', 0.5

            resultados.append({'label': label, 'score': score})
        return resultados

    # ========================================================
    # EXTRACCIÓN DE PALABRAS CLAVE (TF-IDF)
    # ========================================================
    def extraer_palabras_clave(self, textos, n_top=10, max_features=1000):
        """Extrae palabras clave usando TF-IDF."""
        if isinstance(textos, pd.DataFrame):
            col = 'texto' if 'texto' in textos.columns else textos.columns[0]
            textos = textos[col].tolist()

        textos = [str(t).strip() for t in textos
                  if t is not None and pd.notna(t) and str(t).strip() != '']

        if not textos:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})

        textos_proc = self._preprocesar_textos(textos)
        stopwords_es = self._obtener_stopwords_espanol()

        n_docs = len(textos_proc)
        min_df = 1 if n_docs < 5 else 2
        max_features = min(max_features, max(50, n_docs * 5))

        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=list(stopwords_es),
            ngram_range=(1, 2),
            max_df=0.9,
            min_df=min_df,
        )

        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(textos_proc)
        except ValueError as e:
            logger.warning(f"TF-IDF falló: {e}, reintentando con parámetros relajados")
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words=list(stopwords_es),
                ngram_range=(1, 1),
                max_df=1.0,
                min_df=1,
            )
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(textos_proc)

        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.toarray()
        promedio = tfidf_scores.mean(axis=0)

        if len(feature_names) == 0 or len(promedio) == 0:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})

        n_top = min(n_top, len(feature_names))
        if n_top == 0:
            return pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})

        indices = np.argsort(promedio)[::-1][:n_top]

        palabras = []
        for idx in indices:
            palabras.append({
                'palabra': feature_names[idx],
                'tfidf_score': float(promedio[idx]),
                'frecuencia': int(sum(1 for doc in tfidf_scores if doc[idx] > 0)),
            })

        df_kw = pd.DataFrame(palabras)

        if len(df_kw) > 0:
            docs_asociados = []
            for i, _ in enumerate(textos):
                if i < len(tfidf_scores):
                    doc_scores = tfidf_scores[i]
                    top_idx = np.argsort(doc_scores)[::-1][:3]
                    pals = [feature_names[j] for j in top_idx if doc_scores[j] > 0]
                else:
                    pals = []
                docs_asociados.append(pals)

            docs_asociados = docs_asociados[:len(df_kw)]
            while len(docs_asociados) < len(df_kw):
                docs_asociados.append([])
            df_kw['documentos_asociados'] = docs_asociados

        return df_kw

    def _preprocesar_textos(self, textos):
        """Preprocesamiento básico: minúsculas, sin signos, sin números."""
        procesados = []
        for texto in textos:
            t = str(texto).lower()
            t = re.sub(r'[^\wáéíóúñü\s]', ' ', t)
            t = re.sub(r'\s+', ' ', t).strip()
            procesados.append(t)
        return procesados

    # ========================================================
    # MODELADO DE TÓPICOS (LDA)
    # ========================================================
    def clasificar_temas(self, textos, n_temas=5, max_features=1000, n_top_words=10):
        """
        Descubre tópicos latentes usando LDA (modelado de tópicos no supervisado).
        """
        if isinstance(textos, pd.DataFrame):
            col = 'texto' if 'texto' in textos.columns else textos.columns[0]
            textos = textos[col].tolist()

        textos = [str(t).strip() for t in textos
                  if t is not None and pd.notna(t) and str(t).strip() != '']

        if not textos or len(textos) < 3:
            return {
                'temas': [],
                'asignaciones': pd.DataFrame(
                    columns=['documento', 'tema_id', 'confianza', 'tema_nombre']),
                'distribucion_temas': pd.DataFrame(),
            }

        textos_proc = self._preprocesar_textos(textos)
        stopwords_es = self._obtener_stopwords_espanol()

        vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words=list(stopwords_es),
            max_df=0.9,
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(textos_proc)
        feature_names = vectorizer.get_feature_names_out()

        n_temas = max(2, min(n_temas, len(textos)))

        self.lda_model = LatentDirichletAllocation(
            n_components=n_temas,
            random_state=42,
            max_iter=100,
            learning_method='batch',
        )

        doc_topic_dist = self.lda_model.fit_transform(tfidf_matrix)

        temas = []
        for idx, topic in enumerate(self.lda_model.components_):
            top_idx = topic.argsort()[-n_top_words:][::-1]
            top_words = [feature_names[i] for i in top_idx if i < len(feature_names)]
            top_scores = [float(topic[i]) for i in top_idx if i < len(feature_names)]
            temas.append({
                'tema_id': idx + 1,
                'nombre': f"Tema {idx + 1}",
                'palabras_clave': top_words,
                'pesos': top_scores,
            })

        asignaciones = []
        for i, dist in enumerate(doc_topic_dist):
            tema_id = int(np.argmax(dist)) + 1
            asignaciones.append({
                'documento': textos[i] if i < len(textos) else '',
                'tema_id': tema_id,
                'confianza': float(np.max(dist)),
                'tema_nombre': f"Tema {tema_id}",
            })

        return {
            'temas': temas,
            'asignaciones': pd.DataFrame(asignaciones),
            'distribucion_temas': pd.DataFrame(
                doc_topic_dist,
                columns=[f'Tema_{i+1}' for i in range(n_temas)]
            ),
        }

    # ========================================================
    # ANÁLISIS COMPLETO
    # ========================================================
    def analizar_completo(self, textos, n_temas=5, n_keywords=10):
        """Ejecuta sentimiento + palabras clave + modelado de tópicos."""
        if isinstance(textos, pd.DataFrame):
            col = 'texto' if 'texto' in textos.columns else textos.columns[0]
            textos = textos[col].tolist()

        textos = [str(t).strip() for t in textos
                  if t is not None and pd.notna(t) and str(t).strip() != '']

        if not textos:
            return {
                'resultados': pd.DataFrame(),
                'sentimiento': pd.DataFrame(),
                'palabras_clave': pd.DataFrame(),
                'temas': {'temas': [], 'asignaciones': pd.DataFrame(),
                          'distribucion_temas': pd.DataFrame()},
                'resumen': {
                    'total_textos': 0,
                    'sentimiento_predominante': 'N/A',
                    'distribucion_sentimiento': {},
                    'distribucion_temas': {},
                },
            }

        df_textos = pd.DataFrame({'texto': textos})

        logger.info("Analizando sentimiento con BETO...")
        df_sentimiento = self.analizar_sentimiento(df_textos)

        logger.info("Extrayendo palabras clave con TF-IDF...")
        try:
            df_kw = self.extraer_palabras_clave(df_textos, n_top=n_keywords)
            if df_kw is None or df_kw.empty:
                df_kw = pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})
        except Exception as e:
            logger.warning(f"Error en extracción de keywords: {e}")
            df_kw = pd.DataFrame({'palabra': [], 'tfidf_score': [], 'frecuencia': []})

        logger.info("Modelando tópicos con LDA...")
        try:
            temas_res = self.clasificar_temas(df_textos, n_temas=n_temas)
        except Exception as e:
            logger.warning(f"Error en modelado de tópicos: {e}")
            temas_res = {
                'temas': [],
                'asignaciones': pd.DataFrame(
                    columns=['documento', 'tema_id', 'confianza', 'tema_nombre']),
                'distribucion_temas': pd.DataFrame(),
            }

        # Consolidar resultados
        df_resultados = df_textos.copy()
        df_resultados['sentimiento'] = (
            df_sentimiento['sentimiento']
            if 'sentimiento' in df_sentimiento.columns else 'Neutral'
        )
        df_resultados['score_confianza'] = (
            df_sentimiento['score']
            if 'score' in df_sentimiento.columns else 0.5
        )
        if 'sentimiento_original' in df_sentimiento.columns:
            df_resultados['sentimiento_original'] = df_sentimiento['sentimiento_original']

        if not temas_res['asignaciones'].empty:
            df_resultados['tema'] = temas_res['asignaciones']['tema_nombre']
            df_resultados['confianza_tema'] = temas_res['asignaciones']['confianza']
        else:
            df_resultados['tema'] = 'Sin tema'
            df_resultados['confianza_tema'] = 0.0

        return {
            'resultados': df_resultados,
            'sentimiento': df_sentimiento,
            'palabras_clave': df_kw,
            'temas': temas_res,
            'resumen': self._generar_resumen(df_resultados),
        }

    def _generar_resumen(self, df_resultados):
        """Genera un resumen estadístico del análisis."""
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