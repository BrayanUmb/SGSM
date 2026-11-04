"""
SGSM - Sistema de Gestión de Salud Médica
Base de datos y configuración de la aplicación Flask
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base

# Configuración de la base de datos
Base = declarative_base()
db = SQLAlchemy(model_class=Base)


def create_app(config_name: str = "development") -> Flask:
    """
    Factory para crear la aplicación Flask
    
    Args:
        config_name: Nombre de la configuración ('development', 'testing', 'production')
    
    Returns:
        Aplicación Flask configurada
    """
    app = Flask(__name__)
    
    # Configuración según el entorno
    if config_name == "testing":
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
    elif config_name == "production":
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL", "sqlite:///sgsm_production.db"
        )
    else:  # development
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sgsm_development.db"
    
    app.config["SQLALCHEMY_ECHO"] = False
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Inicializar extensiones
    db.init_app(app)
    
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
    
    return app
