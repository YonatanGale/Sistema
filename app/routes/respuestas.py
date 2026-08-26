from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Encuesta, Pregunta, Opcion, Respuesta
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
import unicodedata

respuestas_bp = Blueprint('respuestas', __name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# FUNCIÓN DE NORMALIZACIÓN DE TEXTOS
# ============================================

def normalizar_texto(texto):
    """
    Elimina tildes y convierte a minúsculas para comparación
    Útil para: "Sí" → "si", "Muy Bueno" → "muy bueno"
    """
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


# ============================================
# FUNCIÓN DE MAPEO DE VALORES
# ============================================

def mapear_valor_opcion(valor, opciones):
    """
    Mapea un valor a una opción existente.
    - Números: 1, 2, 3, 4, 5 → opción en esa posición
    - 0 → "No" (para preguntas Sí/No)
    - 1 → "Sí" (para preguntas Sí/No)
    - Letras: A, B, C, D, E → opción en esa posición
    - Texto exacto (con o sin tildes)
    - true/false → Sí/No
    """
    if not opciones:
        return None
    
    valor_str = str(valor).strip()
    valor_normalizado = normalizar_texto(valor_str)
    
    # ============================================
    # 0. MAPEO ESPECIAL PARA SÍ/NO (0 → No, 1 → Sí)
    # ============================================
    if len(opciones) == 2:
        opciones_texto = [normalizar_texto(o.texto) for o in opciones]
        if 'si' in opciones_texto and 'no' in opciones_texto:
            # Mapear 0 → No, 1 → Sí
            if valor_str == '0':
                for opcion in opciones:
                    if normalizar_texto(opcion.texto) == 'no':
                        return opcion
            elif valor_str == '1':
                for opcion in opciones:
                    if normalizar_texto(opcion.texto) == 'si':
                        return opcion
            elif valor_str.lower() in ['true', 'verdadero']:
                for opcion in opciones:
                    if normalizar_texto(opcion.texto) == 'si':
                        return opcion
            elif valor_str.lower() in ['false', 'falso']:
                for opcion in opciones:
                    if normalizar_texto(opcion.texto) == 'no':
                        return opcion
    
    # 1. Coincidencia exacta (case insensitive)
    for opcion in opciones:
        if opcion.texto.strip().lower() == valor_str.lower():
            return opcion
    
    # 2. Coincidencia normalizada (sin tildes)
    for opcion in opciones:
        if normalizar_texto(opcion.texto) == valor_normalizado:
            return opcion
    
    # 3. Mapeo: A → 1ª opción, B → 2ª opción, etc.
    if len(valor_str) == 1 and valor_str.isalpha():
        letra_index = ord(valor_str.upper()) - ord('A')
        if 0 <= letra_index < len(opciones):
            return opciones[letra_index]
    
    # 4. Mapeo: 1 → 1ª opción, 2 → 2ª opción, etc.
    if valor_str.isdigit():
        numero = int(valor_str)
        if 1 <= numero <= len(opciones):
            return opciones[numero - 1]
    
    return None


# ============================================
# RUTA: SELECCIONAR ENCUESTA
# ============================================

@respuestas_bp.route('/seleccionar-encuesta')
@login_required
def seleccionar_encuesta():
    encuestas = Encuesta.query.filter_by(usuario_id=current_user.id).order_by(Encuesta.fecha_creacion.desc()).all()
    return render_template('seleccionar_encuesta.html', encuestas=encuestas)


# ============================================
# RUTA: CARGAR RESPUESTAS
# ============================================

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
                df = pd.read_csv(archivo, encoding='utf-8', quotechar='"')
            else:
                df = pd.read_excel(archivo)
            
            df = df.where(pd.notnull(df), None)
            
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
                    
                    if valor is None or pd.isna(valor) or str(valor).strip() == '':
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
                        opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).all()
                        opcion = mapear_valor_opcion(valor_str, opciones)
                        
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
                            opciones_texto = [o.texto for o in opciones]
                            errores.append(f"Fila {idx+1}: No se encontró la opción '{valor_str}'. Opciones disponibles: {opciones_texto}")
                
                if not tiene_respuesta:
                    advertencias.append(f"Fila {idx+1}: No se encontraron respuestas válidas")
            
            db.session.commit()
            
            if total_guardadas > 0:
                flash(f'✅ {total_guardadas} respuestas cargadas exitosamente de {len(df)} filas', 'success')
            if advertencias:
                flash(f'⚠️ {len(advertencias)} advertencias encontradas', 'warning')
            if errores:
                errores_mostrar = errores[:5]
                flash(f'⚠️ {len(errores)} errores encontrados: {", ".join(errores_mostrar)}', 'warning')
            
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


