from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail # NOVA IMPORTAÇÃO

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail() # NOVA INSTÂNCIA