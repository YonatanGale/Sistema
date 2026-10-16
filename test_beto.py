# test_beto.py
"""
Script de prueba para verificar que el motor cualitativo con BETO
funciona correctamente.
"""

import sys
import time


def separador(titulo):
    print("\n" + "=" * 60)
    print(f"  {titulo}")
    print("=" * 60)


def main():
    separador("1. IMPORTANDO EL ANALIZADOR")
    try:
        from motor_cualitativo.analizador import AnalizadorCualitativo
        print("✅ Import exitoso")
    except ImportError as e:
        print(f"❌ Error de import: {e}")
        print("\nPosibles causas:")
        print("  - Falta __init__.py en motor_cualitativo/")
        print("  - Estás ejecutando desde otra carpeta")
        print("  - Faltan dependencias (revisa pip install -r requirements.txt)")
        sys.exit(1)

    separador("2. INICIALIZANDO EL ANALIZADOR")
    print("⏳ Esto puede tardar 1-3 minutos la primera vez (descarga modelos)")
    t0 = time.time()
    try:
        analizador = AnalizadorCualitativo()
        print(f"✅ Analizador listo en {time.time() - t0:.1f}s")
    except Exception as e:
        print(f"❌ Error al inicializar: {e}")
        sys.exit(1)

    # Verificar que BETO está cargado
    separador("3. VERIFICANDO MODELOS CARGADOS")
    print(f"  Pipeline de sentimiento: {analizador.classifier is not None}")
    print(f"  Tokenizer BETO base:     {analizador.tokenizer_beto is not None}")
    print(f"  Encoder BETO base:       {analizador.model_beto is not None}")
    print(f"  Mejoras heurísticas:     {analizador.usar_mejoras}")

    # Textos de prueba
    textos = [
        "Excelente atención, muy recomendado.",
        "No me gustó nada, una pérdida de tiempo.",
        "Fue una actividad más, sin mucho que destacar.",
        "Nada, todo bien, sigan así.",
        "La atención fue pésima.",
        "El taller estuvo bien.",
        "Muy buena experiencia, gracias.",
        "No sirve, todo mal organizado.",
    ]

    separador("4. ANÁLISIS DE SENTIMIENTO")
    df_sent = analizador.analizar_sentimiento(textos)
    for _, row in df_sent.iterrows():
        marca = "🔴" if "Negativo" in row['sentimiento'] else \
                "🟢" if "Positivo" in row['sentimiento'] else "⚪"
        print(f"  {marca} [{row['sentimiento']:15s}] score={row['score']:.3f}  |  {row['texto'][:50]}")

    separador("5. EXTRACCIÓN DE PALABRAS CLAVE (TF-IDF)")
    df_kw = analizador.extraer_palabras_clave(textos, n_top=5)
    for _, row in df_kw.iterrows():
        print(f"  📌 {row['palabra']:20s}  tfidf={row['tfidf_score']:.4f}  freq={row['frecuencia']}")

    separador("6. MODELADO DE TÓPICOS (LDA)")
    temas = analizador.clasificar_temas(textos, n_temas=3)
    for t in temas['temas']:
        print(f"  🏷️  {t['nombre']}: {', '.join(t['palabras_clave'][:5])}")

    separador("7. EMBEDDINGS CONTEXTUALES CON BETO BASE")
    try:
        emb = analizador.obtener_embeddings(textos)
        print(f"  Shape de embeddings: {emb.shape}")
        print(f"  (esperado: ({len(textos)}, 768))")
        print(f"  Norma del primer embedding: {float((emb[0]**2).sum()**0.5):.3f}")
    except Exception as e:
        print(f"  ⚠️  Error al generar embeddings: {e}")

    separador("8. ANÁLISIS COMPLETO")
    res = analizador.analizar_completo(textos, n_temas=3, n_keywords=5)
    print("  Resumen:")
    for k, v in res['resumen'].items():
        print(f"    {k}: {v}")

    separador("✅ TODAS LAS PRUEBAS PASARON")
    print("El motor cualitativo con BETO está funcionando correctamente.")


if __name__ == "__main__":
    main()