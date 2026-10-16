# motor_cuantitativo/analizador_cuantitativo.py
"""
Clase principal que orquesta todo el análisis cuantitativo.
"""

import os
import logging
import pandas as pd
from datetime import datetime

from .lector_datos import leer_csv_cuantitativo, convertir_a_numerico
from .estadisticas import (
    calcular_estadisticas_descriptivas,
    calcular_frecuencias,
    calcular_correlaciones,
    analizar_grupos,
    calcular_indice_satisfaccion,
    calcular_tabla_contingencia
)
from .visualizador import generar_todos_los_graficos
from .utils import guardar_excel_completo, guardar_json_resultados

logger = logging.getLogger(__name__)


class AnalizadorCuantitativo:
    """Motor de análisis cuantitativo para encuestas."""

    def __init__(self, directorio_resultados='data/resultados'):
        self.directorio_resultados = directorio_resultados
        os.makedirs(directorio_resultados, exist_ok=True)

    def analizar_completo(
        self,
        ruta_csv,
        generar_graficos=True,
        guardar_excel=True,
        guardar_json=True,
        n_grupos=None,
        incluir_html=True,
    ):
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO ANÁLISIS CUANTITATIVO")
        logger.info("=" * 60)

        # 1. LEER
        logger.info("\n📂 Leyendo CSV...")
        datos = leer_csv_cuantitativo(ruta_csv)
        metadata = datos['metadata']
        df_categorico = datos['df']
        logger.info(f"✅ {len(df_categorico)} encuestados")

        # 2. NUMÉRICO
        logger.info("\n🔢 Convirtiendo valores a numérico...")
        conversion = convertir_a_numerico(df_categorico, metadata)
        df_numerico = conversion['df_numerico']
        mapeos = conversion['mapeos']

        # 3. ESTADÍSTICAS
        logger.info("\n📊 Estadísticas...")
        estadisticas = calcular_estadisticas_descriptivas(df_numerico, metadata)
        frecuencias = calcular_frecuencias(df_categorico, metadata)
        correlaciones = calcular_correlaciones(df_numerico, metadata, metodo='spearman')
        grupos = analizar_grupos(df_numerico, df_categorico, metadata,
                                 pregunta_grupo_id=n_grupos)
        indice = calcular_indice_satisfaccion(df_numerico, metadata)

        preguntas_sino = [p for p in metadata['preguntas']
                          if p['tipo'] == 'seleccion_si_no']
        contingencia = None
        if len(preguntas_sino) >= 2:
            contingencia = calcular_tabla_contingencia(
                df_categorico, metadata,
                preguntas_sino[0]['id'],
                preguntas_sino[1]['id']
            )

        # 4. CONSOLIDAR
        resultados = {
            'metadata': metadata,
            'estadisticas_descriptivas': estadisticas,
            'frecuencias': frecuencias,
            'correlaciones': correlaciones,
            'grupos': grupos,
            'indice_satisfaccion': indice,
            'contingencia': contingencia,
            'df_categorico': df_categorico,
            'df_numerico': df_numerico,
            'mapeos': mapeos
        }

        # 5. GRÁFICOS
        archivos_generados = {}
        preguntas_omitidas = []

        if generar_graficos:
            directorio_graficos = os.path.join(self.directorio_resultados, 'graficos')
            salida = generar_todos_los_graficos(
                metadata=metadata,
                df_numerico=df_numerico,
                df_categorico=df_categorico,
                frecuencias_df=frecuencias,
                correlaciones_result=correlaciones,
                grupos_result=grupos,
                indice_result=indice,
                directorio=directorio_graficos,
                incluir_html=incluir_html,
            )
            archivos_generados['graficos'] = salida['graficos']
            preguntas_omitidas = salida['omitidos']
            resultados['preguntas_sin_datos'] = preguntas_omitidas

        # 6. EXCEL
        if guardar_excel:
            logger.info("\n💾 Guardando Excel...")
            resultados_excel = {
                'estadisticas_descriptivas': estadisticas,
                'frecuencias': frecuencias,
                'correlaciones': correlaciones,
                'grupos': grupos,
                'indice_satisfaccion': indice,
                'df_categorico': df_categorico,
            }
            ruta_excel = guardar_excel_completo(resultados_excel, metadata,
                                                 self.directorio_resultados)
            archivos_generados['excel'] = ruta_excel

        # 7. JSON
        if guardar_json:
            logger.info("💾 Guardando JSON...")
            resultados_json = {
                'estadisticas_descriptivas': estadisticas,
                'frecuencias': frecuencias,
                'correlaciones': correlaciones,
                'grupos': grupos,
                'indice_satisfaccion': indice,
                'contingencia': contingencia,
                'preguntas_sin_datos': preguntas_omitidas,
            }
            ruta_json = guardar_json_resultados(resultados_json, metadata,
                                                 self.directorio_resultados)
            archivos_generados['json'] = ruta_json

        self._mostrar_resumen(resultados)

        resultados['archivos'] = archivos_generados
        return resultados

    def _mostrar_resumen(self, resultados):
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN DEL ANÁLISIS")
        logger.info("=" * 60)

        meta = resultados['metadata']
        logger.info(f"\n📋 Encuesta: {meta['titulo']}")
        logger.info(f"👥 Encuestados: {meta['total_encuestados']}")
        logger.info(f"❓ Preguntas: {len(meta['preguntas'])}")

        omitidas = resultados.get('preguntas_sin_datos', [])
        if omitidas:
            logger.info(f"⏭️  Preguntas sin datos (omitidas): {omitidas}")

        est = resultados['estadisticas_descriptivas']
        if not est.empty:
            logger.info("\n📊 Estadísticas descriptivas:")
            for _, row in est.iterrows():
                if pd.notna(row.get('Media')):
                    logger.info(f"   • {row['Pregunta'][:50]}")
                    logger.info(f"     Media: {row['Media']} | Desv: {row['Desv_Est']}")

        corr = resultados['correlaciones']
        if corr.get('pares_significativos') is not None and not corr['pares_significativos'].empty:
            logger.info(f"\n🔗 Correlaciones: {len(corr['pares_significativos'])}")

        indice = resultados['indice_satisfaccion']
        if indice.get('indice_global') is not None:
            logger.info(f"\n⭐ Índice de satisfacción: {indice['indice_global']}/100")

        logger.info("\n" + "=" * 60)
        logger.info("✅ ANÁLISIS COMPLETADO")
        logger.info("=" * 60)