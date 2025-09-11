# app.py

from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from extensions import db, login_manager, mail
from datetime import datetime
from flask_migrate import Migrate
import click
import os
import json
import ast

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_segura_e_longa_aqui' # Use uma chave segura e complexa
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- LINHAS NOVAS PARA DEPURAR A SECRET_KEY ---
    print(f"DEBUG: Tipo da SECRET_KEY: {type(app.config['SECRET_KEY'])}")
    print(f"DEBUG: Valor da SECRET_KEY: {app.config['SECRET_KEY']}")
    # --- FIM DAS LINHAS DE DEPURACÃO ---

    # --- NOVAS CONFIGURAÇÕES PARA FLASK-MAIL ---
    app.config['MAIL_SERVER'] = 'smtp.googlemail.com' # Exemplo para Gmail
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER') # Use variável de ambiente
    app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS') # Use variável de ambiente
    app.config['MAIL_DEFAULT_SENDER'] = 'seu_email@example.com' # Seu e-mail padrão


    # --- NOVO: Configuração para uploads de áudio ---
    app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(app.instance_path, 'uploads', 'audio')
    os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)
    # --- FIM NOVO: Configuração para uploads de áudio ---

    # Inicializa as extensões com o app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app) # NOVA INICIALIZAÇÃO PARA FLASK-MAIL
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    # Habilita a extensão 'do' do Jinja2 para permitir atribuição de variáveis dentro de templates
    app.jinja_env.add_extension('jinja2.ext.do')

    # Context processor para injetar o ano atual em todos os templates
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    # =========================================================================
    # FILTRO JINJA2 ORIGINAL (PARA CASOS DE CRIAÇÃO)
    # =========================================================================
    def from_json_and_extract_value(input_string):
        """
        Função para processar strings JSON (ou literais Python como dict/list)
        e extrair/formatar valores de forma inteligente para exibição.
        Sempre retorna uma LISTA de strings formatadas para melhor leitura.
        """
        if not isinstance(input_string, str):
            return [str(input_string)] if input_string is not None else [""]

        parsed_data = None
        try:
            parsed_data = ast.literal_eval(input_string)
        except (ValueError, SyntaxError):
            try:
                parsed_data = json.loads(input_string)
            except (json.JSONDecodeError, TypeError):
                return [input_string]

        if isinstance(parsed_data, dict):
            formatted_items = []
            for k, v in parsed_data.items():
                formatted_key = str(k).replace('_', ' ').title()
                formatted_value = str(v)
                if isinstance(v, str):
                    try:
                        dt_obj = datetime.fromisoformat(v)
                        formatted_value = dt_obj.strftime('%d/%m/%Y %H:%M:%S')
                    except ValueError:
                        pass
                formatted_items.append(f"{formatted_key}: {formatted_value}")
            return formatted_items
        elif isinstance(parsed_data, list):
            return [str(item) for item in parsed_data]
        else:
            return [str(parsed_data)]

    # REGISTRA O FILTRO
    app.jinja_env.filters['from_json_and_extract_value'] = from_json_and_extract_value
    # =========================================================================
    # FIM DO FILTRO ORIGINAL
    # =========================================================================


    # =========================================================================
    # NOVO FILTRO JINJA2: format_diff_values (PARA EXIBIR APENAS AS DIFERENÇAS)
    # =========================================================================
    def format_diff_values(old_raw_value, new_raw_value):
        """
        Compara dois valores (strings JSON/Python literal ou simples) e retorna
        uma lista de strings descrevendo apenas as diferenças.
        """
        diffs = []

        # Helper para tentar parsear a string (JSON ou literal Python)
        def parse_value(value):
            if not isinstance(value, str):
                return value # Já é um objeto, retorna direto
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value # Não é JSON nem literal, retorna a string original

        old_data = parse_value(old_raw_value)
        new_data = parse_value(new_raw_value)

        # Caso mais comum: ambos são dicionários (alteração de vários campos)
        if isinstance(old_data, dict) and isinstance(new_data, dict):
            all_keys = sorted(list(set(old_data.keys()) | set(new_data.keys())))
            for key in all_keys:
                old_val = old_data.get(key)
                new_val = new_data.get(key)

                # Formata a chave para exibição
                formatted_key = str(key).replace('_', ' ').title()

                # Helper para formatar valores (incluindo datas)
                def format_single_value(value):
                    s_value = str(value)
                    if isinstance(value, str):
                        try:
                            dt_obj = datetime.fromisoformat(value)
                            return dt_obj.strftime('%d/%m/%Y %H:%M:%S')
                        except ValueError:
                            pass
                    return s_value

                formatted_old_val = format_single_value(old_val)
                formatted_new_val = format_single_value(new_val)

                if old_val != new_val: # Apenas se houver diferença
                    if old_val is None: # Campo adicionado
                        diffs.append(f"{formatted_key}: Adicionado '{formatted_new_val}'")
                    elif new_val is None: # Campo removido (menos comum em atualizações)
                        diffs.append(f"{formatted_key}: Removido (Era '{formatted_old_val}')")
                    else: # Campo alterado
                        diffs.append(f"{formatted_key}: De '{formatted_old_val}' para '{formatted_new_val}'")
        # Caso geral: se não for dicionário (ex: string simples) ou falhou no parsing
        elif old_raw_value != new_raw_value:
            # Tenta formatar os valores para evitar JSON bruto, mas como string
            diffs.append(f"Valor alterado de: '{str(old_data)}' para: '{str(new_data)}'")
        
        return diffs if diffs else ["Nenhuma alteração detectada nos detalhes."]

    # REGISTRA O NOVO FILTRO
    app.jinja_env.filters['format_diff_values'] = format_diff_values
    # =========================================================================
    # FIM DO NOVO FILTRO
    # =========================================================================

    # --- NOVO: Importa os modelos após db.init_app(app) ---
    from models import User, Group, Event, EventStatus, TaskStatus, Category, EventPermission

    # --- NOVO: Importa e Registra os Blueprints ---
    from routes import main as main_blueprint
    from admin_routes import admin_bp

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_bp)

    # NOVO: Comando CLI personalizado para criar o banco de dados e usuário admin
    @app.cli.command('create-db')
    def create_db_command():
        """Creates the database tables and an initial admin user."""
        with app.app_context():
            db.create_all()
            if User.query.count() == 0:
                click.echo("Criando usuário administrador padrão...")
                admin_user = User(username='admin', email='admin@example.com', role='admin')
                admin_user.set_password('adminpassword')
                db.session.add(admin_user)
                db.session.commit()
                click.echo("Usuário 'admin' criado com sucesso!")
            click.echo('Database tables created.')

    return app

# IMPORTANTE: Criamos a instância do app aqui FORA da função 'if __name__ == "__main__":'
app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, port=5000)