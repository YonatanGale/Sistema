from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Encuesta, Pregunta, Opcion, Respuesta
from datetime import datetime
import pandas as pd
import unicodedata

encuestas_bp = Blueprint('encuestas', __name__)


# ============================================
# FUNCIONES DE NORMALIZACIÓN Y MAPEO
# ============================================

def normalizar_texto(texto):
    """Elimina tildes y convierte a minúsculas para comparación"""
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


def mapear_valor_opcion(valor, opciones):
    """
    Mapea un valor a una opción existente.
    - Números: 1, 2, 3, 4, 5 → opción en esa posición
    - Letras: A, B, C, D, E → opción en esa posición
    - Texto exacto (con o sin tildes)
    """
    if not opciones:
        return None
    
    valor_str = str(valor).strip()
    
    # 1. MAPEO POR NÚMERO (1 → 1ª opción)
    try:
        if valor_str.isdigit():
            num = int(valor_str)
            if 1 <= num <= len(opciones):
                return opciones[num - 1]
        elif valor_str.replace('.', '').isdigit():
            num = int(float(valor_str))
            if 1 <= num <= len(opciones):
                return opciones[num - 1]
    except (ValueError, TypeError):
        pass
    
    # 2. MAPEO POR LETRA (A → 1ª opción)
    if len(valor_str) == 1 and valor_str.isalpha():
        letra_index = ord(valor_str.upper()) - ord('A')
        if 0 <= letra_index < len(opciones):
            return opciones[letra_index]
    
    # 3. COINCIDENCIA EXACTA (sin tildes)
    valor_normalizado = normalizar_texto(valor_str)
    for opcion in opciones:
        if normalizar_texto(opcion.texto) == valor_normalizado:
            return opcion
    
    # 4. COINCIDENCIA PARCIAL
    for opcion in opciones:
        opcion_normalizado = normalizar_texto(opcion.texto)
        if valor_normalizado in opcion_normalizado or opcion_normalizado in valor_normalizado:
            return opcion
    
    return None


def procesar_opcion_multiple(valor_str, pregunta_id, encuesta_id, identificador, opciones):
    """
    Procesa respuestas de opción múltiple.
    El valor puede ser: "Opcion1, Opcion2, Opcion3" o "1,3,5"
    """
    if not valor_str or not opciones:
        return None
    
    # Dividir por comas
    valores = [v.strip() for v in valor_str.split(',') if v.strip()]
    
    opciones_encontradas = []
    opciones_ids = []
    textos = []
    
    for v in valores:
        opcion = mapear_valor_opcion(v, opciones)
        if opcion:
            opciones_encontradas.append(opcion)
            opciones_ids.append(str(opcion.id))
            textos.append(opcion.texto)
        else:
            print(f"  ⚠️ Opción no encontrada para: '{v}'")
    
    if not opciones_encontradas:
        return None
    
    # Crear una sola respuesta con todas las opciones
    respuesta = Respuesta(
        encuesta_id=encuesta_id,
        pregunta_id=pregunta_id,
        texto_libre=','.join(textos),
        opciones_ids=','.join(opciones_ids),
        identificador_respuesta=identificador
    )
    
    return respuesta


