from flask_login import UserMixin
from app import db
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    encuestas = db.relationship('Encuesta', backref='creador', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Encuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    estado = db.Column(db.String(20), default='activa')
    
    preguntas = db.relationship('Pregunta', backref='encuesta', lazy=True, cascade='all, delete-orphan')
    respuestas = db.relationship('Respuesta', backref='encuesta', lazy=True, cascade='all, delete-orphan')
    
    def total_preguntas(self):
        return len(self.preguntas)
    
    def total_respuestas(self):
        return len(self.respuestas)
    
    def __repr__(self):
        return f'<Encuesta {self.titulo}>'


class Pregunta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encuesta_id = db.Column(db.Integer, db.ForeignKey('encuesta.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    orden = db.Column(db.Integer, default=0)
    requerida = db.Column(db.Boolean, default=True)
    ayudante = db.Column(db.String(200))
    
    opciones = db.relationship('Opcion', backref='pregunta', lazy=True, cascade='all, delete-orphan')
    respuestas = db.relationship('Respuesta', backref='pregunta', lazy=True, cascade='all, delete-orphan')
    
    def tiene_opciones(self):
        return self.tipo in ['opcion_unica', 'opcion_multiple', 'escala_likert', 'seleccion_si_no']
    
    def __repr__(self):
        return f'<Pregunta {self.texto[:50]}>'


class Opcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=False)
    texto = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.String(50))
    orden = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Opcion {self.texto}>'


class Respuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encuesta_id = db.Column(db.Integer, db.ForeignKey('encuesta.id'), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=False)
    opcion_id = db.Column(db.Integer, db.ForeignKey('opcion.id'), nullable=True)
    texto_libre = db.Column(db.Text, nullable=True)
    fecha_respuesta = db.Column(db.DateTime, default=datetime.utcnow)
    identificador_respuesta = db.Column(db.String(50))
    
    opcion = db.relationship('Opcion', backref='respuestas', lazy=True)
    
    def __repr__(self):
        return f'<Respuesta {self.id}>'