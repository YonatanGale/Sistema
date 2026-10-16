# app/routes/cuantitativo.py
"""
Rutas para el Motor de Análisis Cuantitativo.
"""

import os
import json
import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, send_file,
    abort, flash, redirect, url_for, session
)
from flask_login import login_required

logger = logging.getLogger(__name__)

cuantitativo_bp = Blueprint('cuantitativo', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# HELPERS
# ============================================

def _directorio_padre_resultados():
    return os.path.join(BASE_DIR, 'motor_cuantitativo', 'data', 'resultados')


def _cargar_json_analisis(directorio):
    """Carga el JSON del análisis desde un directorio de resultados."""
    if not directorio or not os.path.exists(directorio):
        return None
    for archivo in os.listdir(directorio):
        if archivo.startswith('analisis_cuantitativo_') and archivo.endswith('.json'):
            ruta = os.path.join(directorio, archivo)
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando {ruta}: {e}")
                return None
    return None


def _cargar_htmls_graficos(directorio):
    """
    Lee el archivo auxiliar _graficos_html.json si existe.
    Devuelve {nombre_grafico: html_string}.
    """
    ruta = os.path.join(directorio, '_graficos_html.json')
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"No se pudo leer _graficos_html.json: {e}")
        return {}


def _construir_lista_graficos(directorio):
    """
    Construye la lista de gráficos para el template.
    Combina:
      - PNGs del directorio graficos/
      - HTMLs interactivos del archivo _graficos_html.json (si existe)
    """
    directorio_graficos = os.path.join(directorio, 'graficos')
    if not os.path.exists(directorio_graficos):
        return []

    htmls = _cargar_htmls_graficos(directorio)

    archivos = sorted([f for f in os.listdir(directorio_graficos) if f.endswith('.png')])

    lista = []
    for archivo in archivos:
        clave = archivo.replace('.png', '')   # ej: "P5_En_que_ano_naciste_barras"

        nombre_legible = (
            archivo.replace('.png', '')
            .replace('_', ' ')
            .title()
            .replace('P5 ', 'P5 · ')
            .replace('P6 ', 'P6 · ')
        )

        html = htmls.get(clave) or htmls.get(archivo)

        lista.append({
            'nombre': nombre_legible,
            'archivo': archivo,
            'archivo_png': archivo,
            'html': html,     # None → cae a <img>
        })

    return lista


def _obtener_analisis_de_sesion():
    return session.get('ultimo_analisis_cuantitativo')


def _guardar_analisis_en_sesion(resultados):
    session['ultimo_analisis_cuantitativo'] = {
        'directorio': resultados.get('directorio_resultados'),
        'archivo_excel': resultados.get('archivo_excel'),
        'timestamp': resultados.get('timestamp'),
        'preguntas_sin_datos': resultados.get('preguntas_sin_datos', []),
    }


# ============================================
# PÁGINA PRINCIPAL DEL MOTOR (subida CSV)
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo')
@login_required
def motor_cuantitativo():
    """Página principal del motor cuantitativo (subida de CSV)."""
    return render_template('motor_cuantitativo.html')


# ============================================
# AJAX: ANALIZAR CSV SUBIDO
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/analizar', methods=['POST'])
@login_required
def analizar():
    """Analiza un archivo CSV usando el motor cuantitativo."""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400

        archivo = request.files['archivo']

        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400

        if not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'Formato no permitido. Use .csv'}), 400

        from app.utils.motor_cuantitativo_wrapper import analizar_con_motor_cuantitativo
        resultados = analizar_con_motor_cuantitativo(archivo)

        if resultados.get('success'):
            _guardar_analisis_en_sesion(resultados)

        return jsonify(resultados)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# DASHBOARD (vista persistente)
# ============================================

