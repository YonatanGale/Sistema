from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Encuesta, Pregunta, Opcion
from datetime import datetime

encuestas_bp = Blueprint('encuestas', __name__)

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