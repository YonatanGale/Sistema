# comparar_con_contexto.py
"""
Script para comparar el análisis de sentimiento y palabras clave
con y sin contexto de la pregunta.
"""
from analizador import AnalizadorCualitativo
import pandas as pd
import numpy as np

# ============================================================
# DATOS DE PRUEBA: RESPUESTAS A UNA MISMA PREGUNTA
# ============================================================
# Pregunta: "¿Qué aspectos mejorarías del servicio pastoral?"
# ============================================================

PREGUNTA = "¿Qué aspectos mejorarías del servicio pastoral?"

RESPUESTAS = [
    "Mejorar la comunicación con los feligreses, a veces no nos enteramos de las actividades.",
    "Falta más transparencia en el manejo de las finanzas de la parroquia.",
    "Los horarios de misa deberían ser más flexibles para los trabajadores.",
    "Necesitamos más actividades para los jóvenes de la comunidad.",
    "La infraestructura de la iglesia necesita mejoras urgentes.",
    "Excelente todo, no cambiaría nada del servicio actual.",
    "Mejorar la atención a los enfermos y ancianos de la comunidad.",
    "El párroco debería estar más disponible para escuchar a los feligreses.",
    "Falta organización en las actividades de la comunidad.",
    "La música durante las misas podría ser más variada.",
    "No me gusta cómo se manejan las actividades para niños.",
    "Todo está muy bien, el servicio es excelente.",
    "Mejorar la catequesis para los niños, falta preparación.",
    "Los grupos de oración necesitan más apoyo del párroco.",
    "Deberían hacer más retiros espirituales durante el año.",
    "La parroquia necesita más espacios de encuentro para la comunidad.",
    "Falta difusión de las actividades en las redes sociales.",
    "El servicio de atención a los jóvenes es muy bueno, pero necesita más voluntarios.",
    "Mejorar la predicación del párroco, a veces es muy larga.",
    "Todo funciona bien, la comunidad es muy unida.",
]

# ============================================================
# FUNCIÓN AUXILIAR PARA MOSTRAR RESULTADOS
# ============================================================

def mostrar_resultados(resultados, titulo):
    """Muestra los resultados del análisis de forma formateada"""
    print(f"\n{'=' * 60}")
    print(f"📊 {titulo}")
    print(f"{'=' * 60}")
    
    # Sentimiento
    print("\n1️⃣ DISTRIBUCIÓN DE SENTIMIENTO:")
    distribucion = resultados['resumen']['distribucion_sentimiento']
    total = sum(distribucion.values())
    for sentimiento, count in distribucion.items():
        porcentaje = (count / total * 100) if total > 0 else 0
        print(f"   {sentimiento}: {count} ({porcentaje:.1f}%)")
    
    # Palabras clave
    print("\n2️⃣ TOP 10 PALABRAS CLAVE (TF-IDF):")
    if not resultados['palabras_clave'].empty:
        df_kw = resultados['palabras_clave'][['palabra', 'tfidf_score', 'frecuencia']].head(10)
        print(df_kw.to_string(index=False))
    else:
        print("   ⚠️ No se encontraron palabras clave")
    
    # Temas
    print("\n3️⃣ TEMAS IDENTIFICADOS:")
    for tema in resultados['temas']['temas']:
        palabras = ', '.join(tema['palabras_clave'][:7])
        print(f"\n   {tema['nombre']}:")
        print(f"      Palabras: {palabras}")
    
    # Resumen
    print(f"\n4️⃣ RESUMEN:")
    print(f"   Total textos: {resultados['resumen']['total_textos']}")
    print(f"   Sentimiento predominante: {resultados['resumen']['sentimiento_predominante']}")


