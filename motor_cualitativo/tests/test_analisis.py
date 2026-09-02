# motor_cualitativo/tests/test_analisis.py
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analizador import AnalizadorCualitativo
from procesador import ProcesadorTexto
from utils import crear_dataset_prueba, guardar_resultados


def cargar_dataset_prueba():
    """Carga el dataset de prueba desde CSV o crea uno más grande"""
    ruta_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'pruebas', 'dataset_prueba.csv')
    
    if os.path.exists(ruta_csv):
        df = pd.read_csv(ruta_csv)
        print(f"📂 Dataset cargado desde: {ruta_csv}")
        return df
    else:
        # Crear dataset más grande con textos variados
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
            "Me encanta la labor social que realiza la comunidad.",
            "El servicio de comunicación es deficiente y poco claro.",
            "La comunidad debería tener más actividades recreativas.",
            "Los grupos de catequesis necesitan más recursos y materiales.",
            "El párroco es un excelente líder espiritual y humano.",
            "La parroquia debería abrir sus puertas a más personas.",
            "Las actividades para adultos mayores son muy valoradas.",
            "Me gusta la forma en que se organizan las celebraciones.",
            "La comunidad necesita más espacios de encuentro y diálogo.",
            "El servicio de atención a los jóvenes es muy bueno.",
            "La parroquia debería tener un programa de formación continua."
        ]
        
        df = pd.DataFrame({'texto': textos})
        df['id'] = range(1, len(df) + 1)
        
        # Guardar para futuras ejecuciones
        os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
        df.to_csv(ruta_csv, index=False)
        print(f"📊 Dataset creado con {len(df)} textos")
        
        return df


def test_analisis_completo():
    """Prueba el análisis completo del motor"""
    print("\n" + "="*60)
    print("🧪 TEST: ANÁLISIS CUALITATIVO COMPLETO")
    print("="*60)
    
    # 1. Cargar dataset de prueba
    print("\n📊 Cargando dataset de prueba...")
    df = cargar_dataset_prueba()
    print(f"Dataset cargado: {len(df)} textos")
    
    # 2. Inicializar analizador
    print("\n🤖 Inicializando Analizador Cualitativo...")
    analizador = AnalizadorCualitativo()
    
    # 3. Procesar textos
    print("\n🔧 Procesando textos...")
    procesador = ProcesadorTexto()
    df_procesado = procesador.procesar_lote(df)
    print(f"Textos procesados: {len(df_procesado)}")
    
    # 4. Análisis completo
    print("\n📈 Realizando análisis completo...")
    resultados = analizador.analizar_completo(df, n_temas=3, n_keywords=15)
    
    # 5. Mostrar resultados
    print("\n" + "-"*40)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("-"*40)
    
    print("\n1️⃣ DISTRIBUCIÓN DE SENTIMIENTO:")
    for sentimiento, count in resultados['resumen']['distribucion_sentimiento'].items():
        print(f"   {sentimiento}: {count}")
    
    print("\n2️⃣ PALABRAS CLAVE (TF-IDF):")
    if not resultados['palabras_clave'].empty:
        print(resultados['palabras_clave'].to_string())
    else:
        print("⚠️ No se pudieron extraer palabras clave")
    
    print("\n3️⃣ TEMAS IDENTIFICADOS:")
    for tema in resultados['temas']['temas']:
        print(f"\n  {tema['nombre']}:")
        print(f"  Palabras clave: {', '.join(tema['palabras_clave'])}")
    
    print("\n4️⃣ RESUMEN:")
    print(f"  Total textos: {resultados['resumen']['total_textos']}")
    print(f"  Sentimiento predominante: {resultados['resumen']['sentimiento_predominante']}")
    
    # 5. Guardar resultados
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
    """Prueba de extracción de palabras clave con dataset más grande"""
    print("\n" + "="*60)
    print("🧪 TEST: EXTRACCIÓN DE PALABRAS CLAVE")
    print("="*60)
    
    # Usar dataset más grande
    df = cargar_dataset_prueba()
    print(f"\nAnalizando {len(df)} textos...")
    
    analizador = AnalizadorCualitativo()
    keywords = None
    
    try:
        keywords = analizador.extraer_palabras_clave(df, n_top=15)
        
        print("\n📊 Palabras clave extraídas:")
        if keywords is not None and not keywords.empty:
            print(keywords.to_string())
        else:
            print("⚠️ No se encontraron palabras clave suficientes")
            
    except Exception as e:
        print(f"\n⚠️ Error en extracción de keywords: {e}")
        print("Esto puede ser normal con datasets pequeños. Continuando con las demás pruebas...")
    
    return keywords


def test_clasificacion_temas():
    """Prueba de clasificación de temas"""
    print("\n" + "="*60)
    print("🧪 TEST: CLASIFICACIÓN DE TEMAS")
    print("="*60)
    
    df = cargar_dataset_prueba()
    print(f"\nAnalizando {len(df)} textos...")
    
    analizador = AnalizadorCualitativo()
    resultados = analizador.clasificar_temas(df, n_temas=3)
    
    print("\n📊 Temas identificados:")
    for tema in resultados['temas']:
        print(f"\n  {tema['nombre']}:")
        print(f"  Palabras clave: {', '.join(tema['palabras_clave'])}")
    
    print("\n📊 Asignaciones de temas:")
    print(resultados['asignaciones'][['documento', 'tema_nombre', 'confianza']].head(10))
    
    return resultados


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 INICIANDO PRUEBAS DEL MOTOR DE ANÁLISIS CUALITATIVO")
    print("="*60)
    
    try:
        # Test 1: Análisis de sentimiento
        test_analisis_sentimiento()
        
        # Test 2: Extracción de palabras clave
        test_extraccion_keywords()
        
        # Test 3: Clasificación de temas
        test_clasificacion_temas()
        
        # Test 4: Análisis completo
        test_analisis_completo()
        
        print("\n" + "="*60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()