def procesar_opcion_unica(valor_str, pregunta, opciones, encuesta_id, identificador):
    """
    Procesa respuestas de opción única, con soporte para "Otro".
    """
    if not valor_str or not opciones:
        return None
    
    valor_str_limpio = valor_str.strip()
    valor_lower = valor_str_limpio.lower()
    
    # ============================================
    # 1. VERIFICAR SI ES "OTRO"
    # ============================================
    for opcion in opciones:
        if opcion.es_otro():
            # Si el valor contiene "otro" (case insensitive)
            if 'otro' in valor_lower:
                # Extraer el texto después de "Otro" (si existe)
                texto_ingresado = ''
                
                # Buscar después de "Otro:" o "otro:"
                if ':' in valor_str_limpio:
                    partes = valor_str_limpio.split(':', 1)
                    if len(partes) > 1:
                        texto_ingresado = partes[1].strip()
                
                # Si no hay dos puntos, pero hay texto después de "otro"
                if not texto_ingresado and valor_lower != 'otro':
                    # Quitar la palabra "otro" del inicio
                    temp = valor_str_limpio
                    for prefijo in ['otro:', 'otro ', 'otro-', 'otro_']:
                        if temp.lower().startswith(prefijo):
                            texto_ingresado = temp[len(prefijo):].strip()
                            break
                
                # Si no hay texto adicional, usar "Otro" como texto
                if not texto_ingresado and valor_lower == 'otro':
                    texto_ingresado = 'Otro (sin especificar)'
                elif not texto_ingresado:
                    texto_ingresado = valor_str_limpio
                
                # Crear respuesta con opción "Otro" y texto ingresado
                respuesta = Respuesta(
                    encuesta_id=encuesta_id,
                    pregunta_id=pregunta.id,
                    opcion_id=opcion.id,
                    texto_libre=texto_ingresado,
                    identificador_respuesta=identificador
                )
                return respuesta
    
    # ============================================
    # 2. MAPEO NORMAL (por número, letra o texto)
    # ============================================
    opcion = mapear_valor_opcion(valor_str_limpio, opciones)
    
    if opcion:
        respuesta = Respuesta(
            encuesta_id=encuesta_id,
            pregunta_id=pregunta.id,
            opcion_id=opcion.id,
            identificador_respuesta=identificador
        )
        return respuesta
    
    return None


# ============================================
# RUTAS PRINCIPALES
# ============================================

@encuestas_bp.route('/crear-encuesta', methods=['GET', 'POST'])
@login_required
def crear_encuesta():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        
        if not titulo:
            flash('El título de la encuesta es obligatorio', 'danger')
            return redirect(url_for('encuestas.crear_encuesta'))
        
        nueva_encuesta = Encuesta(
            titulo=titulo,
            descripcion=descripcion,
            usuario_id=current_user.id
        )
        db.session.add(nueva_encuesta)
        db.session.commit()
        
        flash('Encuesta creada exitosamente. Ahora agrega preguntas.', 'success')
        return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=nueva_encuesta.id))
    
    return render_template('crear_encuesta.html')


@encuestas_bp.route('/encuesta/<int:encuesta_id>/agregar-pregunta', methods=['GET', 'POST'])
@login_required
def agregar_pregunta(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para modificar esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    if request.method == 'POST':
        texto = request.form.get('texto')
        tipo = request.form.get('tipo')
        requerida = request.form.get('requerida') == 'on'
        ayudante = request.form.get('ayudante')
        
        if not texto or not tipo:
            flash('El texto y tipo de pregunta son obligatorios', 'danger')
            return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta_id))
        
        nueva_pregunta = Pregunta(
            encuesta_id=encuesta_id,
            texto=texto,
            tipo=tipo,
            requerida=requerida,
            ayudante=ayudante,
            orden=Pregunta.query.filter_by(encuesta_id=encuesta_id).count() + 1
        )
        db.session.add(nueva_pregunta)
        db.session.commit()
        
        if tipo in ['opcion_unica', 'opcion_multiple', 'escala_likert', 'seleccion_si_no']:
            return redirect(url_for('encuestas.agregar_opciones', pregunta_id=nueva_pregunta.id))
        
        flash('Pregunta agregada exitosamente', 'success')
        return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta_id))
    
    return render_template('agregar_pregunta.html', encuesta=encuesta)


@encuestas_bp.route('/pregunta/<int:pregunta_id>/agregar-opciones', methods=['GET', 'POST'])
@login_required
def agregar_opciones(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    encuesta = pregunta.encuesta
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para modificar esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    if request.method == 'POST':
        opciones_texto = request.form.getlist('opcion_texto')
        opciones_valor = request.form.getlist('opcion_valor')
        
        if not opciones_texto or not opciones_texto[0]:
            flash('Debes agregar al menos una opción', 'danger')
            return redirect(url_for('encuestas.agregar_opciones', pregunta_id=pregunta_id))
        
        for i, texto in enumerate(opciones_texto):
            if texto.strip():
                opcion = Opcion(
                    pregunta_id=pregunta_id,
                    texto=texto.strip(),
                    valor=opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None,
                    orden=i + 1
                )
                db.session.add(opcion)
        
        db.session.commit()
        flash('Opciones agregadas exitosamente', 'success')
        return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id))
    
    return render_template('agregar_opciones.html', pregunta=pregunta, encuesta=encuesta)


