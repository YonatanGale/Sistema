from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui-cambiala'
    
    # CONFIGURACIÓN PARA MYSQL CON PHPMyAdmin
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/sistema_encuestas'
    # Si tienes contraseña: mysql+pymysql://root:tu_contraseña@localhost/sistema_encuestas
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    with app.app_context():
        db.create_all()
        print("✅ Base de datos conectada correctamente")
    
    return app