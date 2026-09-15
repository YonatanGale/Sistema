# motor_cualitativo/runner.py
"""
Script de línea de comandos para ejecutar el motor cualitativo
sobre un archivo CSV generado por el sistema de encuestas.

Uso:
    python runner.py <ruta_csv> [--temas N] [--keywords N]

Ejemplo:
    python runner.py ../exports/cualitativo_1_20260915.csv --temas 3 --keywords 15
"""
import sys
import os
import argparse

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lector_csv import leer_csv_encuestas, leer_csv_agrupado_por_pregunta
from analizador import AnalizadorCualitativo
from utils import guardar_resultados


def mostrar_banner():
    """Muestra el banner del runner"""
    print("\n" + "=" * 65)
    print("  🧠 MOTOR DE ANÁLISIS CUALITATIVO - RUNNER")
    print("  Análisis de respuestas desde CSV (sin conexión a BD)")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description='Ejecuta el motor cualitativo sobre un CSV de encuestas.'
    )
    parser.add_argument(
        'ruta_csv',
        help='Ruta al archivo CSV generado por el sistema de encuestas'
    )
    parser.add_argument(
        '--temas', '-t',
        type=int,
        default=3,
        help='Número de temas a identificar (default: 3)'
    )
    parser.add_argument(
        '--keywords', '-k',
        type=int,
        default=15,
        help='Número de palabras clave (default: 15)'
    )
    parser.add_argument(
        '--salida', '-s',
        default='data/resultados',
        help='Directorio de salida (default: data/resultados)'
    )
    parser.add_argument(
        '--agrupado', '-a',
        action='store_true',
        help='Analizar agrupado por pregunta (un análisis por pregunta)'
    )
    
    args = parser.parse_args()
    
    mostrar_banner()
    
    # Validar archivo
    if not os.path.exists(args.ruta_csv):
        print(f"\n❌ ERROR: No se encontró el archivo: {args.ruta_csv}")
        sys.exit(1)
    
    print(f"\n📂 Archivo CSV: {args.ruta_csv}")
    print(f"⚙️  Configuración:")
    print(f"   - Temas: {args.temas}")
    print(f"   - Palabras clave: {args.keywords}")
    print(f"   - Directorio salida: {args.salida}")
    print(f"   - Modo: {'Agrupado por pregunta' if args.agrupado else 'Análisis global'}")
    
    try:
        if args.agrupado:
            # Análisis agrupado por pregunta
            ejecutar_agrupado(args)
        else:
            # Análisis global
            ejecutar_global(args)
            
    except Exception as e:
        print(f"\n❌ ERROR durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def ejecutar_global(args):
    """Análisis global (todas las respuestas juntas)"""
    print("\n" + "-" * 65)
    print("🚀 INICIANDO ANÁLISIS GLOBAL")
    print("-" * 65)
    
    # 1. Leer CSV
    print("\n📖 Leyendo CSV...")
    df = leer_csv_encuestas(args.ruta_csv)
    print(f"   ✅ {len(df)} respuestas cargadas")
    
    if df.empty:
        print("   ⚠️ No hay respuestas para analizar")
        return
    
    # 2. Analizar
    print("\n🧠 Analizando...")
    analizador = AnalizadorCualitativo()
    resultados = analizador.analizar_completo(
        df,
        n_temas=args.temas,
        n_keywords=args.keywords
    )
    
    # 3. Mostrar resultados
    mostrar_resultados(resultados)
    
    # 4. Guardar Excel
    print("\n💾 Guardando resultados...")
    nombre_base = os.path.splitext(os.path.basename(args.ruta_csv))[0]
    ruta_excel = guardar_resultados(
        resultados,
        nombre_base=f"analisis_{nombre_base}",
        formato='excel',
        directorio=args.salida
    )
    print(f"   ✅ Excel guardado en: {ruta_excel}")
    
    print("\n" + "=" * 65)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 65)


