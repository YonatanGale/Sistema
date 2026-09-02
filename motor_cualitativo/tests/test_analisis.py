# motor_cualitativo/tests/test_analisis.py
import sys
import os

# Agregar el directorio padre al path para que Python pueda encontrar el módulo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from analizador import AnalizadorCualitativo
from procesador import ProcesadorTexto
from utils import crear_dataset_prueba, guardar_resultados


def test_analisis_completo():
    """Prueba el análisis completo del motor"""
    print("\n" + "="*60)
    print("🧪 TEST: ANÁLISIS CUALITATIVO COMPLETO")
    print("="*60)
    
    # 1. Crear dataset de prueba
    print("\n📊 Creando dataset de prueba...")
    df = crear_dataset_prueba(15)
    print(f"Dataset creado: {len(df)} textos")
    print(df.head())
    
    # 2. Inicializar analizador
    print("\n🤖 Inicializando Analizador Cualitativo...")
    analizador = AnalizadorCualitativo()
    
    # 3. Procesar textos
    print("\n🔧 Procesando textos...")
    procesador = ProcesadorTexto()
    df_procesado = procesador.procesar_lote(df)
    print("Textos procesados:")
    print(df_procesado[['texto_original', 'longitud_tokens']].head())
    
    # 4. Análisis completo
    print("\n📈 Realizando análisis completo...")
    resultados = analizador.analizar_completo(df, n_temas=3, n_keywords=10)
    
    # 5. Mostrar resultados
    print("\n" + "-"*40)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("-"*40)
    
    print("\n1️⃣ DISTRIBUCIÓN DE SENTIMIENTO:")
    print(resultados['resumen']['distribucion_sentimiento'])
    
    print("\n2️⃣ PALABRAS CLAVE (TF-IDF):")
    print(resultados['palabras_clave'])
    
    print("\n3️⃣ TEMAS IDENTIFICADOS:")
    for tema in resultados['temas']['temas']:
        print(f"\n  {tema['nombre']}:")
        print(f"  Palabras clave: {tema['palabras_clave']}")
    
    print("\n4️⃣ ASIGNACIONES DE TEMAS:")
    print(resultados['temas']['asignaciones'].head())
    
    print("\n5️⃣ RESUMEN:")
    print(f"  Total textos: {resultados['resumen']['total_textos']}")
    print(f"  Sentimiento predominante: {resultados['resumen']['sentimiento_predominante']}")
    
    # 6. Guardar resultados
    print("\n💾 Guardando resultados...")
    guardar_resultados(resultados, "test_analisis_completo", formato='excel')
    
    print("\n✅ Prueba completada exitosamente!")
    return resultados


def test_analisis_sentimiento():
    """Prueba específica de análisis de sentimiento"""
    print("\n" + "="*60)
    print("🧪 TEST: ANÁLISIS DE SENTIMIENTO")
    print("="*60)
    
    textos = [
        "El servicio es excelente, muy satisfecho.",
        "No me gusta nada, es pésimo.",
        "Regular, tiene cosas buenas y malas.",
        "Me encanta la comunidad, son muy acogedores.",
        "Necesita mejorar urgentemente la organización.",
        "Es un lugar maravilloso para crecer espiritualmente.",
        "La atención es buena pero pueden mejorar."
    ]
    
    df_textos = pd.DataFrame({'texto': textos})
    
    print("\nTextos a analizar:")
    for i, t in enumerate(textos):
        print(f"{i+1}. {t}")
    
    analizador = AnalizadorCualitativo()
    resultados = analizador.analizar_sentimiento(df_textos)
    
    print("\n📊 Resultados de sentimiento:")
    print(resultados[['texto', 'sentimiento', 'score']])
    
    return resultados


def test_extraccion_keywords():
    """Prueba de extracción de palabras clave"""
    print("\n" + "="*60)
    print("🧪 TEST: EXTRACCIÓN DE PALABRAS CLAVE")
    print("="*60)
    
    textos = [
        "El servicio pastoral de la parroquia es excelente.",
        "Los grupos de oración y retiros espirituales son muy buenos.",
        "La comunidad es muy unida y solidaria.",
        "Necesitamos mejorar la comunicación y la infraestructura.",
        "El párroco es muy dedicado y comprometido."
    ]
    
    df_textos = pd.DataFrame({'texto': textos})
    
    print("\nTextos analizados:")
    for i, t in enumerate(textos):
        print(f"{i+1}. {t}")
    
    analizador = AnalizadorCualitativo()
    keywords = analizador.extraer_palabras_clave(df_textos, n_top=8)
    
    print("\n📊 Palabras clave extraídas:")
    print(keywords)
    
    return keywords


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 INICIANDO PRUEBAS DEL MOTOR DE ANÁLISIS CUALITATIVO")
    print("="*60)
    
    try:
        # Test 1: Análisis de sentimiento
        test_analisis_sentimiento()
        
        # Test 2: Extracción de palabras clave
        test_extraccion_keywords()
        
        # Test 3: Análisis completo
        test_analisis_completo()
        
        print("\n" + "="*60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()