@cuantitativo_bp.route('/dashboard-cuantitativo/<int:encuesta_id>')
@login_required
def dashboard_cuantitativo(encuesta_id):
    """
    Renderiza el dashboard con el último análisis disponible.
    Si no hay análisis en sesión, redirige al motor para subir uno.
    """
    info = _obtener_analisis_de_sesion()

    if not info or not info.get('directorio'):
        flash('⚠️ No hay análisis disponible. Sube un CSV en el motor cuantitativo.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    directorio = info.get('directorio')
    if not os.path.exists(directorio):
        flash('⚠️ El directorio del último análisis ya no existe.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    analisis = _cargar_json_analisis(directorio)
    if not analisis:
        flash('⚠️ No se pudo cargar el JSON del análisis.', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    metadata = analisis.get('metadata', {})
    resultados = analisis.get('resultados', {})

    # Cargar encuesta
    try:
        from app.models import Encuesta
        encuesta = Encuesta.query.get(encuesta_id)
    except Exception as e:
        logger.error(f"Error cargando encuesta {encuesta_id}: {e}")
        encuesta = None

    if not encuesta:
        abort(404)

    graficos = _construir_lista_graficos(directorio)

    excel_disponible = False
    if info.get('archivo_excel'):
        excel_disponible = os.path.exists(os.path.join(directorio, info['archivo_excel']))

    fecha_analisis = analisis.get('fecha_generacion', datetime.now().isoformat())

    return render_template(
        'dashboard_cuantitativo.html',
        encuesta=encuesta,
        metadata=metadata,
        resultados=resultados,
        graficos=graficos,
        fecha_analisis=fecha_analisis,
        excel_disponible=excel_disponible,
        preguntas_sin_datos=info.get('preguntas_sin_datos', []),
    )


# ============================================
# RE-ANALIZAR DESDE UNA ENCUESTA
# ============================================

@cuantitativo_bp.route('/analizar-cuantitativo/<int:encuesta_id>')
@login_required
def analizar_cuantitativo(encuesta_id):
    """
    Re-ejecuta el análisis: exporta el CSV de la encuesta y lo procesa.
    """
    try:
        from app.utils.exportar_cuantitativo_csv import exportar_respuestas_cuantitativas
        from app.utils.motor_cuantitativo_wrapper import analizar_con_motor_cuantitativo
        from werkzeug.datastructures import FileStorage

        # 1. Exportar CSV
        exportacion = exportar_respuestas_cuantitativas(encuesta_id)
        if not exportacion.get('ruta'):
            flash(f'⚠️ {exportacion.get("mensaje", "No se pudo exportar")}', 'warning')
            return redirect(url_for('cuantitativo.motor_cuantitativo'))

        ruta_csv = exportacion['ruta']

        # 2. Ejecutar análisis
        with open(ruta_csv, 'rb') as f:
            archivo_fs = FileStorage(
                stream=f,
                filename=os.path.basename(ruta_csv),
                content_type='text/csv',
            )
            resultados = analizar_con_motor_cuantitativo(archivo_fs)

        if not resultados.get('success'):
            flash(f"❌ {resultados.get('message', 'Error desconocido')}", 'danger')
            return redirect(url_for('cuantitativo.motor_cuantitativo'))

        _guardar_analisis_en_sesion(resultados)

        return redirect(url_for('cuantitativo.dashboard_cuantitativo', encuesta_id=encuesta_id))

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))


# ============================================
# DESCARGAR EXCEL
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/descargar-excel')
@login_required
def descargar_excel():
    """Descarga el Excel del último análisis."""
    info = _obtener_analisis_de_sesion()

    if not info or not info.get('archivo_excel'):
        flash('⚠️ No hay análisis para descargar.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    directorio = info.get('directorio')
    nombre_archivo = info.get('archivo_excel')
    ruta = os.path.join(directorio, nombre_archivo)

    if not os.path.exists(ruta):
        flash('⚠️ El archivo ya no está disponible.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    return send_file(
        ruta,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nombre_archivo,
    )


@cuantitativo_bp.route('/dashboard-cuantitativo/<int:encuesta_id>/excel')
@login_required
def descargar_analisis_excel(encuesta_id):
    """Alias para el botón del dashboard."""
    return descargar_excel()


# ============================================
# DESCARGAR PDF
# ============================================

@cuantitativo_bp.route('/motor-cuantitativo/descargar-pdf')
@login_required
def descargar_pdf():
    """Genera y descarga el PDF del último análisis."""
    info = _obtener_analisis_de_sesion()

    if not info or not info.get('directorio'):
        flash('⚠️ No hay análisis para descargar.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    directorio = info.get('directorio')
    if not os.path.exists(directorio):
        flash('⚠️ El directorio de resultados ya no existe.', 'warning')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))

    try:
        from app.utils.generar_pdf_cuantitativo import generar_pdf_analisis_cuantitativo

        pdf_buffer = generar_pdf_analisis_cuantitativo(directorio)

        timestamp = info.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        nombre_archivo = f"analisis_cuantitativo_{timestamp}.pdf"

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo,
        )

    except ImportError as e:
        logger.error(f"Error importando generador PDF: {e}")
        flash('❌ Falta instalar reportlab.', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'❌ Error al generar el PDF: {str(e)}', 'danger')
        return redirect(url_for('cuantitativo.motor_cuantitativo'))


# ============================================
# SERVIR GRÁFICOS
# ============================================

@cuantitativo_bp.route('/dashboard-cuantitativo/<int:encuesta_id>/grafico/<nombre_archivo>')
@login_required
def servir_grafico(encuesta_id, nombre_archivo):
    """
    Sirve un PNG del último análisis. Compatible con el template
    dashboard_cuantitativo.html que llama:
        url_for('cuantitativo.servir_grafico', encuesta_id=..., nombre_archivo=...)
    """
    if '..' in nombre_archivo or '/' in nombre_archivo or '\\' in nombre_archivo:
        abort(400)

    info = _obtener_analisis_de_sesion()
    if not info or not info.get('directorio'):
        abort(404)

    ruta = os.path.join(info['directorio'], 'graficos', nombre_archivo)
    if not os.path.exists(ruta):
        abort(404)

    return send_file(ruta, mimetype='image/png')


# Backward compat: ruta antigua por timestamp
@cuantitativo_bp.route('/motor-cuantitativo/grafico/<timestamp>/<nombre_archivo>')
@login_required
def servir_grafico_timestamp(timestamp, nombre_archivo):
    """Sirve un PNG por timestamp (formato antiguo)."""
    if '..' in nombre_archivo or '/' in nombre_archivo or '\\' in nombre_archivo:
        abort(400)
    if '..' in timestamp or '/' in timestamp or '\\' in timestamp:
        abort(400)

    ruta = os.path.join(
        BASE_DIR, 'motor_cuantitativo', 'data', 'resultados',
        f'motor_{timestamp}', 'graficos', nombre_archivo,
    )

    if not os.path.exists(ruta):
        abort(404)

    return send_file(ruta, mimetype='image/png')