# C:\gerenciador-eventos\app.py

from dotenv import load_dotenv
load_dotenv() # Isso é para seu ambiente local, no Render as variáveis serão definidas no painel
from flask import Flask, render_template, redirect, url_for, flash, request
# --- IMPORTAÇÕES ATUALIZADAS DE extensions.py ---
from extensions import db, login_manager, mail, migrate
# --- FIM DAS IMPORTAÇÕES ATUALIZADAS ---
from datetime import datetime
import click
import os
import json
import ast
from sqlalchemy import text
from sqlalchemy.inspection import inspect
# NOVO: Importar joinedload para eager-loading
from sqlalchemy.orm import joinedload

# --- NOVO: Flask-Admin Imports ---
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.security import generate_password_hash
# --- ATUALIZADO: Importar Attachment para o Flask-Admin (ADICIONADO AQUI) ---
from models import User, Role, Status, Category, TaskCategory, Group, Event, EventPermission, Attachment # Importar todos os modelos relevantes, incluindo EventPermission para a validação do form
# CORREÇÃO AQUI: Importar os nomes corretos dos Forms do forms.py (sem o prefixo 'Admin')
# --- ATUALIZADO: Importar AttachmentForm para o Flask-Admin (ADICIONADO AQUI) ---
from forms import UserForm, AdminRoleForm, GroupForm, CategoryForm, TaskCategoryForm, StatusForm, EventForm, AttachmentForm # Importar todos os forms necessários
from flask_admin.menu import MenuLink
# --- FIM: Flask-Admin Imports ---

def create_app():
    app = Flask(__name__)

    # --- Configuração da SECRET_KEY ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma_chave_secreta_muito_segura_e_longa_aqui_fallback_dev')
