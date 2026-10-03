# app/utils/motor_wrapper.py
"""
Wrapper que conecta Flask con el motor cualitativo existente.
Convierte el CSV del sistema al formato que espera el motor.
Incluye limpieza universal de marcadores técnicos.
"""

import os
import sys
import re
import pandas as pd
import tempfile
from io import StringIO
from collections import Counter

# ============================================
# AGREGAR EL DIRECTORIO DEL MOTOR AL PATH
# ============================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOTOR_DIR = os.path.join(BASE_DIR, 'motor_cualitativo')

if MOTOR_DIR not in sys.path:
    sys.path.insert(0, MOTOR_DIR)

# Cache global del analizador (singleton)
_analizador_global = None


# ============================================
# STOPWORDS EN ESPAÑOL
# ============================================
STOPWORDS_ES = {
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por',
    'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero',
    'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre', 'cuando',
    'muy', 'sin', 'sobre', 'también', 'me', 'hasta', 'hay', 'donde', 'quien',
    'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra',
    'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos',
    'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos',
    'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas',
    'algunas', 'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu', 'tus',
    'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'mío', 'mía', 'míos', 'mías',
    'tuyo', 'tuya', 'tuyos', 'tuyas', 'suyo', 'suya', 'suyos', 'suyas', 'nuestro',
    'nuestra', 'nuestros', 'nuestras', 'vuestro', 'vuestra', 'vuestros', 'vuestras',
    'esos', 'esas', 'estoy', 'estás', 'está', 'estamos', 'estáis', 'están',
    'sea', 'seas', 'seamos', 'seáis', 'sean', 'seré', 'serás', 'será', 'seremos',
    'seréis', 'serán', 'sería', 'serías', 'seríamos', 'seríais', 'serían',
    'tengo', 'tienes', 'tiene', 'tenemos', 'tenéis', 'tienen', 'tendré', 'tendrás',
    'tendrá', 'tendremos', 'tendréis', 'tendrán', 'tendría', 'tendrías', 'tendríamos',
    'tendríais', 'tendrían', 'hago', 'haces', 'hace', 'hacemos', 'hacéis', 'hacen',
    'haré', 'harás', 'hará', 'haremos', 'haréis', 'harán', 'haría', 'harías',
    'haríamos', 'haríais', 'harían', 'puedo', 'puedes', 'puede', 'podemos', 'podéis',
    'pueden', 'podré', 'podrás', 'podrá', 'podremos', 'podréis', 'podrán',
    'puse', 'puso', 'pusimos', 'pusisteis', 'pusieron', 'haya', 'hayas', 'hayamos',
    'hayáis', 'hayan', 'hubiera', 'hubieras', 'hubiéramos', 'hubierais', 'hubieran',
    'hay', 'sido', 'siendo', 'estado', 'estando', 'tenido', 'teniendo', 'hecho',
    'haciendo', 'dicho', 'diciendo', 'visto', 'viendo', 'puesto', 'poniendo',
    'pregunta', 'respuesta', 'preguntas', 'respuestas', 'encuesta', 'encuestas',
    'aspectos', 'servicios', 'sugerencias', 'comentarios'
}


# ============================================
# LIMPIADOR UNIVERSAL DE MARCADORES TÉCNICOS
# ============================================

def limpiar_marcadores_tecnicos(texto):
    """
    Limpia marcadores técnicos que no son parte de la respuesta real.
    """
    if not texto or pd.isna(texto):
        return ""
    
    texto = str(texto).strip()
    
    # 1. Eliminar marcadores entre corchetes
    texto = re.sub(r'\[[^\]]*\]', ' ', texto)
    
    # 2. Eliminar marcadores entre llaves
    texto = re.sub(r'\{[^\}]*\}', ' ', texto)
    
    # 3. Eliminar marcadores entre paréntesis angulares
    texto = re.sub(r'<[^>]*>', ' ', texto)
    
    # 4. Eliminar prefijos de pregunta
    texto = re.sub(r'\b(P|PREGUNTA|Q|QUESTION)\s*\d+\s*:', ' ', texto, flags=re.IGNORECASE)
    
    # 5. Eliminar comillas externas
    texto = texto.strip('"\'')
    
    # 6. Eliminar puntos sueltos al inicio/final
    texto = re.sub(r'^\s*\.\s*', '', texto)
    texto = re.sub(r'\s*\.\s*$', '', texto)
    
    # 7. Eliminar paréntesis vacíos o con solo puntuación
    texto = re.sub(r'\(\s*[\.,;:\-]*\s*\)', ' ', texto)
    
    # 8. Eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # 9. Verificar si queda contenido útil
    if not texto or re.match(r'^[\s\.,;:\-]*$', texto):
        return ""
    
    return texto


