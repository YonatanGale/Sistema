# app/routes/cuantitativo.py
"""
Rutas para el Motor de Análisis Cuantitativo.
"""

import os
import logging
from flask import (
    Blueprint, render_template, request, jsonify, send_file,
    current_app, abort, flash, redirect, url_for, session
)
from flask_login import login_required
from datetime import datetime

logger = logging.getLogger(__name__)

cuantitativo_bp = Blueprint('cuantitativo', __name__)

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# RUTA PRINCIPAL: PÁGINA DEL MOTOR
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo')
@login_required
def motor_cuantitativo():
    """Página principal del motor cuantitativo"""
    return render_template('motor_cuantitativo.html')


# ============================================
# RUTA AJAX: ANALIZAR CSV
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/analizar', methods=['POST'])
@login_required
def analizar():
    """Analiza un archivo CSV usando el motor cuantitativo"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        if not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'Formato no permitido. Use .csv'}), 400
        
        # Importar el wrapper
        from app.utils.motor_cuantitativo_wrapper import analizar_con_motor_cuantitativo
        
        # Ejecutar análisis
        resultados = analizar_con_motor_cuantitativo(archivo)
        
        # ✅ GUARDAR EN SESIÓN PARA PDF/EXCEL POSTERIOR
        if resultados.get('success'):
            session['ultimo_analisis_cuantitativo'] = {
                'directorio': resultados.get('directorio_resultados'),
                'archivo_excel': resultados.get('archivo_excel'),
                'timestamp': resultados.get('timestamp')
            }
        
        return jsonify(resultados)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RUTA: DESCARGAR EXCEL DEL ÚLTIMO ANÁLISIS
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/descargar-excel')
@login_required
def descargar_excel():
    """Descarga el Excel generado en el último análisis"""
    info = session.get('ultimo_analisis_cuantitativo')
    
    if not info or not info.get('archivo_excel'):
        flash('⚠️ No hay análisis para descargar. Ejecuta un análisis primero.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    
    directorio = info.get('directorio')
    nombre_archivo = info.get('archivo_excel')
    ruta = os.path.join(directorio, nombre_archivo)
    
    if not os.path.exists(ruta):
        flash('⚠️ El archivo ya no está disponible', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    
    return send_file(
        ruta,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nombre_archivo
    )


# ============================================
# RUTA: DESCARGAR PDF DEL ÚLTIMO ANÁLISIS
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/descargar-pdf')
@login_required
def descargar_pdf():
    """
    Genera y descarga un PDF completo con todos los resultados del último análisis.
    """
    info = session.get('ultimo_analisis_cuantitativo')
    
    if not info or not info.get('directorio'):
        flash('⚠️ No hay análisis para descargar. Ejecuta un análisis primero.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    
    directorio = info.get('directorio')
    
    if not os.path.exists(directorio):
        flash('⚠️ El directorio de resultados ya no existe', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    
    try:
        from app.utils.generar_pdf_cuantitativo import generar_pdf_analisis_cuantitativo
        
        # Generar PDF
        pdf_buffer = generar_pdf_analisis_cuantitativo(directorio)
        
        # Nombre del archivo
        timestamp = info.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        nombre_archivo = f"analisis_cuantitativo_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except ImportError as e:
        logger.error(f"Error importando generador PDF: {e}")
        flash('❌ Error: Falta instalar reportlab. Ejecuta: pip install reportlab', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'❌ Error al generar el PDF: {str(e)}', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))


# ============================================
# RUTA: SERVIR GRÁFICO ESPECÍFICO
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/grafico/<timestamp>/<nombre_archivo>')
@login_required
def servir_grafico(timestamp, nombre_archivo):
    """Sirve un gráfico PNG específico del análisis"""
    if '..' in nombre_archivo or '/' in nombre_archivo or '\\' in nombre_archivo:
        abort(400)
    
    if '..' in timestamp or '/' in timestamp or '\\' in timestamp:
        abort(400)
    
    ruta = os.path.join(
        BASE_DIR, 'motor_cuantitativo', 'data', 'resultados',
        f'motor_{timestamp}', 'graficos', nombre_archivo
    )
    
    if not os.path.exists(ruta):
        abort(404)
    
    return send_file(ruta, mimetype='image/png')