def comparar_resultados(res_sin, res_con):
    """Compara los resultados con y sin contexto"""
    print(f"\n{'=' * 60}")
    print("🔍 COMPARACIÓN: SIN CONTEXTO vs CON CONTEXTO")
    print(f"{'=' * 60}")
    
    # Comparar sentimiento
    print("\n📊 SENTIMIENTO:")
    sent_sin = res_sin['resumen']['distribucion_sentimiento']
    sent_con = res_con['resumen']['distribucion_sentimiento']
    
    todos_sentimientos = set(sent_sin.keys()) | set(sent_con.keys())
    print(f"\n   {'Sentimiento':<20} {'Sin Contexto':<15} {'Con Contexto':<15} {'Diferencia':<10}")
    print(f"   {'-'*60}")
    for sent in sorted(todos_sentimientos):
        c_sin = sent_sin.get(sent, 0)
        c_con = sent_con.get(sent, 0)
        diff = c_con - c_sin
        signo = "+" if diff > 0 else ""
        print(f"   {sent:<20} {c_sin:<15} {c_con:<15} {signo}{diff:<10}")
    
    # Comparar palabras clave
    print("\n📊 PALABRAS CLAVE (comparación):")
    kw_sin = set(res_sin['palabras_clave']['palabra'].head(10).tolist()) if not res_sin['palabras_clave'].empty else set()
    kw_con = set(res_con['palabras_clave']['palabra'].head(10).tolist()) if not res_con['palabras_clave'].empty else set()
    
    solo_sin = kw_sin - kw_con
    solo_con = kw_con - kw_sin
    comunes = kw_sin & kw_con
    
    print(f"\n   ✅ Comunes ({len(comunes)}): {', '.join(sorted(comunes))}")
    print(f"   🔵 Solo sin contexto ({len(solo_sin)}): {', '.join(sorted(solo_sin))}")
    print(f"   🟢 Solo con contexto ({len(solo_con)}): {', '.join(sorted(solo_con))}")
    
    # Comparar temas
    print("\n📊 TEMAS:")
    temas_sin = res_sin['temas']['temas']
    temas_con = res_con['temas']['temas']
    
    print(f"\n   Sin contexto ({len(temas_sin)} temas):")
    for tema in temas_sin:
        print(f"      {tema['nombre']}: {', '.join(tema['palabras_clave'][:5])}")
    
    print(f"\n   Con contexto ({len(temas_con)} temas):")
    for tema in temas_con:
        print(f"      {tema['nombre']}: {', '.join(tema['palabras_clave'][:5])}")


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 COMPARACIÓN: ANÁLISIS CON Y SIN CONTEXTO")
    print("=" * 60)
    print(f"\n📌 Pregunta analizada: {PREGUNTA}")
    print(f"📊 Total de respuestas: {len(RESPUESTAS)}")
    
    # --------------------------------------------------------
    # PREPARAR DATOS
    # --------------------------------------------------------
    # Dataset 1: Solo respuestas
    df_sin_contexto = pd.DataFrame({'texto': RESPUESTAS})
    
    # Dataset 2: Pregunta + Respuesta
    textos_con_contexto = [
        f"Pregunta: {PREGUNTA} Respuesta: {r}" 
        for r in RESPUESTAS
    ]
    df_con_contexto = pd.DataFrame({'texto': textos_con_contexto})
    
    # --------------------------------------------------------
    # INICIALIZAR ANALIZADOR
    # --------------------------------------------------------
    print("\n🤖 Inicializando Analizador Cualitativo...")
    analizador = AnalizadorCualitativo()
    
    # --------------------------------------------------------
    # ANÁLISIS 1: SIN CONTEXTO
    # --------------------------------------------------------
    print("\n" + "🔵 " + "=" * 56)
    print("🔵 ANÁLISIS SIN CONTEXTO (solo respuestas)")
    print("🔵 " + "=" * 56)
    
    resultados_sin = analizador.analizar_completo(
        df_sin_contexto, 
        n_temas=3, 
        n_keywords=10
    )
    mostrar_resultados(resultados_sin, "RESULTADOS SIN CONTEXTO")
    
    # --------------------------------------------------------
    # ANÁLISIS 2: CON CONTEXTO
    # --------------------------------------------------------
    print("\n" + "🟢 " + "=" * 56)
    print("🟢 ANÁLISIS CON CONTEXTO (pregunta + respuesta)")
    print("🟢 " + "=" * 56)
    
    resultados_con = analizador.analizar_completo(
        df_con_contexto, 
        n_temas=3, 
        n_keywords=10
    )
    mostrar_resultados(resultados_con, "RESULTADOS CON CONTEXTO")
    
    # --------------------------------------------------------
    # COMPARACIÓN
    # --------------------------------------------------------
    comparar_resultados(resultados_sin, resultados_con)
    
    # --------------------------------------------------------
    # GUARDAR RESULTADOS
    # --------------------------------------------------------
    print("\n💾 Guardando resultados...")
    from utils import guardar_resultados
    
    # Combinar ambos resultados en un solo Excel
    import os
    from datetime import datetime
    from io import BytesIO
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ruta_excel = f"data/resultados/comparacion_contexto_{timestamp}.xlsx"
    os.makedirs("data/resultados", exist_ok=True)
    
    with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
        # Hoja 1: Comparación de sentimientos
        sent_sin = resultados_sin['resumen']['distribucion_sentimiento']
        sent_con = resultados_con['resumen']['distribucion_sentimiento']
        todos_sent = set(sent_sin.keys()) | set(sent_con.keys())
        
        comparacion_sent = pd.DataFrame({
            'Sentimiento': sorted(todos_sent),
            'Sin_Contexto': [sent_sin.get(s, 0) for s in sorted(todos_sent)],
            'Con_Contexto': [sent_con.get(s, 0) for s in sorted(todos_sent)],
        })
        comparacion_sent.to_excel(writer, sheet_name='Comparacion_Sentimiento', index=False)
        
        # Hoja 2: Palabras clave sin contexto
        if not resultados_sin['palabras_clave'].empty:
            resultados_sin['palabras_clave'].to_excel(
                writer, sheet_name='KW_Sin_Contexto', index=False
            )
        
        # Hoja 3: Palabras clave con contexto
        if not resultados_con['palabras_clave'].empty:
            resultados_con['palabras_clave'].to_excel(
                writer, sheet_name='KW_Con_Contexto', index=False
            )
        
        # Hoja 4: Resultados completos sin contexto
        resultados_sin['resultados'].to_excel(
            writer, sheet_name='Resultados_Sin_Contexto', index=False
        )
        
        # Hoja 5: Resultados completos con contexto
        resultados_con['resultados'].to_excel(
            writer, sheet_name='Resultados_Con_Contexto', index=False
        )
        
        # Hoja 6: Temas sin contexto
        temas_sin_df = pd.DataFrame([
            {
                'Tema': t['nombre'],
                'Palabras_Clave': ', '.join(t['palabras_clave'])
            }
            for t in resultados_sin['temas']['temas']
        ])
        temas_sin_df.to_excel(writer, sheet_name='Temas_Sin_Contexto', index=False)
        
        # Hoja 7: Temas con contexto
        temas_con_df = pd.DataFrame([
            {
                'Tema': t['nombre'],
                'Palabras_Clave': ', '.join(t['palabras_clave'])
            }
            for t in resultados_con['temas']['temas']
        ])
        temas_con_df.to_excel(writer, sheet_name='Temas_Con_Contexto', index=False)
    
    print(f"✅ Resultados guardados en: {ruta_excel}")
    
    print("\n" + "=" * 60)
    print("✅ COMPARACIÓN COMPLETADA")
    print("=" * 60)
    print("\n💡 CONCLUSIÓN:")
    print("   Revisa las diferencias en sentimiento, palabras clave y temas")
    print("   para determinar si el contexto de la pregunta mejora el análisis.")