def extraer_palabras_significativas(texto):
    """Extrae palabras significativas de un texto (sin stopwords)"""
    if not texto or pd.isna(texto):
        return []
    
    texto_limpio = str(texto).lower()
    texto_limpio = re.sub(r'[^\w\sáéíóúñü]', ' ', texto_limpio)
    
    palabras = texto_limpio.split()
    palabras = [p for p in palabras if len(p) > 3 and p not in STOPWORDS_ES]
    return palabras


def obtener_analizador():
    """Obtiene o crea el analizador (singleton)"""
    global _analizador_global
    
    if _analizador_global is None:
        print("🧠 Inicializando motor cualitativo (primera vez, puede tardar)...")
        from analizador import AnalizadorCualitativo
        _analizador_global = AnalizadorCualitativo(usar_mejoras=True)
        print("✅ Motor inicializado correctamente")
    
    return _analizador_global


def convertir_csv_sistema_a_motor(df_sistema):
    """Convierte un DataFrame del sistema al formato del motor."""
    registros = []
    
    df_sistema.columns = [
        col.replace('\ufeff', '').strip() for col in df_sistema.columns
    ]
    
    columnas_preguntas = [col for col in df_sistema.columns if col != 'Identificador']
    
    print(f"📋 Columnas detectadas: {columnas_preguntas}")
    
    for idx, row in df_sistema.iterrows():
        identificador = row.get('Identificador', f'R{idx+1:04d}')
        
        for i, columna in enumerate(columnas_preguntas, 1):
            valor = row[columna]
            
            if pd.isna(valor) or str(valor).strip() == '':
                continue
            
            texto_respuesta = limpiar_marcadores_tecnicos(valor)
            
            if not texto_respuesta:
                continue
            
            texto_analisis = f"Pregunta: {columna} Respuesta: {texto_respuesta}"
            
            registros.append({
                'id_pregunta': i,
                'pregunta_texto': columna,
                'respuesta_texto': texto_respuesta,
                'texto_analisis': texto_analisis,
                'identificador': identificador
            })
    
    return pd.DataFrame(registros)


def analizar_con_motor(archivo):
    """Analiza un archivo CSV del sistema usando el motor cualitativo."""
    try:
        content = archivo.stream.read().decode('utf-8-sig')
        df_sistema = pd.read_csv(StringIO(content), quotechar='"')
        
        print(f"\n{'='*60}")
        print(f"📂 CSV del sistema cargado: {len(df_sistema)} filas, {len(df_sistema.columns)} columnas")
        print(f"📋 Columnas: {list(df_sistema.columns)}")
        
        df_motor = convertir_csv_sistema_a_motor(df_sistema)
        
        if df_motor.empty:
            return {
                'success': False,
                'message': 'No se encontraron respuestas de texto para analizar'
            }
        
        print(f"🔄 Convertido: {len(df_motor)} registros, {df_motor['pregunta_texto'].nunique()} preguntas")
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding='utf-8'
        ) as tmp:
            df_motor.to_csv(tmp.name, index=False, encoding='utf-8')
            ruta_temporal = tmp.name
        
        try:
            from lector_csv import leer_csv_encuestas
            df_para_analisis = leer_csv_encuestas(ruta_temporal, usar_texto_analisis=True)
            
            if df_para_analisis.empty:
                return {
                    'success': False,
                    'message': 'No hay datos válidos para analizar'
                }
            
            analizador = obtener_analizador()
            
            print(f"🔍 Analizando sentimiento de {len(df_para_analisis)} textos...")
            
            # ✅ Análisis de sentimiento (SÍ usa pregunta+respuesta para contexto)
            df_sentimiento = analizador.analizar_sentimiento(df_para_analisis)
            
            print(f"✅ Análisis completado")
            
            return convertir_resultados_a_json(df_sentimiento, df_motor, analizador)
            
        finally:
            if os.path.exists(ruta_temporal):
                os.unlink(ruta_temporal)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Error al analizar: {str(e)}'
        }


