# gerenciador-eventos/app/__init__.py

from flask import Flask
from .extensions import db, login_manager
from datetime import datetime
from flask_migrate import Migrate
import click
import os
import json # Certifique-se que esta linha está presente!

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_segura_e_longa_aqui' # Use uma chave segura e complexa
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- NOVO: Configuração para uploads de áudio ---
    app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(app.instance_path, 'uploads', 'audio')
    os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)
    # --- FIM NOVO: Configuração para uploads de áudio ---

    # Inicializa as extensões com o app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # Nome do endpoint para a rota de login
    login_manager.login_message_category = 'info'

    app.jinja_env.add_extension('jinja2.ext.do')

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    # =========================================================================
    # ESTE É O BLOCO DO FILTRO JINJA2 - AGORA COM REGISTRO EXPLÍCITO
    # =========================================================================
    def from_json_and_extract_value(json_string):
        """
        Função para processar strings JSON e extrair valores de forma inteligente
        para exibição no histórico.
        """
        try:
            # Tenta carregar a string como JSON
            data = json.loads(json_string)
            
            # Se for um dicionário com um único par chave-valor, retorna apenas o valor
            if isinstance(data, dict) and len(data) == 1:
                return next(iter(data.values()))
            
            # Se for uma lista de strings, tenta uni-las
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return ", ".join(data)
            
            # Para outros tipos de JSON (int, float, bool, dicionários maiores), converte para string
            return str(data) 
        except (json.JSONDecodeError, TypeError):
            # Se não for um JSON válido ou houver outro erro, retorna a string original
            return json_string

    # REGISTRA O FILTRO DIRETAMENTE NO AMBIENTE JINJA2
    app.jinja_env.filters['from_json_and_extract_value'] = from_json_and_extract_value
    # =========================================================================
    # FIM DO BLOCO DO FILTRO JINJA2
    # =========================================================================

    # --- NOVO: Importa os modelos após db.init_app(app) ---
    from .models import User, Group, Event, EventStatus, TaskStatus, Category, EventPermission

    # --- NOVO: Importa e Registra os Blueprints ---
    from .routes import main as main_blueprint
    from .admin_routes import admin_bp

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_bp)

    # NOVO: Comando CLI personalizado para criar o banco de dados e usuário admin
    @app.cli.command('create-db')
    def create_db_command():
        """Creates the database tables and an initial admin user."""
        with app.app_context():
            db.create_all() # ISTO É O QUE CRIA TODAS AS TABELAS
            if User.query.count() == 0:
                click.echo("Criando usuário administrador padrão...")
                admin_user = User(username='admin', email='admin@example.com', role='admin')
                admin_user.set_password('adminpassword') # Mude 'adminpassword' para uma senha forte
                db.session.add(admin_user)
                db.session.commit()
                click.echo("Usuário 'admin' criado com sucesso!")
            click.echo('Database tables created.')

    return app

# IMPORTANTE: Criamos a instância do app aqui FORA da função 'if __name__ == "__main__":'
# para que o Flask CLI (e o Flask-Migrate) possam encontrá-lo.
# Não execute o app.run() aqui, pois o 'run.py' é quem fará isso.
app = create_app()

# NOVO: Inicializa o Flask-Migrate APÓS o app e o db estarem definidos.
migrate = Migrate(app, db)