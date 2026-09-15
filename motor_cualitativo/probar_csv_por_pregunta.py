# motor_cualitativo/probar_csv_por_pregunta.py
import os
import pandas as pd
from analizador import AnalizadorCualitativo
from utils import guardar_resultados

# ============================================
# RUTA DEL ARCHIVO
# ============================================
RUTA_CSV = "data/pruebas/cualitativo_1_Encuesta_de_Satisfaccion_Gener_20260915_154326.csv"

if not os.path.exists(RUTA_CSV):
    RUTA_CSV = os.path.join(
        os.path.expanduser("~"), "Downloads",
        "cualitativo_1_Encuesta_de_Satisfaccion_Gener_20260915_154326.csv"
    )

print("=" * 60)
print("🔍 ANÁLISIS POR PREGUNTA")
print("=" * 60)
print(f"\n📂 Archivo: {RUTA_CSV}\n")

df = pd.read_csv(RUTA_CSV, encoding='utf-8-sig')
print(f"✅ {len(df)} filas cargadas")
print(f"📊 Columnas: {list(df.columns)}\n")

# ============================================
# INICIALIZAR ANALIZADOR
# ============================================
analizador = AnalizadorCualitativo()

# ============================================
# ANALIZAR CADA PREGUNTA POR SEPARADO
# ============================================
resultados_totales = {}

for columna in df.columns:
    if columna == 'Identificador':
        continue
    
    # Obtener respuestas no vacías
    textos = df[columna].dropna().astype(str).tolist()
    textos = [t.strip() for t in textos if t.strip() != '']
    
    if not textos:
        print(f"⚠️ '{columna}': Sin respuestas")
        continue
    
    print(f"\n{'='*60}")
    print(f"📋 PREGUNTA: {columna}")
    print(f"{'='*60}")
    print(f"📊 Total respuestas: {len(textos)}")
    
    # Analizar
    df_pregunta = pd.DataFrame({'texto': textos})
    resultados = analizador.analizar_completo(df_pregunta, n_temas=2, n_keywords=8)
    
    # Guardar resultados
    resultados_totales[columna] = resultados
    
    # ============================================
    # MOSTRAR SENTIMIENTO
    # ============================================
    print(f"\n📊 Distribución de sentimiento:")
    for sent, count in resultados['resumen']['distribucion_sentimiento'].items():
        porcentaje = (count / len(textos)) * 100
        print(f"   {sent}: {count} ({porcentaje:.1f}%)")
    
    # ============================================
    # MOSTRAR PALABRAS CLAVE
    # ============================================
    if not resultados['palabras_clave'].empty:
        print(f"\n📊 Palabras clave:")
        print(resultados['palabras_clave'][['palabra', 'tfidf_score', 'frecuencia']].head(5).to_string(index=False))
    
    # ============================================
    # MOSTRAR TEMAS
    # ============================================
    print(f"\n📊 Temas identificados:")
    for tema in resultados['temas']['temas']:
        print(f"   {tema['nombre']}: {', '.join(tema['palabras_clave'][:5])}")
    
    # ============================================
    # MOSTRAR RESULTADOS POR TEXTO
    # ============================================
    print(f"\n📊 Primeros 5 resultados:")
    print(resultados['resultados'][['texto', 'sentimiento']].head(5).to_string(index=False))

# ============================================
# GUARDAR TODOS LOS RESULTADOS
# ============================================
print("\n" + "=" * 60)
print("💾 Guardando resultados...")
print("=" * 60)

# Guardar cada pregunta en una hoja diferente del Excel
from io import BytesIO
from datetime import datetime

output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    for i, (nombre_pregunta, res) in enumerate(resultados_totales.items()):
        # Hoja de resumen
        nombre_hoja = f"P{i+1}_resumen"[:31]
        resumen_df = pd.DataFrame([{
            'Pregunta': nombre_pregunta,
            'Total_respuestas': res['resumen']['total_textos'],
            'Sentimiento_predominante': res['resumen']['sentimiento_predominante'],
            **{f'Sent_{k}': v for k, v in res['resumen']['distribucion_sentimiento'].items()}
        }])
        resumen_df.to_excel(writer, sheet_name=nombre_hoja, index=False)
        
        # Hoja de resultados individuales
        nombre_hoja2 = f"P{i+1}_resultados"[:31]
        res['resultados'][['texto', 'sentimiento', 'tema']].to_excel(
            writer, sheet_name=nombre_hoja2, index=False
        )

# Guardar en carpeta de resultados
ruta_salida = os.path.join(
    'data', 'resultados',
    f"analisis_por_pregunta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
)
os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

with open(ruta_salida, 'wb') as f:
    f.write(output.getvalue())

print(f"\n✅ Resultados guardados en: {ruta_salida}")

print("\n" + "=" * 60)
print("✅ ANÁLISIS COMPLETADO")
print("=" * 60)