def convertir_resultados_a_json(df_sentimiento, df_original, analizador):
    """Convierte los resultados del motor a JSON serializable."""
    
    # ============================================
    # SENTIMIENTOS (global)
    # ============================================
    sentimientos_norm = {'positivo': 0, 'neutral': 0, 'negativo': 0}
    
    for _, row in df_sentimiento.iterrows():
        sent = str(row.get('sentimiento', 'Neutral')).lower()
        if 'positivo' in sent:
            sentimientos_norm['positivo'] += 1
        elif 'negativo' in sent:
            sentimientos_norm['negativo'] += 1
        else:
            sentimientos_norm['neutral'] += 1
    
    total = sum(sentimientos_norm.values())
    score_promedio = (
        (sentimientos_norm['positivo'] - sentimientos_norm['negativo']) / total
        if total > 0 else 0
    )
    
    # ============================================
    # ✅ PALABRAS CLAVE (SOLO DE LAS RESPUESTAS)
    # ============================================
    palabras_frecuentes = []
    
    todas_palabras = []
    for texto in df_original['respuesta_texto'].tolist():
        todas_palabras.extend(extraer_palabras_significativas(texto))
    
    conteo_palabras = Counter(todas_palabras).most_common(20)
    palabras_frecuentes = [[p, c] for p, c in conteo_palabras]
    
    # ============================================
    # ✅ TEMAS (SOLO DE LAS RESPUESTAS)
    # ============================================
    temas = []
    
    try:
        # Crear DataFrame con SOLO las respuestas (sin la pregunta)
        df_solo_respuestas = pd.DataFrame({
            'texto': df_original['respuesta_texto'].tolist()
        })
        
        # Filtrar textos válidos
        df_solo_respuestas = df_solo_respuestas[
            df_solo_respuestas['texto'].notna() & 
            (df_solo_respuestas['texto'].str.strip() != '')
        ]
        
        if len(df_solo_respuestas) >= 3:
            # Calcular número de temas basado en cantidad de respuestas
            n_temas = min(3, max(2, len(df_solo_respuestas) // 15))
            
            print(f"🎯 Identificando {n_temas} temas de {len(df_solo_respuestas)} respuestas...")
            
            # Llamar al motor para clasificar temas (SOLO respuestas)
            temas_resultado = analizador.clasificar_temas(
                df_solo_respuestas, 
                n_temas=n_temas, 
                n_top_words=10
            )
            
            if 'temas' in temas_resultado:
                for tema in temas_resultado['temas']:
                    temas.append({
                        'id': tema['tema_id'],
                        'nombre': tema['nombre'],
                        'palabras_clave': tema['palabras_clave'][:10]
                    })
    except Exception as e:
        print(f"⚠️ Error clasificando temas: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================
    # ANÁLISIS POR PREGUNTA
    # ============================================
    resultados_por_pregunta = {}
    
    if 'pregunta_texto' in df_original.columns:
        for pregunta_texto in df_original['pregunta_texto'].unique():
            mask = df_original['pregunta_texto'] == pregunta_texto
            registros_pregunta = df_original[mask]
            textos_pregunta = registros_pregunta['respuesta_texto'].tolist()
            
            if not textos_pregunta:
                continue
            
            # Sentimientos de esta pregunta (SÍ usa pregunta para contexto)
            sentimientos_preg = {'positivo': 0, 'neutral': 0, 'negativo': 0}
            
            try:
                df_pregunta = pd.DataFrame({
                    'texto': [
                        f"Pregunta: {pregunta_texto} Respuesta: {t}"
                        for t in textos_pregunta
                    ]
                })
                
                df_sent_preg = analizador.analizar_sentimiento(df_pregunta)
                
                for _, row_sent in df_sent_preg.iterrows():
                    sent = str(row_sent.get('sentimiento', 'Neutral')).lower()
                    if 'positivo' in sent:
                        sentimientos_preg['positivo'] += 1
                    elif 'negativo' in sent:
                        sentimientos_preg['negativo'] += 1
                    else:
                        sentimientos_preg['neutral'] += 1
            except Exception as e:
                print(f"⚠️ Error analizando sentimiento de '{pregunta_texto}': {e}")
                sentimientos_preg['neutral'] = len(textos_pregunta)
            
            # ✅ Palabras frecuentes de esta pregunta (SOLO respuestas)
            palabras_preg = []
            try:
                palabras_preg_todas = []
                for texto in textos_pregunta:
                    palabras_preg_todas.extend(extraer_palabras_significativas(texto))
                
                conteo = Counter(palabras_preg_todas).most_common(10)
                palabras_preg = [[p, c] for p, c in conteo]
            except:
                pass
            
            # Ejemplos (primeros 5)
            ejemplos = textos_pregunta[:5]
            
            resultados_por_pregunta[pregunta_texto] = {
                'total_respuestas': len(textos_pregunta),
                'sentimientos': sentimientos_preg,
                'palabras_frecuentes': palabras_preg,
                'textos_ejemplo': ejemplos
            }
    
    return {
        'success': True,
        'total_respuestas': len(df_original),
        'total_preguntas': df_original['pregunta_texto'].nunique(),
        'sentimientos': {
            'positivo': sentimientos_norm['positivo'],
            'neutral': sentimientos_norm['neutral'],
            'negativo': sentimientos_norm['negativo'],
            'promedio': round(score_promedio, 2)
        },
        'palabras_frecuentes': palabras_frecuentes,
        'temas': temas,
        'resultados_por_pregunta': resultados_por_pregunta
    }