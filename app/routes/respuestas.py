from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Encuesta, Pregunta, Opcion, Respuesta
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

respuestas_bp = Blueprint('respuestas', __name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@respuestas_bp.route('/seleccionar-encuesta')
@login_required
def seleccionar_encuesta():
    encuestas = Encuesta.query.filter_by(usuario_id=current_user.id).order_by(Encuesta.fecha_creacion.desc()).all()
    return render_template('seleccionar_encuesta.html', encuestas=encuestas)


@respuestas_bp.route('/encuesta/<int:encuesta_id>/cargar-respuestas', methods=['GET', 'POST'])
@login_required
def cargar_respuestas(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para modificar esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if not allowed_file(archivo.filename):
            flash('Formato no permitido. Use .xlsx, .xls o .csv', 'danger')
            return redirect(request.url)
        
        try:
            if archivo.filename.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
            
            columnas_archivo = list(df.columns)
            
            mapeo = {}
            for columna in columnas_archivo:
                pregunta_id = request.form.get(f'mapping_{columna}')
                if pregunta_id:
                    mapeo[columna] = int(pregunta_id)
            
            if not mapeo:
                flash('Debes mapear al menos una columna a una pregunta', 'danger')
                return redirect(request.url)
            
            total_guardadas = 0
            errores = []
            advertencias = []
            
            for idx, row in df.iterrows():
                identificador = f"R{idx+1:04d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                tiene_respuesta = False
                
                for columna, pregunta_id in mapeo.items():
                    pregunta = Pregunta.query.get(pregunta_id)
                    if not pregunta:
                        continue
                    
                    valor = row[columna]
                    
                    if pd.isna(valor) or str(valor).strip() == '':
                        continue
                    
                    valor_str = str(valor).strip()
                    tiene_respuesta = True
                    
                    if pregunta.tipo == 'texto_libre':
                        nueva_respuesta = Respuesta(
                            encuesta_id=encuesta_id,
                            pregunta_id=pregunta.id,
                            texto_libre=valor_str,
                            identificador_respuesta=identificador
                        )
                        db.session.add(nueva_respuesta)
                        total_guardadas += 1
                    else:
                        opcion = Opcion.query.filter_by(
                            pregunta_id=pregunta.id,
                            texto=valor_str
                        ).first()
                        
                        if not opcion:
                            opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).all()
                            for o in opciones:
                                if valor_str.strip().lower() in o.texto.strip().lower() or o.texto.strip().lower() in valor_str.strip().lower():
                                    opcion = o
                                    break
                        
                        if opcion:
                            nueva_respuesta = Respuesta(
                                encuesta_id=encuesta_id,
                                pregunta_id=pregunta.id,
                                opcion_id=opcion.id,
                                identificador_respuesta=identificador
                            )
                            db.session.add(nueva_respuesta)
                            total_guardadas += 1
                        else:
                            errores.append(f"Fila {idx+1}: No se encontró la opción '{valor_str}' para la pregunta '{pregunta.texto[:30]}'")
                
                if not tiene_respuesta:
                    advertencias.append(f"Fila {idx+1}: No se encontraron respuestas válidas")
            
            db.session.commit()
            
            if total_guardadas > 0:
                flash(f'✅ {total_guardadas} respuestas cargadas exitosamente de {len(df)} filas', 'success')
            if advertencias:
                flash(f'⚠️ {len(advertencias)} advertencias encontradas', 'warning')
            if errores:
                flash(f'⚠️ {len(errores)} errores encontrados. Revisa los detalles.', 'warning')
            
            return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.url)
    
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).count()
    if total_respuestas > 0:
        identificadores = db.session.query(Respuesta.identificador_respuesta).filter_by(encuesta_id=encuesta_id).distinct().count()
    else:
        identificadores = 0
    
    return render_template('cargar_respuestas.html', 
                         encuesta=encuesta, 
                         preguntas=preguntas,
                         total_respuestas=total_respuestas,
                         identificadores=identificadores)


@respuestas_bp.route('/encuesta/<int:encuesta_id>/previsualizar', methods=['POST'])
@login_required
def previsualizar_archivo(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        return jsonify({'error': 'No tienes permiso'}), 403
    
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    archivo = request.files['archivo']
    
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    try:
        if archivo.filename.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)
        
        columnas = list(df.columns)
        preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).all()
        
        preguntas_data = [{'id': p.id, 'texto': p.texto, 'tipo': p.tipo} for p in preguntas]
        
        return jsonify({
            'columnas': columnas,
            'preguntas': preguntas_data,
            'preview': df.head(5).to_dict('records')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@respuestas_bp.route('/encuesta/<int:encuesta_id>/respuestas')
@login_required
def ver_respuestas(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para ver esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).order_by(Respuesta.fecha_respuesta.desc()).all()
    
    respuestas_agrupadas = {}
    for r in respuestas:
        if r.identificador_respuesta not in respuestas_agrupadas:
            respuestas_agrupadas[r.identificador_respuesta] = []
        respuestas_agrupadas[r.identificador_respuesta].append(r)
    
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    return render_template('ver_respuestas.html', 
                         encuesta=encuesta, 
                         respuestas_agrupadas=respuestas_agrupadas,
                         preguntas=preguntas,
                         total_encuestados=len(respuestas_agrupadas))


@respuestas_bp.route('/encuesta/<int:encuesta_id>/respuestas/eliminar', methods=['POST'])
@login_required
def eliminar_respuestas(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para eliminar estas respuestas', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    Respuesta.query.filter_by(encuesta_id=encuesta_id).delete()
    db.session.commit()
    flash('✅ Todas las respuestas han sido eliminadas', 'success')
    return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))


@respuestas_bp.route('/encuesta/<int:encuesta_id>/respuestas/exportar')
@login_required
def exportar_respuestas(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para exportar estas respuestas', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).all()
    
    if not respuestas:
        flash('No hay respuestas para exportar', 'warning')
        return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))
    
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    datos_agrupados = {}
    for r in respuestas:
        if r.identificador_respuesta not in datos_agrupados:
            datos_agrupados[r.identificador_respuesta] = {}
        if r.opcion:
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.opcion.texto
        else:
            datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = r.texto_libre
    
    data = []
    for identificador, respuestas_dict in datos_agrupados.items():
        row = {'Identificador': identificador}
        for pregunta in preguntas:
            row[pregunta.texto] = respuestas_dict.get(pregunta.texto, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Respuestas', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'respuestas_{encuesta.titulo[:30]}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


@respuestas_bp.route('/encuesta/<int:encuesta_id>/respuestas/eliminar-ajax', methods=['POST'])
@login_required
def eliminar_respuestas_ajax(encuesta_id):
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        Respuesta.query.filter_by(encuesta_id=encuesta_id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': '✅ Todas las respuestas han sido eliminadas'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500