@encuestas_bp.route('/mis-encuestas')
@login_required
def mis_encuestas():
    encuestas = Encuesta.query.filter_by(usuario_id=current_user.id).order_by(Encuesta.fecha_creacion.desc()).all()
    return render_template('mis_encuestas.html', encuestas=encuestas)


@encuestas_bp.route('/encuesta/<int:encuesta_id>/ver')
@login_required
def ver_encuesta(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    return render_template('ver_encuesta.html', encuesta=encuesta)


@encuestas_bp.route('/encuesta/<int:encuesta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_encuesta(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para eliminar esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    db.session.delete(encuesta)
    db.session.commit()
    flash('Encuesta eliminada exitosamente', 'success')
    return redirect(url_for('encuestas.mis_encuestas'))


@encuestas_bp.route('/pregunta/<int:pregunta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_pregunta(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    encuesta = pregunta.encuesta
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para eliminar esta pregunta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    db.session.delete(pregunta)
    db.session.commit()
    flash('Pregunta eliminada exitosamente', 'success')
    return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id))


@encuestas_bp.route('/encuesta/<int:encuesta_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_encuesta(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para editar esta encuesta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).count()
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado', 'activa')
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        
        if not titulo:
            flash('El título de la encuesta es obligatorio', 'danger')
            return redirect(request.url)
        
        if total_respuestas > 0:
            if not confirmar_eliminar:
                flash('⚠️ Debes confirmar que quieres eliminar las respuestas existentes para editar las preguntas', 'danger')
                return redirect(request.url)
            
            Respuesta.query.filter_by(encuesta_id=encuesta_id).delete()
            db.session.commit()
            flash(f'🗑️ Se eliminaron {total_respuestas} respuestas para poder editar la encuesta', 'warning')
        
        encuesta.titulo = titulo
        encuesta.descripcion = descripcion
        encuesta.estado = estado
        encuesta.fecha_actualizacion = datetime.utcnow()
        
        db.session.commit()
        flash('✅ Encuesta actualizada exitosamente', 'success')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    return render_template('editar_encuesta.html', 
                         encuesta=encuesta, 
                         preguntas=preguntas,
                         total_respuestas=total_respuestas)


@encuestas_bp.route('/pregunta/<int:pregunta_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pregunta(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    encuesta = pregunta.encuesta
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para editar esta pregunta', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta.id).count()
    
    if request.method == 'POST':
        texto = request.form.get('texto')
        tipo = request.form.get('tipo')
        requerida = request.form.get('requerida') == 'on'
        ayudante = request.form.get('ayudante')
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        
        if not texto or not tipo:
            flash('El texto y tipo de pregunta son obligatorios', 'danger')
            return redirect(request.url)
        
        if total_respuestas > 0:
            if not confirmar_eliminar:
                flash('⚠️ Debes confirmar que quieres eliminar las respuestas existentes', 'danger')
                return redirect(request.url)
            
            Respuesta.query.filter_by(encuesta_id=encuesta.id).delete()
            db.session.commit()
            flash(f'🗑️ Se eliminaron {total_respuestas} respuestas para poder editar la pregunta', 'warning')
        
        pregunta.texto = texto
        pregunta.tipo = tipo
        pregunta.requerida = requerida
        pregunta.ayudante = ayudante
        
        db.session.commit()
        flash('✅ Pregunta actualizada exitosamente', 'success')
        
        if pregunta.tiene_opciones():
            return redirect(url_for('encuestas.editar_opciones', pregunta_id=pregunta.id))
        
        return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id))
    
    return render_template('editar_pregunta.html', 
                         pregunta=pregunta, 
                         encuesta=encuesta,
                         total_respuestas=total_respuestas)


@encuestas_bp.route('/pregunta/<int:pregunta_id>/opciones/editar', methods=['GET', 'POST'])
@login_required
def editar_opciones(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    encuesta = pregunta.encuesta
    
    if encuesta.usuario_id != current_user.id:
        flash('No tienes permiso para editar estas opciones', 'danger')
        return redirect(url_for('encuestas.mis_encuestas'))
    
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta.id).count()
    opciones = Opcion.query.filter_by(pregunta_id=pregunta_id).order_by(Opcion.orden).all()
    
    if request.method == 'POST':
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        
        if total_respuestas > 0:
            if not confirmar_eliminar:
                flash('⚠️ Debes confirmar que quieres eliminar las respuestas existentes', 'danger')
                return redirect(request.url)
            
            Respuesta.query.filter_by(encuesta_id=encuesta.id).delete()
            db.session.commit()
            flash(f'🗑️ Se eliminaron {total_respuestas} respuestas para poder editar las opciones', 'warning')
        
        opciones_ids = request.form.getlist('opcion_id')
        opciones_texto = request.form.getlist('opcion_texto')
        opciones_valor = request.form.getlist('opcion_valor')
        opciones_eliminar = request.form.getlist('opcion_eliminar')
        
        for opcion_id in opciones_eliminar:
            opcion = Opcion.query.get(int(opcion_id))
            if opcion:
                db.session.delete(opcion)
        
        for i in range(len(opciones_texto)):
            if opciones_texto[i].strip():
                if i < len(opciones_ids) and opciones_ids[i]:
                    opcion = Opcion.query.get(int(opciones_ids[i]))
                    if opcion:
                        opcion.texto = opciones_texto[i].strip()
                        opcion.valor = opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None
                        opcion.orden = i + 1
                else:
                    nueva_opcion = Opcion(
                        pregunta_id=pregunta_id,
                        texto=opciones_texto[i].strip(),
                        valor=opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None,
                        orden=i + 1
                    )
                    db.session.add(nueva_opcion)
        
        db.session.commit()
        flash('✅ Opciones actualizadas exitosamente', 'success')
        return redirect(url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id))
    
    return render_template('editar_opciones.html', 
                         pregunta=pregunta, 
                         encuesta=encuesta, 
                         opciones=opciones,
                         total_respuestas=total_respuestas)