def ejecutar_agrupado(args):
    """Análisis agrupado por pregunta"""
    print("\n" + "-" * 65)
    print("🚀 INICIANDO ANÁLISIS AGRUPADO POR PREGUNTA")
    print("-" * 65)
    
    # 1. Leer y agrupar
    print("\n📖 Leyendo y agrupando por pregunta...")
    grupos = leer_csv_agrupado_por_pregunta(args.ruta_csv)
    print(f"   ✅ {len(grupos)} preguntas encontradas")
    
    if not grupos:
        print("   ⚠️ No hay preguntas para analizar")
        return
    
    analizador = AnalizadorCualitativo()
    resultados_totales = {}
    
    # 2. Analizar cada grupo
    for pregunta_id, grupo in grupos.items():
        print(f"\n{'─' * 65}")
        print(f"📌 PREGUNTA: {grupo['pregunta'][:60]}...")
        print(f"   Respuestas: {len(grupo['respuestas'])}")
        
        # Crear DataFrame solo con este grupo
        df_grupo = grupo['df'][['texto']]
        
        # Analizar
        resultados = analizador.analizar_completo(
            df_grupo,
            n_temas=min(args.temas, max(2, len(df_grupo) // 5)),
            n_keywords=args.keywords
        )
        
        resultados_totales[pregunta_id] = {
            'pregunta': grupo['pregunta'],
            'resultados': resultados
        }
        
        # Mostrar resumen de esta pregunta
        print(f"   Sentimientos: {resultados['resumen']['distribucion_sentimiento']}")
        if not resultados['palabras_clave'].empty:
            top_kw = resultados['palabras_clave']['palabra'].head(5).tolist()
            print(f"   Top palabras: {', '.join(top_kw)}")
    
    # 3. Guardar Excel con todas las hojas
    print(f"\n💾 Guardando resultados...")
    nombre_base = os.path.splitext(os.path.basename(args.ruta_csv))[0]
    ruta_excel = guardar_resultados_agrupados(
        resultados_totales,
        nombre_base=f"analisis_agrupado_{nombre_base}",
        directorio=args.salida
    )
    print(f"   ✅ Excel guardado en: {ruta_excel}")
    
    print("\n" + "=" * 65)
    print("✅ ANÁLISIS AGRUPADO COMPLETADO")
    print("=" * 65)


def mostrar_resultados(resultados):
    """Muestra los resultados del análisis"""
    print("\n" + "-" * 65)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("-" * 65)
    
    # Sentimiento
    print("\n1️⃣ DISTRIBUCIÓN DE SENTIMIENTO:")
    dist = resultados['resumen']['distribucion_sentimiento']
    total = sum(dist.values())
    for sent, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total > 0 else 0
        barra = '█' * int(pct / 5)
        print(f"   {sent:<15} {count:>3} ({pct:>5.1f}%) {barra}")
    
    # Palabras clave
    print("\n2️⃣ TOP PALABRAS CLAVE:")
    if not resultados['palabras_clave'].empty:
        for i, row in resultados['palabras_clave'].head(10).iterrows():
            print(f"   {i+1:>2}. {row['palabra']:<20} (score: {row['tfidf_score']:.4f})")
    else:
        print("   ⚠️ No se encontraron palabras clave")
    
    # Temas
    print("\n3️⃣ TEMAS IDENTIFICADOS:")
    for tema in resultados['temas']['temas']:
        palabras = ', '.join(tema['palabras_clave'][:7])
        print(f"\n   🔹 {tema['nombre']}:")
        print(f"      {palabras}")
    
    # Resumen
    print("\n4️⃣ RESUMEN:")
    print(f"   Total textos: {resultados['resumen']['total_textos']}")
    print(f"   Sentimiento predominante: {resultados['resumen']['sentimiento_predominante']}")


def guardar_resultados_agrupados(resultados_totales, nombre_base, directorio='data/resultados'):
    """Guarda los resultados agrupados en un Excel con múltiples hojas"""
    import pandas as pd
    from datetime import datetime
    
    os.makedirs(directorio, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta = os.path.join(directorio, f"{nombre_base}_{timestamp}.xlsx")
    
    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja resumen
        resumen_data = []
        for pregunta_id, datos in resultados_totales.items():
            r = datos['resultados']
            resumen_data.append({
                'id_pregunta': pregunta_id,
                'pregunta': datos['pregunta'],
                'total_respuestas': r['resumen']['total_textos'],
                'sentimiento_predominante': r['resumen']['sentimiento_predominante'],
                'muy_positivo': r['resumen']['distribucion_sentimiento'].get('Muy Positivo', 0),
                'positivo': r['resumen']['distribucion_sentimiento'].get('Positivo', 0),
                'neutral': r['resumen']['distribucion_sentimiento'].get('Neutral', 0),
                'negativo': r['resumen']['distribucion_sentimiento'].get('Negativo', 0),
                'muy_negativo': r['resumen']['distribucion_sentimiento'].get('Muy Negativo', 0),
            })
        
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)
        
        # Una hoja por pregunta
        for pregunta_id, datos in resultados_totales.items():
            nombre_hoja = f"P{pregunta_id}"[:31]
            df = datos['resultados']['resultados']
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    
    return ruta


if __name__ == '__main__':
    main()