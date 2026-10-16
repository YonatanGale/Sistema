# motor_cuantitativo/utils.py
"""
Helpers para guardar resultados del motor cuantitativo.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def convertir_a_serializable(obj):
    """Convierte objetos numpy/pandas a tipos serializables para JSON."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if pd.isna(obj):
        return None
    return obj


def guardar_excel_completo(resultados, metadata, directorio='data/resultados'):
    """
    Guarda un Excel con múltiples hojas con todos los resultados del análisis.
    
    Args:
        resultados: dict con todos los resultados
        metadata: metadata de la encuesta
        directorio: dónde guardar
    
    Returns:
        ruta del archivo Excel
    """
    os.makedirs(directorio, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_base = metadata.get('titulo', 'encuesta')[:30]
    nombre_base = ''.join(c if c.isalnum() or c in '_-' else '_' for c in nombre_base)
    
    ruta = os.path.join(directorio, f"analisis_cuantitativo_{nombre_base}_{timestamp}.xlsx")
    
    with pd.ExcelWriter(ruta, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        formato_titulo = workbook.add_format({
            'bold': True, 'bg_color': '#1a1a2e', 'font_color': 'white', 'font_size': 12
        })
        formato_header = workbook.add_format({
            'bold': True, 'bg_color': '#3498db', 'font_color': 'white', 'border': 1
        })
        formato_numero = workbook.add_format({'num_format': '0.00'})
        
        # ============================================
        # HOJA 1: RESUMEN
        # ============================================
        resumen_data = {
            'Encuesta': [metadata.get('titulo', '')],
            'Descripción': [metadata.get('descripcion', '')],
            'Fecha de análisis': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Total encuestados': [metadata.get('total_encuestados', 0)],
            'Preguntas cuantitativas': [len(metadata.get('preguntas', []))],
        }
        
        if resultados.get('indice_satisfaccion', {}).get('indice_global') is not None:
            resumen_data['Índice de satisfacción global (0-100)'] = [
                resultados['indice_satisfaccion']['indice_global']
            ]
        
        df_resumen = pd.DataFrame(resumen_data).T
        df_resumen.columns = ['Valor']
        df_resumen.to_excel(writer, sheet_name='Resumen', startrow=1)
        
        hoja_resumen = writer.sheets['Resumen']
        hoja_resumen.write(0, 0, 'RESUMEN DEL ANÁLISIS', formato_titulo)
        hoja_resumen.set_column('A:A', 35)
        hoja_resumen.set_column('B:B', 50)
        
        # ============================================
        # HOJA 2: ESTADÍSTICAS DESCRIPTIVAS
        # ============================================
        if 'estadisticas_descriptivas' in resultados:
            df = resultados['estadisticas_descriptivas']
            if not df.empty:
                df.to_excel(writer, sheet_name='Estadísticas', startrow=1, index=False)
                hoja = writer.sheets['Estadísticas']
                hoja.write(0, 0, 'ESTADÍSTICAS DESCRIPTIVAS', formato_titulo)
                for col_num, col_name in enumerate(df.columns):
                    hoja.write(1, col_num, col_name, formato_header)
                hoja.set_column(0, len(df.columns) - 1, 18)
        
        # ============================================
        # HOJA 3: FRECUENCIAS POR OPCIÓN
        # ============================================
        if 'frecuencias' in resultados:
            df = resultados['frecuencias']
            if not df.empty:
                df.to_excel(writer, sheet_name='Frecuencias', startrow=1, index=False)
                hoja = writer.sheets['Frecuencias']
                hoja.write(0, 0, 'FRECUENCIAS POR OPCIÓN', formato_titulo)
                for col_num, col_name in enumerate(df.columns):
                    hoja.write(1, col_num, col_name, formato_header)
                hoja.set_column(0, len(df.columns) - 1, 20)
        
        # ============================================
        # HOJA 4: CORRELACIONES
        # ============================================
        if 'correlaciones' in resultados:
            corr = resultados['correlaciones']
            
            # Matriz
            if not corr.get('matriz', pd.DataFrame()).empty:
                corr['matriz'].to_excel(writer, sheet_name='Correlaciones', startrow=2)
                hoja = writer.sheets['Correlaciones']
                hoja.write(0, 0, 'MATRIZ DE CORRELACIONES (Spearman)', formato_titulo)
            
            # Pares significativos
            if not corr.get('pares_significativos', pd.DataFrame()).empty:
                start_row = len(corr['matriz']) + 5
                corr['pares_significativos'].to_excel(
                    writer, sheet_name='Correlaciones', startrow=start_row, index=False
                )
                hoja = writer.sheets['Correlaciones']
                hoja.write(start_row - 1, 0, 'PARES CON CORRELACIÓN SIGNIFICATIVA (|r| ≥ 0.3)', formato_titulo)
        
        # ============================================
        # HOJA 5: ANÁLISIS POR GRUPOS
        # ============================================
        if 'grupos' in resultados:
            grupos = resultados['grupos']
            if not grupos.get('resumen', pd.DataFrame()).empty:
                grupos['resumen'].to_excel(writer, sheet_name='Grupos', startrow=1, index=False)
                hoja = writer.sheets['Grupos']
                hoja.write(0, 0, f"ANÁLISIS POR GRUPOS: {grupos.get('grupo_pregunta', '')[:80]}", formato_titulo)
                hoja.set_column(0, len(grupos['resumen'].columns) - 1, 20)
        
        # ============================================
        # HOJA 6: ÍNDICE DE SATISFACCIÓN
        # ============================================
        if 'indice_satisfaccion' in resultados:
            indice = resultados['indice_satisfaccion']
            
            if not indice.get('por_pregunta', pd.DataFrame()).empty:
                indice['por_pregunta'].to_excel(writer, sheet_name='Satisfacción', startrow=2, index=False)
                hoja = writer.sheets['Satisfacción']
                hoja.write(0, 0, 'ÍNDICE DE SATISFACCIÓN POR PREGUNTA', formato_titulo)
                hoja.write(1, 0, f"Índice global: {indice['indice_global']}/100", formato_header)
                hoja.set_column(0, len(indice['por_pregunta'].columns) - 1, 25)
        
        # ============================================
        # HOJA 7: DATOS ORIGINALES
        # ============================================
        if 'df_categorico' in resultados:
            df = resultados['df_categorico']
            if not df.empty:
                df.to_excel(writer, sheet_name='Datos_originales', startrow=1, index=False)
                hoja = writer.sheets['Datos_originales']
                hoja.write(0, 0, 'DATOS ORIGINALES', formato_titulo)
                hoja.set_column(0, len(df.columns) - 1, 18)
    
    logger.info(f"✅ Excel guardado: {ruta}")
    return ruta


def guardar_json_resultados(resultados, metadata, directorio='data/resultados'):
    """
    Guarda los resultados en JSON (útil para el dashboard HTML).
    """
    os.makedirs(directorio, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_base = metadata.get('titulo', 'encuesta')[:30]
    nombre_base = ''.join(c if c.isalnum() or c in '_-' else '_' for c in nombre_base)
    
    ruta = os.path.join(directorio, f"analisis_cuantitativo_{nombre_base}_{timestamp}.json")
    
    # Convertir a serializable
    def limpiar(obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        if isinstance(obj, dict):
            return {k: limpiar(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [limpiar(x) for x in obj]
        return convertir_a_serializable(obj)
    
    data = {
        'metadata': metadata,
        'resultados': limpiar(resultados),
        'fecha_generacion': datetime.now().isoformat()
    }
    
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"✅ JSON guardado: {ruta}")
    return ruta