@encuestas_bp.route('/encuesta/<int:encuesta_id>/tiene-respuestas')
@login_required
def tiene_respuestas(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    
    if encuesta.usuario_id != current_user.id:
        return jsonify({'error': 'No tienes permiso'}), 403
    
    tiene = Respuesta.query.filter_by(encuesta_id=encuesta_id).first() is not None
    
    return jsonify({'tiene_respuestas': tiene})


# ============================================
# RUTAS AJAX - BÚSQUEDA EN SERVIDOR
# ============================================

@encuestas_bp.route('/buscar-encuestas')
@login_required
def buscar_encuestas():
    termino = request.args.get('q', '').strip()
    limite = request.args.get('limite', 20, type=int)
    pagina = request.args.get('pagina', 1, type=int)
    
    query = Encuesta.query.filter_by(usuario_id=current_user.id)
    
    if termino:
        query = query.filter(Encuesta.titulo.ilike(f'%{termino}%'))
    
    paginacion = query.order_by(Encuesta.fecha_creacion.desc()).paginate(
        page=pagina, per_page=limite, error_out=False
    )
    
    resultados = []
    for e in paginacion.items:
        resultados.append({
            'id': e.id,
            'titulo': e.titulo,
            'descripcion': e.descripcion,
            'estado': e.estado,
            'preguntas': len(e.preguntas),
            'respuestas': len(e.respuestas),
            'fecha': e.fecha_creacion.strftime('%d/%m/%Y')
        })
    
    return jsonify({
        'total': paginacion.total,
        'pagina': pagina,
        'total_paginas': paginacion.pages,
        'resultados': resultados
    })


@encuestas_bp.route('/encuestas-lista-ajax')
@login_required
def encuestas_lista_ajax():
    encuestas = Encuesta.query.filter_by(usuario_id=current_user.id).order_by(Encuesta.fecha_creacion.desc()).limit(20).all()
    
    data = []
    for e in encuestas:
        data.append({
            'id': e.id,
            'titulo': e.titulo,
            'preguntas': len(e.preguntas),
            'respuestas': len(e.respuestas),
            'estado': e.estado
        })
    
    return jsonify({'encuestas': data})


@encuestas_bp.route('/encuesta/<int:encuesta_id>/cargar-respuestas-modal')
@login_required
def cargar_respuestas_modal(encuesta_id):
    encuesta = Encuesta.query.get_or_404(encuesta_id)
    preguntas = Pregunta.query.filter_by(encuesta_id=encuesta_id).order_by(Pregunta.orden).all()
    
    total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).count()
    if total_respuestas > 0:
        identificadores = db.session.query(Respuesta.identificador_respuesta).filter_by(encuesta_id=encuesta_id).distinct().count()
    else:
        identificadores = 0
    
    return render_template('carga_respuestas_modal.html', 
                         encuesta=encuesta, 
                         preguntas=preguntas,
                         total_respuestas=total_respuestas,
                         identificadores=identificadores)