# ============================================
# RUTA: PREVISUALIZAR ARCHIVO
# ============================================

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
        import io
        
        if archivo.filename.endswith('.csv'):
            content = archivo.stream.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content), quotechar='"')
        else:
            df = pd.read_excel(archivo)
        
        df = df.where(pd.notnull(df), None)
        columnas = list(df.columns)
        columnas_limpias = [col.strip('"').strip() for col in columnas]
        
        preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).all()
        preguntas_data = [{'id': p.id, 'texto': p.texto, 'tipo': p.tipo} for p in preguntas]
        
        preview = df.head(5).to_dict('records')
        
        preview_limpio = []
        for row in preview:
            row_limpio = {}
            for key, value in row.items():
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    row_limpio[key] = ''
                else:
                    row_limpio[key] = value
            preview_limpio.append(row_limpio)
        
        return jsonify({
            'success': True,
            'columnas': columnas_limpias,
            'preguntas': preguntas_data,
            'preview': preview_limpio
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# RUTA: VER RESPUESTAS
# ============================================

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


# ============================================
# RUTA: ELIMINAR RESPUESTAS (POST tradicional)
# ============================================

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


# ============================================
# RUTA: EXPORTAR RESPUESTAS (Todas)
# ============================================

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
            if r.opcion.es_otro() and r.texto_libre:
                datos_agrupados[r.identificador_respuesta][r.pregunta.texto] = f"Otro: {r.texto_libre}"
            else:
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


# ============================================
# RUTA AJAX: ELIMINAR RESPUESTA INDIVIDUAL (por ID)
# ============================================

@respuestas_bp.route('/respuesta/<int:respuesta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_respuesta(respuesta_id):
    """Elimina una respuesta individual por su ID"""
    try:
        respuesta = Respuesta.query.get_or_404(respuesta_id)
        encuesta = respuesta.encuesta
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        db.session.delete(respuesta)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '✅ Respuesta eliminada exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RUTA AJAX: ELIMINAR RESPUESTAS POR IDENTIFICADOR
# ============================================

@respuestas_bp.route('/encuesta/<int:encuesta_id>/respuestas/<string:identificador>/eliminar', methods=['POST'])
@login_required
def eliminar_respuestas_por_identificador(encuesta_id, identificador):
    """Elimina todas las respuestas de un encuestado específico"""
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        respuestas = Respuesta.query.filter_by(
            encuesta_id=encuesta_id,
            identificador_respuesta=identificador
        ).all()
        
        if not respuestas:
            return jsonify({'success': False, 'message': 'No se encontraron respuestas'}), 404
        
        for r in respuestas:
            db.session.delete(r)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'✅ {len(respuestas)} respuestas eliminadas exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RUTA AJAX: ELIMINAR TODAS LAS RESPUESTAS
# ============================================

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


# ============================================
# RUTA AJAX: CARGAR RESPUESTAS (desde modal)
# ============================================

@respuestas_bp.route('/encuesta/<int:encuesta_id>/cargar-respuestas-ajax', methods=['POST'])
@login_required
def cargar_respuestas_ajax(encuesta_id):
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        allowed = {'xlsx', 'xls', 'csv'}
        if not ('.' in archivo.filename and archivo.filename.rsplit('.', 1)[1].lower() in allowed):
            return jsonify({'success': False, 'message': 'Formato no permitido'}), 400
        
        if archivo.filename.endswith('.csv'):
            df = pd.read_csv(archivo, encoding='utf-8', quotechar='"')
        else:
            df = pd.read_excel(archivo)
        
        df = df.where(pd.notnull(df), None)
        columnas_archivo = list(df.columns)
        
        mapeo = {}
        for columna in columnas_archivo:
            pregunta_id = request.form.get(f'mapping_{columna}')
            if pregunta_id:
                mapeo[columna] = int(pregunta_id)
        
        if not mapeo:
            return jsonify({'success': False, 'message': 'Debes mapear al menos una columna'}), 400
        
        total_guardadas = 0
        errores = []
        
        for idx, row in df.iterrows():
            identificador = f"R{idx+1:04d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            for columna, pregunta_id in mapeo.items():
                pregunta = Pregunta.query.get(pregunta_id)
                if not pregunta:
                    continue
                
                valor = row[columna]
                if valor is None or pd.isna(valor) or str(valor).strip() == '':
                    continue
                
                valor_str = str(valor).strip()
                
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
                    opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).all()
                    opcion = mapear_valor_opcion(valor_str, opciones)
                    
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
                        errores.append(f"Fila {idx+1}: No se encontró la opción '{valor_str}'")
        
        db.session.commit()
        
        mensaje = f'✅ {total_guardadas} respuestas cargadas exitosamente'
        if errores:
            mensaje += f' ⚠️ {len(errores)} errores encontrados'
        
        return jsonify({
            'success': True,
            'message': mensaje,
            'close_modal': True,
            'reload': True
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RUTA: EXPORTAR DATOS CUALITATIVOS
# ============================================

@respuestas_bp.route('/encuesta/<int:encuesta_id>/exportar/cualitativos')
@login_required
def exportar_cualitativos(encuesta_id):
    """Exporta preguntas cualitativas y sus respuestas"""
    from app.utils.exportar_datos import exportar_datos_cualitativos
    
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para exportar estos datos', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    output = exportar_datos_cualitativos(encuesta_id)
    
    if output is None:
        flash('⚠️ No hay preguntas cualitativas (texto libre) en esta encuesta', 'warning')
        return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'datos_cualitativos_{encuesta.titulo[:30]}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


# ============================================
# RUTA: EXPORTAR DATOS CUANTITATIVOS
# ============================================

@respuestas_bp.route('/encuesta/<int:encuesta_id>/exportar/cuantitativos')
@login_required
def exportar_cuantitativos(encuesta_id):
    """Exporta preguntas cuantitativas con todas las opciones posibles y estadísticas"""
    from app.utils.exportar_datos import exportar_datos_cuantitativos
    
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para exportar estos datos', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    output = exportar_datos_cuantitativos(encuesta_id)
    
    if output is None:
        flash('⚠️ No hay preguntas cuantitativas (cerradas) en esta encuesta', 'warning')
        return redirect(url_for('respuestas.ver_respuestas', encuesta_id=encuesta_id))
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'datos_cuantitativos_{encuesta.titulo[:30]}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )