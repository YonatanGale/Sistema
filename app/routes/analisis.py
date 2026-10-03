# app/routes/analisis.py
from flask import Blueprint, render_template, request, jsonify, send_file, session
from flask_login import login_required
from datetime import datetime

analisis_bp = Blueprint('analisis', __name__)


@analisis_bp.route('/motor-analisis')
@login_required
def motor_analisis():
    """Página principal del motor de análisis"""
    return render_template('motor_analisis.html')


@analisis_bp.route('/motor-analisis/analizar', methods=['POST'])
@login_required
def analizar():
    """Analiza un archivo CSV usando el motor cualitativo"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        if not archivo.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'Formato no permitido. Use .csv'}), 400
        
        # Importar el wrapper
        from app.utils.motor_wrapper import analizar_con_motor
        
        # Ejecutar análisis
        resultados = analizar_con_motor(archivo)
        
        # ✅ GUARDAR RESULTADOS EN SESIÓN PARA PODER EXPORTAR A PDF
        if resultados.get('success'):
            session['ultimo_analisis'] = resultados
            session['ultimo_analisis_fecha'] = datetime.now().isoformat()
        
        return jsonify(resultados)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@analisis_bp.route('/motor-analisis/exportar-pdf', methods=['GET'])
@login_required
def exportar_pdf():
    """Exporta los resultados del último análisis a PDF"""
    try:
        resultados = session.get('ultimo_analisis')
        
        if not resultados:
            return jsonify({
                'success': False,
                'message': 'No hay análisis para exportar. Ejecuta un análisis primero.'
            }), 400
        
        # Importar el generador de PDF
        from app.utils.generar_pdf import generar_pdf_analisis
        
        # Generar PDF
        pdf_buffer = generar_pdf_analisis(resultados)
        
        # Nombre del archivo
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'analisis_cualitativo_{fecha}.pdf'
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}. Instala WeasyPrint con: pip install weasyprint'
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500