# ============================================
# RUTA AJAX: CARGAR RESPUESTAS (CON SOPORTE PARA "OTRO")
# ============================================

@encuestas_bp.route('/encuesta/<int:encuesta_id>/cargar-respuestas-ajax', methods=['POST'])
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
        
        # Leer archivo
        if archivo.filename.endswith('.csv'):
            df = pd.read_csv(archivo, encoding='utf-8', quotechar='"')
        else:
            df = pd.read_excel(archivo)
        
        df = df.where(pd.notnull(df), None)
        columnas_archivo = list(df.columns)
        
        # Obtener mapeo del formulario
        mapeo = {}
        for columna in columnas_archivo:
            pregunta_id = request.form.get(f'mapping_{columna}')
            if pregunta_id:
                mapeo[columna] = int(pregunta_id)
                print(f"🔗 Columna '{columna}' → Pregunta ID {pregunta_id}")
        
        if not mapeo:
            return jsonify({'success': False, 'message': 'Debes mapear al menos una columna a una pregunta'}), 400
        
        total_guardadas = 0
        errores = []
        
        for idx, row in df.iterrows():
            identificador = f"R{idx+1:04d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"\n📝 Procesando fila {idx+1}: {identificador}")
            
            for columna, pregunta_id in mapeo.items():
                pregunta = Pregunta.query.get(pregunta_id)
                if not pregunta:
                    print(f"  ❌ Pregunta ID {pregunta_id} no encontrada")
                    continue
                
                valor = row[columna]
                if valor is None or pd.isna(valor) or str(valor).strip() == '':
                    print(f"  ⏭️ Columna '{columna}': valor vacío")
                    continue
                
                valor_str = str(valor).strip()
                print(f"  🔍 Columna '{columna}' → '{valor_str}'")
                
                # ============================================
                # GUARDAR SEGÚN TIPO DE PREGUNTA
                # ============================================
                if pregunta.tipo == 'texto_libre':
                    nueva_respuesta = Respuesta(
                        encuesta_id=encuesta_id,
                        pregunta_id=pregunta.id,
                        texto_libre=valor_str,
                        identificador_respuesta=identificador
                    )
                    db.session.add(nueva_respuesta)
                    total_guardadas += 1
                    print(f"  ✅ Texto libre guardado: '{valor_str}'")
                else:
                    opciones = Opcion.query.filter_by(pregunta_id=pregunta.id).order_by(Opcion.orden).all()
                    print(f"  📋 Opciones disponibles: {[o.texto for o in opciones]}")
                    
                    # ============================================
                    # VERIFICAR SI ES OPCIÓN MÚLTIPLE
                    # ============================================
                    if pregunta.tipo == 'opcion_multiple':
                        respuesta = procesar_opcion_multiple(valor_str, pregunta.id, encuesta_id, identificador, opciones)
                        if respuesta:
                            db.session.add(respuesta)
                            total_guardadas += 1
                            print(f"  ✅ Opción múltiple guardada: '{valor_str}'")
                        else:
                            errores.append(f"Fila {idx+1}: No se encontraron opciones para '{valor_str}'")
                    else:
                        # ============================================
                        # OPCIÓN ÚNICA (CON SOPORTE PARA "OTRO")
                        # ============================================
                        respuesta = procesar_opcion_unica(valor_str, pregunta, opciones, encuesta_id, identificador)
                        
                        if respuesta:
                            db.session.add(respuesta)
                            total_guardadas += 1
                            if respuesta.opcion:
                                print(f"  ✅ Opción guardada: '{respuesta.opcion.texto}' (ID: {respuesta.opcion.id})")
                                if respuesta.texto_libre:
                                    print(f"  📝 Texto adicional: '{respuesta.texto_libre}'")
                            else:
                                print(f"  ✅ Respuesta procesada: '{valor_str}'")
                        else:
                            opciones_texto = [o.texto for o in opciones]
                            errores.append(f"Fila {idx+1}: No se encontró la opción '{valor_str}'. Opciones: {opciones_texto}")
                            print(f"  ❌ ERROR: No se encontró '{valor_str}'")
        
        db.session.commit()
        
        print(f"\n✅ Total guardadas: {total_guardadas}")
        
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
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# RUTAS AJAX - CRUD
# ============================================