# --- Configuração do Banco de Dados ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///events.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Configurações para FLASK-MAIL ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'seu_email@example.com')

    # --- Configuração para uploads de áudio ---
    app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(app.instance_path, 'uploads', 'audio')
    os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)

    # --- NOVO: Configuração para uploads de anexos (ADICIONADO AQUI) ---
    app.config['UPLOAD_FOLDER_ATTACHMENTS'] = os.path.join(app.instance_path, 'uploads', 'attachments')
    os.makedirs(app.config['UPLOAD_FOLDER_ATTACHMENTS'], exist_ok=True)
    # --- FIM NOVO ---

    # --- Inicializa as extensões com o app (DEPOIS que o objeto 'app' é criado) ---
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = "strong"

    # Habilita a extensão 'do' do Jinja2
    app.jinja_env.add_extension('jinja2.ext.do')

    # Context processor para injetar o ano atual em todos os templates
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    # CORREÇÃO AQUI: Eager-load o role_obj do User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.options(joinedload(User.role_obj)).get(int(user_id))

    @app.context_processor
    def inject_user_role():
        if current_user.is_authenticated:
            return {'current_user_role': current_user.role_obj.name if current_user.role_obj else 'Guest'}
        return {'current_user_role': 'Guest'}

    ### INÍCIO: Configuração do Flask-Admin ###

    class MyAdminIndexView(AdminIndexView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def _handle_view(self, name, **kwargs):
            if not self.is_accessible():
                if not current_user.is_authenticated:
                    flash('Por favor, faça login para acessar o painel de administração.', 'warning')
                    return redirect(url_for('main.login', next=request.url))
                else:
                    flash('Você não tem permissão para acessar o painel de administração.', 'danger')
                    return redirect(url_for('main.home'))

    class MyModelView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def _handle_view(self, name, **kwargs):
            if not self.is_accessible():
                if not current_user.is_authenticated:
                    flash('Por favor, faça login para acessar esta seção do painel de administração.', 'warning')
                    return redirect(url_for('main.login', next=request.url))
                else:
                    flash('Você não tem permissão para acessar esta seção do painel de administração.', 'danger')
                    return redirect(url_for('main.home'))

    class UserAdminView(MyModelView):
        form = UserForm

        column_list = ('id', 'username', 'email', 'role_obj', 'is_active', 'created_at', 'last_login')
        column_labels = dict(role_obj='Papel', is_active='Ativo')
        column_searchable_list = ('username', 'email')
        column_filters = ('role_obj.name',)

        form_columns = ['username', 'email', 'password', 'confirm_password', 'role_obj']

        def get_form(self):
            class UserAdminFormWrapper(self.form):
                def __init__(self, formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs):
                    is_new_user = (obj is None)
                    super().__init__(
                        formdata=formdata,
                        obj=obj,
                        prefix=prefix,
                        data=data,
                        meta=meta,
                        is_new_user=is_new_user,
                        original_username=obj.username if obj else None,
                        original_email=obj.email if obj else None,
                        **kwargs
                    )
            return UserAdminFormWrapper

        def on_model_change(self, form, model, is_created):
            if form.password.data:
                model.set_password(form.password.data)

            if form.role_obj.data:
                model.role_id = form.role_obj.data.id
            else:
                model.role_id = None

    class RoleAdminView(MyModelView):
        form = AdminRoleForm

        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome do Papel', description='Descrição')
        column_searchable_list = ('name', 'description')

        form_excluded_columns = ['users']

        # --- ATUALIZADO: Adicionar novas permissões de anexo (ADICIONADO AQUI) ---
        form_columns = ('name', 'description', 'can_view_event', 'can_edit_event', 'can_manage_permissions',
                        'can_create_event', 'can_create_task', 'can_edit_task', 'can_delete_task',
                        'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio',
                        'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments',
                        'can_upload_attachments', 'can_manage_attachments') # Adicionado can_upload_attachments e can_manage_attachments aqui
        # --- FIM ATUALIZADO ---

        def on_model_change(self, form, model, is_created):
            existing_role = Role.query.filter_by(name=form.name.data).first()
            if existing_role and existing_role.id != model.id:
                raise ValueError('Este nome de papel já existe. Por favor, escolha outro.')

    class GroupAdminView(MyModelView):
        form = GroupForm

        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome do Grupo', description='Descrição')
        column_searchable_list = ('name', 'description')

        form_excluded_columns = ['members']

        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            existing_group = Group.query.filter_by(name=form.name.data).first()
            if existing_group and existing_group.id != model.id:
                raise ValueError('Este nome de grupo já existe. Por favor, escolha outro.')

    # View Personalizada para Category
    class CategoryAdminView(MyModelView):
        form = CategoryForm
        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome', description='Descrição')
        column_searchable_list = ('name',)
        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            # Validação para garantir que o nome da categoria é único
            existing_category = Category.query.filter_by(name=form.name.data).first()
            if existing_category and existing_category.id != model.id:
                raise ValueError('Este nome de categoria já existe. Por favor, escolha outro.')

    # View Personalizada para TaskCategory
    class TaskCategoryAdminView(MyModelView):
        form = TaskCategoryForm
        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome', description='Descrição')
        column_searchable_list = ('name',)
        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            # Validação para garantir que o nome da categoria de tarefa é único
            existing_task_category = TaskCategory.query.filter_by(name=form.name.data).first()
            if existing_task_category and existing_task_category.id != model.id:
                raise ValueError('Este nome de categoria de tarefa já existe. Por favor, escolha outro.')

    # View Personalizada para Status
    class StatusAdminView(MyModelView):
        form = StatusForm
        column_list = ('id', 'name', 'type', 'description')
        column_labels = dict(name='Nome', type='Tipo', description='Descrição')
        column_searchable_list = ('name', 'type')
        form_columns = ('name', 'type', 'description')

        def on_model_change(self, form, model, is_created):
            # Validação para garantir que a combinação nome e tipo do status é única
            existing_status = Status.query.filter_by(name=form.name.data, type=form.type.data).first()
            if existing_status and existing_status.id != model.id:
                raise ValueError(f"Um status com o nome '{form.name.data}' e tipo '{form.type.data}' já existe. Por favor, escolha outro nome ou tipo.")

    # View Personalizada para Event
    class EventAdminView(MyModelView):
        form = EventForm
        column_list = ('id', 'title', 'due_date', 'author', 'category', 'status', 'location')
        column_labels = dict(author='Autor', category='Categoria', status='Status')
        column_searchable_list = ('title', 'location', 'description')
        column_filters = ('author.username', 'category.name', 'status.name')

        # Define quais colunas serão mostradas no formulário de criação/edição
        form_columns = [
            'title', 'description', 'due_date', 'end_date', 'location',
            'author', 'category', 'status'
        ]

        # Ordenar eventos por 'due_date' (data de início) em ordem crescente por padrão
        column_default_sort = ('due_date', False)

        def on_model_change(self, form, model, is_created):
            # O autor, categoria e status são objetos selecionados, precisamos atribuir os IDs
            model.author_id = form.author.data.id
            model.category_id = form.category.data.id if form.category.data else None
            model.status_id = form.status.data.id
            # O restante dos campos são atribuídos automaticamente pelo form.populate_obj(model)

    # --- NOVO: Classe para gerenciar Anexos no Flask-Admin (ADICIONADO AQUI) ---
    class AttachmentAdminView(MyModelView):
        form = AttachmentForm # Usará o formulário de anexo se você criar um
        column_list = ('id', 'task', 'filename', 'unique_filename', 'mimetype', 'filesize', 'uploader', 'upload_timestamp')
        column_labels = dict(task='Tarefa', filename='Nome Original', unique_filename='Nome no Servidor',
                             mimetype='Tipo', filesize='Tamanho', uploader='Feito por', upload_timestamp='Data Upload')
        column_searchable_list = ('filename', 'unique_filename', 'mimetype')
        column_filters = ('task.title', 'uploader.username', 'mimetype')

        # Para que o admin possa ver o arquivo real, pode-se adicionar um link
        def _attachment_download_link(view, context, model, name):
            if not model.unique_filename:
                return ''
            return f'<a href="{url_for("main.download_attachment", attachment_id=model.id)}" target="_blank">Download</a>'
        column_formatters = {
            'filename': _attachment_download_link
        }

        # Sobrescrever o método de exclusão para remover o arquivo do sistema de arquivos
        def on_model_delete(self, model):
            file_path = os.path.join(app.config['UPLOAD_FOLDER_ATTACHMENTS'], model.unique_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f"Anexo '{model.filename}' e arquivo excluídos com sucesso.", 'success')

        # Desabilitar criação e edição via admin, pois o upload é feito via rota de tarefa.
        # O administrador poderá apenas visualizar e deletar.
        can_create = False
        can_edit = False
    # --- FIM NOVO ---


    # CORREÇÃO AQUI para o "Página Não Encontrada" do Flask-Admin:
    # A AdminIndexView é a página inicial DO PAINEL ADMIN.
    # O link "Ir para Home do Site" é para a home da sua APLICAÇÃO.
    admin = Admin(app, name='Gerenciador de Eventos', template_mode='bootstrap4',
                  index_view=MyAdminIndexView(name='Início do Admin')) # Nome para o índice do próprio painel admin
    # Adiciona um link no menu do Admin para a home page da aplicação principal
    admin.add_link(MenuLink(name='Ir para Home do Site', url='/', target="_top", icon_type='fa', icon_value='fa-home'))

    admin.add_view(UserAdminView(User, db.session, name='Usuários', category='Administração'))
    admin.add_view(RoleAdminView(Role, db.session, name='Papéis', category='Administração'))
    admin.add_view(GroupAdminView(Group, db.session, name='Grupos', category='Administração'))
    admin.add_view(CategoryAdminView(Category, db.session, name='Categorias de Evento', category='Configurações'))
    admin.add_view(TaskCategoryAdminView(TaskCategory, db.session, name='Categorias de Tarefa', category='Configurações'))
    admin.add_view(StatusAdminView(Status, db.session, name='Status', category='Configurações'))
    admin.add_view(EventAdminView(Event, db.session, name='Eventos')) # O modelo Event agora usa EventAdminView
    # --- NOVO: Adicionar a View de Anexos ao Flask-Admin (ADICIONADO AQUI) ---
    admin.add_view(AttachmentAdminView(Attachment, db.session, name='Anexos', category='Configurações'))
    # --- FIM NOVO ---


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

    app.jinja_env.filters['from_json_and_extract_value'] = from_json_and_extract_value


    def format_diff_values(old_raw_value, new_raw_value):
        """
        Compara dois valores (strings JSON/Python literal ou simples) e retorna
        uma lista de strings descrevendo apenas as diferenças.
        """
        diffs = []

        def parse_value(value):
            if not isinstance(value, str):
                return value
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value

        old_data = parse_value(old_raw_value)
        new_data = parse_value(new_raw_value)

        if isinstance(old_data, dict) and isinstance(new_data, dict):
            all_keys = sorted(list(set(old_data.keys()) | set(new_data.keys())))
            for key in all_keys:
                old_val = old_data.get(key)
                new_val = new_data.get(key)

                formatted_key = str(key).replace('_', ' ').title()

                def format_single_value(value):
                    s_value = str(value)
                    if isinstance(value, str):
                        try:
                            dt_obj = datetime.fromisoformat(s_value)
                            return dt_obj.strftime('%d/%m/%Y %H:%M:%S')
                        except ValueError:
                            pass
                    return s_value

                formatted_old_val = format_single_value(old_val)
                formatted_new_val = format_single_value(new_val)

                if old_val != new_val:
                    if old_val is None:
                        diffs.append(f"{formatted_key}: Adicionado '{formatted_new_val}'")
                    elif new_val is None:
                        diffs.append(f"{formatted_key}: Removido (Era '{formatted_old_val}')")
                    else:
                        diffs.append(f"{formatted_key}: De '{formatted_old_val}' para '{formatted_new_val}'")
        elif old_raw_value != new_raw_value:
            diffs.append(f"Valor alterado de: '{str(old_data)}' para: '{str(new_data)}'")

        return diffs if diffs else ["Nenhuma alteração detectada nos detalhes."]

    app.jinja_env.filters['format_diff_values'] = format_diff_values

    from routes import main as main_blueprint
    # from admin_routes import admin_bp # REMOVIDO: Já não temos este arquivo

    app.register_blueprint(main_blueprint)
    # app.register_blueprint(admin_bp) # REMOVIDO: Já não temos este arquivo

    @app.cli.command('create-db')
    def create_db_command():
        """Cria as tabelas do banco de dados, papéis padrão e um usuário administrador inicial."""
        with app.app_context():
            click.echo("Verificando e criando papéis padrão (Admin, User, Project Manager)...")
            default_roles_data = {
                'Admin': 'Administrador do sistema com acesso total.',
                'User': 'Usuário padrão com acesso básico.',
                'Project Manager': 'Gerente de projeto com permissões elevadas.'
            }
            for name, description in default_roles_data.items():
                if not Role.query.filter_by(name=name).first():
                    role = Role(name=name, description=description)
                    db.session.add(role)
                    click.echo(f"Papel '{name}' criado.")
                else:
                    click.echo(f"Papel '{name}' já existe.")
            db.session.commit()
            click.echo("Papéis verificados/criados.")

            click.echo("Verificando e criando status padrão de evento (Ativo)...")
            if not Status.query.filter_by(name='Ativo', type='event').first():
                ativo_event_status = Status(name='Ativo', type='event', description='Evento em andamento ou futuro.')
                db.session.add(ativo_event_status)
                click.echo("Status de evento 'Ativo' criado.")
            else:
                click.echo("Status de evento 'Ativo' já existe.")

            if not Status.query.filter_by(name='Pendente', type='task').first():
                pendente_task_status = Status(name='Pendente', type='task', description='Tarefa aguardando início ou atribuição.')
                db.session.add(pendente_task_status)
                click.echo("Status de tarefa 'Pendente' criado.")
            else:
                click.echo("Status de tarefa 'Pendente' já existe.")

            if not Status.query.filter_by(name='Concluída', type='task').first():
                concluida_task_status = Status(name='Concluída', type='task', description='Tarefa concluída com sucesso.')
                db.session.add(concluida_task_status)
                click.echo("Status de tarefa 'Concluída' criado.")
            else:
                click.echo("Status de tarefa 'Concluída' já existe.")

            db.session.commit()
            click.echo("Status de evento/tarefa verificado/criado.")

            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                if User.query.filter_by(username='admin_test').first() is None:
                    click.echo("Criando usuário administrador padrão 'admin_test'...")
                    admin_user = User(username='admin_test', email='admin@example.com', role_obj=admin_role)
                    admin_user.set_password('suasenhaadmin123')
                    db.session.add(admin_user)
                    db.session.commit()
                    click.echo("Usuário 'admin_test' criado com sucesso!")
                else:
                    click.echo("Usuário administrador 'admin_test' já existe.")
            else:
                click.echo("Erro: Papel 'Admin' não encontrado. Não foi possível criar o usuário administrador.")

            click.echo('Operação create-db concluída.')

    @app.cli.command("reset-db")
    def reset_db_command():
        """Apaga todas as tabelas e limpa o histórico do Alembic."""
        if click.confirm("ATENÇÃO: Esta operação irá apagar TODAS as tabelas do seu banco de dados e resetar o histórico de migrações. Deseja continuar? (Esta ação é IRREVERSÍVEL!)"):
            with app.app_context():
                print("Iniciando reset do banco de dados...")

                db.drop_all()
                print("Tabelas definidas nos modelos foram apagadas.")

                with db.engine.connect() as connection:
                    inspector = inspect(db.engine)
                    table_names = inspector.get_table_names()
                    if 'alembic_version' in table_names:
                        try:
                            # CORREÇÃO PARA SQLITE: CASCADE não é suportado diretamente
                            connection.execute(text("DROP TABLE alembic_version;"))
                            connection.commit()
                            print("Tabela 'alembic_version' apagada.")
                        except Exception as e:
                            print(f"Erro ao tentar apagar a tabela 'alembic_version': {e}. Pode ser que já tenha sido apagada ou não existisse.")
                            connection.rollback()
                    else:
                        print("Tabela 'alembic_version' não encontrada ou já apagada.")

                print("Banco de dados limpo com sucesso!")
                print("Próximos passos:")
                print("1. Execute 'flask db upgrade' para recriar todas as tabelas.")
                print("2. Execute 'flask create-db' para criar os papéis e o usuário administrador inicial.")
        else:
            print("Operação de reset de banco de dados cancelada.")

    @app.cli.command("list-tables")
    def list_tables_command():
        """Lista todas as tabelas atualmente no banco de dados."""
        with app.app_context():
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            if table_names:
                click.echo("Tabelas existentes no banco de dados:")
                for table in sorted(table_names):
                    click.echo(f"- {table}")
            else:
                click.echo("Nenhuma tabela encontrada no banco de dados.")

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)