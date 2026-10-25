# app/routes/motor_integrado.py
"""
Rutas del Motor Integrado (cuantitativo + cualitativo).
"""

import os
import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, session, flash, redirect,
    url_for, send_file
)
from flask_login import login_required

logger = logging.getLogger(__name__)

motor_integrado_bp = Blueprint('motor_integrado', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# PÁGINA PRINCIPAL
# ============================================
@motor_integrado_bp.route('/motor-integrado')
@login_required
def motor_integrado():
    """Página de carga del motor integrado."""
    return render_template('motor_integrado.html')


# ============================================
# AJAX: ANALIZAR CSV UNIFICADO
# ============================================
@motor_integrado_bp.route('/motor-integrado/analizar', methods=['POST'])
@login_required
def analizar():
    """Analiza un CSV unificado usando ambos motores."""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó archivo'}), 400

        archivo = request.files['archivo']

        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'Archivo vacío'}), 400

        if not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'Formato no permitido. Use .csv'}), 400

        from app.utils.motor_integrado_wrapper import analizar_con_motores_integrados
        resultados = analizar_con_motores_integrados(archivo)

        if resultados.get('success'):
            session['ultimo_analisis_integrado'] = {
                'timestamp': resultados.get('timestamp'),
                'cuantitativo_dir': (
                    resultados['cuantitativo'].get('directorio_resultados')
                    if resultados.get('cuantitativo') else None
                ),
                'cuantitativo_excel': (
                    resultados['cuantitativo'].get('archivo_excel')
                    if resultados.get('cuantitativo') else None
                ),
            }

        return jsonify(resultados)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# DESCARGAR EXCEL CUANTITATIVO
# ============================================
@motor_integrado_bp.route('/motor-integrado/descargar-excel')
@login_required
def descargar_excel():
    """Descarga el Excel del análisis cuantitativo."""
    info = session.get('ultimo_analisis_integrado')

    if not info or not info.get('cuantitativo_dir') or not info.get('cuantitativo_excel'):
        flash('⚠️ No hay análisis cuantitativo para descargar.', 'warning')
        return redirect(url_for('motor_integrado.motor_integrado'))

    ruta = os.path.join(info['cuantitativo_dir'], info['cuantitativo_excel'])
    if not os.path.exists(ruta):
        flash('⚠️ El archivo ya no está disponible.', 'warning')
        return redirect(url_for('motor_integrado.motor_integrado'))

    return send_file(
        ruta,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=info['cuantitativo_excel'],
    )


# ============================================
# DESCARGAR PDF CUALITATIVO
# ============================================
@motor_integrado_bp.route('/motor-integrado/descargar-pdf-cualitativo')
@login_required
def descargar_pdf_cualitativo():
    """Descarga el PDF del análisis cualitativo."""
    resultados = session.get('ultimo_analisis')
    if not resultados:
        flash('⚠️ No hay análisis cualitativo para descargar.', 'warning')
        return redirect(url_for('motor_integrado.motor_integrado'))

    try:
        from app.utils.generar_pdf import generar_pdf_analisis
        pdf_buffer = generar_pdf_analisis(resultados)
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'analisis_cualitativo_{fecha}.pdf',
        )
    except Exception as e:
        flash(f'❌ Error al generar PDF: {str(e)}', 'danger')
        return redirect(url_for('motor_integrado.motor_integrado'))


# ============================================
# EXPORTAR CSV UNIFICADO DESDE UNA ENCUESTA
# ============================================
@motor_integrado_bp.route('/exportar-completo/<int:encuesta_id>')
@login_required
def exportar_completo(encuesta_id):
    """Genera y descarga el CSV unificado de una encuesta."""
    from app.utils.exportar_encuesta_completa import exportar_encuesta_completa

    resultado = exportar_encuesta_completa(encuesta_id)

    if not resultado.get('ruta'):
        flash(f"⚠️ {resultado.get('mensaje', 'Error')}", 'warning')
        return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))

    return send_file(
        resultado['ruta'],
        mimetype='text/csv',
        as_attachment=True,
        download_name=resultado['nombre_archivo'],
    )