@encuestas_bp.route('/crear-encuesta-ajax', methods=['POST'])
@login_required
def crear_encuesta_ajax():
    try:
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        
        if not titulo:
            return jsonify({'success': False, 'message': 'El título es obligatorio'}), 400
        
        nueva_encuesta = Encuesta(
            titulo=titulo,
            descripcion=descripcion,
            usuario_id=current_user.id
        )
        db.session.add(nueva_encuesta)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Encuesta creada exitosamente',
            'redirect': url_for('encuestas.agregar_pregunta', encuesta_id=nueva_encuesta.id)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/encuesta/<int:encuesta_id>/editar-ajax', methods=['POST'])
@login_required
def editar_encuesta_ajax(encuesta_id):
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado', 'activa')
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        
        if not titulo:
            return jsonify({'success': False, 'message': 'El título es obligatorio'}), 400
        
        total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta_id).count()
        
        if total_respuestas > 0 and not confirmar_eliminar:
            return jsonify({'success': False, 'message': 'Debes confirmar la eliminación de respuestas'}), 400
        
        if total_respuestas > 0 and confirmar_eliminar:
            Respuesta.query.filter_by(encuesta_id=encuesta_id).delete()
        
        encuesta.titulo = titulo
        encuesta.descripcion = descripcion
        encuesta.estado = estado
        encuesta.fecha_actualizacion = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Encuesta actualizada exitosamente',
            'redirect': url_for('encuestas.mis_encuestas')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/pregunta/<int:pregunta_id>/editar-ajax', methods=['POST'])
@login_required
def editar_pregunta_ajax(pregunta_id):
    try:
        pregunta = Pregunta.query.get_or_404(pregunta_id)
        encuesta = pregunta.encuesta
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        texto = request.form.get('texto')
        tipo = request.form.get('tipo')
        requerida = request.form.get('requerida') == 'on'
        ayudante = request.form.get('ayudante')
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        
        if not texto or not tipo:
            return jsonify({'success': False, 'message': 'Texto y tipo son obligatorios'}), 400
        
        total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta.id).count()
        
        if total_respuestas > 0 and not confirmar_eliminar:
            return jsonify({'success': False, 'message': 'Debes confirmar la eliminación de respuestas'}), 400
        
        if total_respuestas > 0 and confirmar_eliminar:
            Respuesta.query.filter_by(encuesta_id=encuesta.id).delete()
        
        pregunta.texto = texto
        pregunta.tipo = tipo
        pregunta.requerida = requerida
        pregunta.ayudante = ayudante
        
        db.session.commit()
        
        response = {
            'success': True,
            'message': '✅ Pregunta actualizada exitosamente'
        }
        
        if pregunta.tiene_opciones():
            response['redirect'] = url_for('encuestas.editar_opciones', pregunta_id=pregunta.id)
        else:
            response['redirect'] = url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/pregunta/<int:pregunta_id>/opciones/editar-ajax', methods=['POST'])
