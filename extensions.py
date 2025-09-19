# C:\gerenciador-eventos\extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate # Adicionando a importação do Flask-Migrate

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate() # Adicionando a instância do Flask-Migrate