@login_required
def editar_opciones_ajax(pregunta_id):
    try:
        pregunta = Pregunta.query.get_or_404(pregunta_id)
        encuesta = pregunta.encuesta
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        confirmar_eliminar = request.form.get('confirmar_eliminar') == 'on'
        total_respuestas = Respuesta.query.filter_by(encuesta_id=encuesta.id).count()
        
        if total_respuestas > 0 and not confirmar_eliminar:
            return jsonify({'success': False, 'message': 'Debes confirmar la eliminación de respuestas'}), 400
        
        if total_respuestas > 0 and confirmar_eliminar:
            Respuesta.query.filter_by(encuesta_id=encuesta.id).delete()
        
        opciones_ids = request.form.getlist('opcion_id')
        opciones_texto = request.form.getlist('opcion_texto')
        opciones_valor = request.form.getlist('opcion_valor')
        opciones_eliminar = request.form.getlist('opcion_eliminar')
        
        for opcion_id in opciones_eliminar:
            opcion = Opcion.query.get(int(opcion_id))
            if opcion:
                db.session.delete(opcion)
        
        for i in range(len(opciones_texto)):
            if opciones_texto[i].strip():
                if i < len(opciones_ids) and opciones_ids[i]:
                    opcion = Opcion.query.get(int(opciones_ids[i]))
                    if opcion:
                        opcion.texto = opciones_texto[i].strip()
                        opcion.valor = opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None
                        opcion.orden = i + 1
                else:
                    nueva_opcion = Opcion(
                        pregunta_id=pregunta_id,
                        texto=opciones_texto[i].strip(),
                        valor=opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None,
                        orden=i + 1
                    )
                    db.session.add(nueva_opcion)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Opciones actualizadas exitosamente',
            'redirect': url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/encuesta/<int:encuesta_id>/eliminar-ajax', methods=['POST'])
@login_required
def eliminar_encuesta_ajax(encuesta_id):
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        db.session.delete(encuesta)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '✅ Encuesta eliminada exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/pregunta/<int:pregunta_id>/eliminar-ajax', methods=['POST'])
@login_required
def eliminar_pregunta_ajax(pregunta_id):
    try:
        pregunta = Pregunta.query.get_or_404(pregunta_id)
        encuesta = pregunta.encuesta
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        db.session.delete(pregunta)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '✅ Pregunta eliminada exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/encuesta/<int:encuesta_id>/agregar-pregunta-ajax', methods=['POST'])
@login_required
def agregar_pregunta_ajax(encuesta_id):
    try:
        encuesta = Encuesta.query.get_or_404(encuesta_id)
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        texto = request.form.get('texto')
        tipo = request.form.get('tipo')
        requerida = request.form.get('requerida') == 'on'
        ayudante = request.form.get('ayudante')
        
        if not texto or not tipo:
            return jsonify({'success': False, 'message': 'Texto y tipo son obligatorios'}), 400
        
        nueva_pregunta = Pregunta(
            encuesta_id=encuesta_id,
            texto=texto,
            tipo=tipo,
            requerida=requerida,
            ayudante=ayudante,
            orden=Pregunta.query.filter_by(encuesta_id=encuesta_id).count() + 1
        )
        db.session.add(nueva_pregunta)
        db.session.commit()
        
        response = {
            'success': True,
            'message': '✅ Pregunta agregada exitosamente'
        }
        
        if tipo in ['opcion_unica', 'opcion_multiple', 'escala_likert', 'seleccion_si_no']:
            response['redirect'] = url_for('encuestas.agregar_opciones', pregunta_id=nueva_pregunta.id)
        else:
            response['redirect'] = url_for('encuestas.agregar_pregunta', encuesta_id=encuesta_id)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@encuestas_bp.route('/pregunta/<int:pregunta_id>/agregar-opciones-ajax', methods=['POST'])
@login_required
def agregar_opciones_ajax(pregunta_id):
    try:
        pregunta = Pregunta.query.get_or_404(pregunta_id)
        encuesta = pregunta.encuesta
        
        if encuesta.usuario_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso'}), 403
        
        opciones_texto = request.form.getlist('opcion_texto')
        opciones_valor = request.form.getlist('opcion_valor')
        
        if not opciones_texto or not opciones_texto[0]:
            return jsonify({'success': False, 'message': 'Debes agregar al menos una opción'}), 400
        
        for i, texto in enumerate(opciones_texto):
            if texto.strip():
                opcion = Opcion(
                    pregunta_id=pregunta_id,
                    texto=texto.strip(),
                    valor=opciones_valor[i].strip() if i < len(opciones_valor) and opciones_valor[i] else None,
                    orden=i + 1
                )
                db.session.add(opcion)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Opciones agregadas exitosamente',
            'redirect': url_for('encuestas.agregar_pregunta', encuesta_id=encuesta.id)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500