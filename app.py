# C:\\\gerenciador-eventos\\\app.py

from dotenv import load_dotenv
# Carrega variáveis do arquivo .env para desenvolvimento local.
# No Render, as variáveis de ambiente serão definidas no painel do serviço.
load_dotenv() 

from flask import Flask, render_template, redirect, url_for, flash, request
# Importações das extensões Flask que você configurou em extensions.py
from extensions import db, login_manager, mail, migrate
from datetime import datetime
import click # Para comandos da CLI (Command Line Interface) do Flask
import os
import json
import ast # Para parsear literais Python de forma segura
from sqlalchemy import text
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import joinedload # Para otimização de carregamento de relacionamentos

# --- Flask-Admin Imports ---
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.security import generate_password_hash
# Importa todos os modelos relevantes para o Flask-Admin
# IMPORTANTE: Garanta que Notification está aqui
from models import User, Role, Status, Category, TaskCategory, Group, Event, EventPermission, Attachment, Notification 
# Importa todos os forms necessários do forms.py
from forms import UserForm, AdminRoleForm, GroupForm, CategoryForm, TaskCategoryForm, StatusForm, EventForm, AttachmentForm 
from flask_admin.menu import MenuLink
# --- Fim Flask-Admin Imports ---

import re # <-- MANTENHA ESTA LINHA: IMPORTADO PARA O FILTRO REGEX PERSONALIZADO

def create_app():
    app = Flask(__name__)

    # --- Configuração da SECRET_KEY ---
    # Busca a SECRET_KEY das variáveis de ambiente ou usa um fallback para desenvolvimento.
    # **É CRÍTICO que esta chave seja gerada de forma segura e mantida secreta em produção.**
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma_chave_secreta_muito_segura_e_longa_aqui_fallback_dev')
# --- Configuração do Banco de Dados ---
    # Busca a URL do banco de dados das variáveis de ambiente (ex: no Render) ou usa um SQLite local.
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///events.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Configurações para FLASK-MAIL ---
    # Busca as configurações de e-mail das variáveis de ambiente.
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587)) # Converte para inteiro
    # Converte string 'True'/'False' para booleano
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'seu_email@example.com')
# --- DEBUG: Verifica se as variáveis de ambiente de email estão sendo lidas ---
    print(f"DEBUG MAIL_SERVER: {app.config['MAIL_SERVER']}")
    print(f"DEBUG MAIL_PORT: {app.config['MAIL_PORT']}")
    print(f"DEBUG MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
    print(f"DEBUG MAIL_USERNAME (primeiras 3 letras): {app.config['MAIL_USERNAME'][:3] if app.config['MAIL_USERNAME'] else 'N/A'}")
    print(f"DEBUG MAIL_PASSWORD (primeiras 3 letras): {app.config['MAIL_PASSWORD'][:3] if app.config['MAIL_PASSWORD'] else 'N/A'}")
    print(f"DEBUG MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")
    # --- FIM DEBUG ---

    # --- Configuração para uploads de áudio ---
    # Cria a pasta de uploads se não existir, garantindo que seja absoluta.
    app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(app.instance_path, 'uploads', 'audio')
    os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)

    # --- Configuração para uploads de anexos ---
    # Cria a pasta de uploads se não existir.
    app.config['UPLOAD_FOLDER_ATTACHMENTS'] = os.path.join(app.instance_path, 'uploads', 'attachments')
    os.makedirs(app.config['UPLOAD_FOLDER_ATTACHMENTS'], exist_ok=True)

    # --- Inicializa as extensões com o app ---
    # É fundamental que isso aconteça APÓS a criação do objeto 'app' e suas configurações.
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Configuração do Flask-Login
    login_manager.login_view = 'main.login' # Define a rota para redirecionar usuários não logados.
    login_manager.login_message_category = 'info' # Categoria da mensagem flash para login requerido.
    login_manager.session_protection = "strong" # Proteção de sessão para evitar sequestro de sessão.

    # Habilita a extensão 'do' do Jinja2 para melhor controle de fluxo em templates.
    app.jinja_env.add_extension('jinja2.ext.do')
    # COMENTADO/REMOVIDO: Linha que causava o erro ModuleNotFoundError. Usaremos um filtro personalizado abaixo.
    # app.jinja_env.add_extension('jinja2_regex.Extension')

    # NOVO: Registra um filtro Jinja personalizado para substituição de regex
    @app.template_filter('regex_replace')
    def regex_replace_filter(s, pattern, replacement):
        """
        Um filtro Jinja personalizado para realizar a substituição de regex.
        Uso no template: {{ minha_string | regex_replace('padrao', 'substituicao') }}
        """
        return re.sub(pattern, replacement, s)

    # Context processor para injetar o ano atual em todos os templates
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    # Context processor para injetar o número de notificações não lidas
    @app.context_processor
    def inject_unread_notifications_count():
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            return dict(unread_notifications_count=unread_count)
        return dict(unread_notifications_count=0) # Retorna 0 se o usuário não estiver logado

    # Carrega um usuário dado seu ID para o Flask-Login, carregando o objeto Role junto para otimização.
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.options(joinedload(User.role_obj)).get(int(user_id))

    # Injeta a role do usuário atual em todos os templates.
    @app.context_processor
    def inject_user_role():
        if current_user.is_authenticated:
            return {'current_user_role': current_user.role_obj.name if current_user.role_obj else 'Guest'}
        return {'current_user_role': 'Guest'}

    ### INÍCIO: Configuração do Flask-Admin ###

    # View customizada para o índice do painel administrativo.
    class MyAdminIndexView(AdminIndexView):
        def is_accessible(self):
            # Apenas usuários autenticados e com role 'Admin' podem acessar.
            return current_user.is_authenticated and current_user.is_admin

        def _handle_view(self, name, **kwargs):
            # Lida com o acesso não autorizado.
            if not self.is_accessible():
                if not current_user.is_authenticated:
                    flash('Por favor, faça login para acessar o painel de administração.', 'warning')
                    return redirect(url_for('main.login', next=request.url))
                else:
                    flash('Você não tem permissão para acessar o painel de administração.', 'danger')
                    return redirect(url_for('main.home'))
            # Retorna None ou chama a função super para continuar o processamento da view
            return super()._handle_view(name, **kwargs) # CORRIGIDO: Passando **kwargs

    # View base customizada para modelos do Flask-Admin.
    class MyModelView(ModelView):
        def is_accessible(self):
            # Apenas usuários autenticados e com role 'Admin' podem acessar.
            return current_user.is_authenticated and current_user.is_admin

        def _handle_view(self, name, **kwargs):
            # Lida com o acesso não autorizado.
            if not self.is_accessible():
                if not current_user.is_authenticated:
                    flash('Por favor, faça login para acessar esta seção do painel de administração.', 'warning')
                    return redirect(url_for('main.login', next=request.url))
                else:
                    flash('Você não tem permissão para acessar esta seção do painel de administração.', 'danger')
                    return redirect(url_for('main.home'))
            return super()._handle_view(name, **kwargs) # CORRIGIDO: Passando **kwargs

    # Views específicas para cada modelo no Flask-Admin.
    class UserAdminView(MyModelView):
        form = UserForm # Usa o UserForm que você criou

        column_list = ('id', 'username', 'email', 'role_obj', 'is_active_db', 'created_at', 'updated_at')
        column_labels = dict(role_obj='Papel', is_active_db='Ativo', created_at='Criado Em', updated_at='Última Atualização')
        column_searchable_list = ('username', 'email')
        column_filters = ('role_obj.name', 'is_active_db')

        # Define as colunas do formulário.
        form_columns = ['username', 'email', 'password', 'confirm_password', 'role_obj', 'is_active_db']

        # Sobrescreve o método get_form para passar o contexto de 'is_new_user' para o formulário.
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

        # Hook executado antes de salvar um modelo.
        def on_model_change(self, form, model, is_created):
            if form.password.data: # Se uma senha foi fornecida, faz o hash.
                model.set_password(form.password.data)

            if form.role_obj.data: # Garante que o role_id seja atualizado com base no objeto selecionado.
                model.role_id = form.role_obj.data.id
            else:
                model.role_id = None # Ou define um valor padrão se não selecionado.

    class RoleAdminView(MyModelView):
        form = AdminRoleForm # Usa o AdminRoleForm que você criou

        column_list = ('id', 'name', 'description', 'can_view_event', 'can_edit_event', 'can_manage_permissions',
                        'can_create_event', 'can_create_task', 'can_edit_task', 'can_delete_task',
                        'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio',
                        'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments',
                        'can_upload_attachments', 'can_manage_attachments')
        column_labels = dict(name='Nome do Papel', description='Descrição', can_view_event='Pode Ver Evento',
                             can_edit_event='Pode Editar Evento', can_manage_permissions='Pode Gerenciar Permissões',
                             can_create_event='Pode Criar Evento', can_create_task='Pode Criar Tarefa',
                             can_edit_task='Pode Editar Tarefa', can_delete_task='Pode Deletar Tarefa',
                             can_complete_task='Pode Concluir Tarefa', can_uncomplete_task='Pode Reverter Tarefa',
                             can_upload_task_audio='Pode Upload Audio', can_delete_task_audio='Pode Deletar Audio',
                             can_view_task_history='Pode Ver Histórico', can_manage_task_comments='Pode Gerenciar Comentários',
                             can_upload_attachments='Pode Upload Anexos', can_manage_attachments='Pode Gerenciar Anexos')
        column_searchable_list = ('name', 'description')

        # Define as colunas do formulário, incluindo todas as permissões granulares.
        form_columns = ('name', 'description', 'can_view_event', 'can_edit_event', 'can_manage_permissions',
                        'can_create_event', 'can_create_task', 'can_edit_task', 'can_delete_task',
                        'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio',
                        'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments',
                        'can_upload_attachments', 'can_manage_attachments') 

        def on_model_change(self, form, model, is_created):
            # Validação para garantir a unicidade do nome do papel.
            existing_role = Role.query.filter_by(name=form.name.data).first()
            if existing_role and existing_role.id != model.id:
                raise ValueError('Este nome de papel já existe. Por favor, escolha outro.')

    class GroupAdminView(MyModelView):
        form = GroupForm

        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome do Grupo', description='Descrição')
        column_searchable_list = ('name', 'description')

        form_excluded_columns = ['members'] # Não editar membros do grupo por aqui, use a rota específica.
        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            existing_group = Group.query.filter_by(name=form.name.data).first()
            if existing_group and existing_group.id != model.id:
                raise ValueError('Este nome de grupo já existe. Por favor, escolha outro.')

    class CategoryAdminView(MyModelView):
        form = CategoryForm
        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome', description='Descrição')
        column_searchable_list = ('name',)
        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            existing_category = Category.query.filter_by(name=form.name.data).first()
            if existing_category and existing_category.id != model.id:
                raise ValueError('Este nome de categoria já existe. Por favor, escolha outro.')

    class TaskCategoryAdminView(MyModelView):
        form = TaskCategoryForm
        column_list = ('id', 'name', 'description')
        column_labels = dict(name='Nome', description='Descrição')
        column_searchable_list = ('name',)
        form_columns = ('name', 'description')

        def on_model_change(self, form, model, is_created):
            existing_task_category = TaskCategory.query.filter_by(name=form.name.data).first()
            if existing_task_category and existing_task_category.id != model.id:
                raise ValueError('Este nome de categoria de tarefa já existe. Por favor, escolha outro.')
    class StatusAdminView(MyModelView):
        form = StatusForm
        column_list = ('id', 'name', 'type', 'description')
        column_labels = dict(name='Nome', type='Tipo', description='Descrição')
        column_searchable_list = ('name', 'type')
        form_columns = ('name', 'type', 'description')

        def on_model_change(self, form, model, is_created):
            existing_status = Status.query.filter_by(name=form.name.data, type=form.type.data).first()
            if existing_status and existing_status.id != model.id:
                raise ValueError(f"Um status com o nome '{form.name.data}' e tipo '{form.type.data}' já existe. Por favor, escolha outro nome ou tipo.")

    class EventAdminView(MyModelView):
        form = EventForm
        column_list = ('id', 'title', 'due_date', 'author', 'category', 'status', 'location')
        column_labels = dict(author='Autor', category='Categoria', status='Status')
        column_searchable_list = ('title', 'location', 'description')
        column_filters = ('author.username', 'category.name', 'status.name')

        form_columns = [
            'title', 'description', 'due_date', 'end_date', 'location',
            'author', 'category', 'status'
        ]

        column_default_sort = ('due_date', False)

        def on_model_change(self, form, model, is_created):
            # O autor, categoria e status são objetos selecionados, precisamos atribuir os IDs.
            # O Flask-Admin geralmente lida com isso se os campos são Foreign Key, mas se houver customização...
            model.author_id = form.author.data.id
            model.category_id = form.category.data.id if form.category.data else None
            model.status_id = form.status.data.id

    class AttachmentAdminView(MyModelView):
        form = AttachmentForm # Pode usar um formulário para visualização/edição, se necessário.
        column_list = ('id', 'task', 'filename', 'unique_filename', 'mimetype', 'filesize', 'uploader', 'upload_timestamp')
        column_labels = dict(task='Tarefa', filename='Nome Original', unique_filename='Nome no Servidor',
                             mimetype='Tipo', filesize='Tamanho', uploader='Feito por', upload_timestamp='Data Upload')
        column_searchable_list = ('filename', 'unique_filename', 'mimetype')
        column_filters = ('task.title', 'uploader.username', 'mimetype')

        # Formatter para criar um link de download na coluna 'filename'.
        def _attachment_download_link(view, context, model, name):
            if not model.unique_filename:
                return ''
            # Usa url_for para gerar o URL de download para a rota principal.
            # CORREÇÃO AQUI: As aspas externas da f-string e as internas do HTML foram corrigidas.
            return f'<a href="{url_for("main.download_attachment", attachment_id=model.id)}" target="_blank">{model.filename}</a>'
        column_formatters = {
            'filename': _attachment_download_link
        }

        # Sobrescreve o método de exclusão para remover o arquivo do sistema de arquivos.
        def on_model_delete(self, model):
            file_path = os.path.join(app.config['UPLOAD_FOLDER_ATTACHMENTS'], model.unique_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f"Anexo '{model.filename}' e arquivo excluídos com sucesso.", 'success')

        # Desabilita a criação e edição via admin, pois o upload é feito via rota de tarefa.
        # O administrador poderá apenas visualizar e deletar.
        can_create = False
        can_edit = False

    # Inicialização do Flask-Admin.
    # O `index_view` define a página inicial do PAINEL ADMIN.
    admin = Admin(app, name='Gerenciador de Eventos', template_mode='bootstrap4',
                  index_view=MyAdminIndexView(name='Início do Admin')) 
    # Adiciona um link no menu do Admin para a home page da aplicação principal.
    # Isso corresponde ao que você queria para "Ir para Home do Site".
    admin.add_link(MenuLink(name='Ir para Home do Site', url='/', target="_top", icon_type='fa', icon_value='fa-home'))

    # Adiciona as views dos modelos ao Flask-Admin.
    admin.add_view(UserAdminView(User, db.session, name='Usuários', category='Administração'))
    admin.add_view(RoleAdminView(Role, db.session, name='Papéis', category='Administração'))
    admin.add_view(GroupAdminView(Group, db.session, name='Grupos', category='Administração'))
    admin.add_view(CategoryAdminView(Category, db.session, name='Categorias de Evento', category='Configurações'))
    admin.add_view(TaskCategoryAdminView(TaskCategory, db.session, name='Categorias de Tarefa', category='Configurações'))
    admin.add_view(StatusAdminView(Status, db.session, name='Status', category='Configurações'))
    admin.add_view(EventAdminView(Event, db.session, name='Eventos'))
    admin.add_view(AttachmentAdminView(Attachment, db.session, name='Anexos', category='Configurações'))


    # Filtro Jinja2 para processar JSON/literais Python em templates para exibir diferenças.
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

    # Importa e registra o blueprint 'main'.
    from routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Comandos da CLI do Flask.
    @app.cli.command('create-db')
    def create_db_command():
        """Cria as tabelas do banco de dados, papéis padrão e um usuário administrador inicial."""
        with app.app_context():
            click.echo("Verificando e criando papéis padrão (Admin, User, Project Manager)...")
            # Define as permissões padrão para cada role na criação, conforme discutido.
            default_roles_config = {
                'Admin': {'description': 'Administrador do sistema com acesso total.', 'perms': {
                    'can_view_event': True, 'can_edit_event': True, 'can_manage_permissions': True,
                    'can_create_event': True, 'can_create_task': True, 'can_edit_task': True,
                    'can_delete_task': True, 'can_complete_task': True, 'can_uncomplete_task': True,
                    'can_upload_task_audio': True, 'can_delete_task_audio': True, 'can_view_task_history': True,
                    'can_manage_task_comments': True, 'can_upload_attachments': True, 'can_manage_attachments': True
                }},
                'Project Manager': {'description': 'Gerente de projeto com permissões elevadas.', 'perms': {
                    'can_view_event': True, 'can_edit_event': True, 'can_manage_permissions': True,
                    'can_create_event': True, 'can_create_task': True, 'can_edit_task': True,
                    'can_delete_task': True, 'can_complete_task': True, 'can_uncomplete_task': True,
                    'can_upload_task_audio': True, 'can_delete_task_audio': True, 'can_view_task_history': True,
                    'can_manage_task_comments': True, 'can_upload_attachments': True, 'can_manage_attachments': True
                }},
                'User': {'description': 'Usuário padrão com acesso básico.', 'perms': {
                    'can_view_event': True, 'can_edit_event': False, 'can_manage_permissions': False,
                    'can_create_event': False, 'can_create_task': True, 'can_edit_task': True,
                    'can_delete_task': False, 'can_complete_task': True, 'can_uncomplete_task': True,
                    'can_upload_task_audio': True, 'can_delete_task_audio': True, 'can_view_task_history': True,
                    'can_manage_task_comments': True, 'can_upload_attachments': True, 'can_manage_attachments': False
                }}
            }

            for name, config in default_roles_config.items():
                role = Role.query.filter_by(name=name).first()
                if not role:
                    # Cria a role com as permissões definidas.
                    role = Role(name=name, description=config['description'], **config['perms'])
                    db.session.add(role)
                    click.echo(f"Papel '{name}' criado com permissões iniciais.")
                else:
                    # Se a role já existe, atualiza as permissões para garantir consistência.
                    # Isso é útil caso você adicione novas permissões ao modelo Role.
                    for perm_name, perm_value in config['perms'].items():
                        setattr(role, perm_name, perm_value)
                    click.echo(f"Papel '{name}' já existe e permissões atualizadas.")
            db.session.commit()
            click.echo("Papéis verificados/criados/atualizados.")

            click.echo("Verificando e criando status padrão de evento (Ativo, Realizado, Arquivado)...")
            default_event_statuses = {'Ativo': 'Evento em andamento ou futuro.', 'Realizado': 'Evento que já ocorreu.', 'Arquivado': 'Evento antigo ou inativo.'}
            for name, desc in default_event_statuses.items():
                if not Status.query.filter_by(name=name, type='event').first():
                    status = Status(name=name, type='event', description=desc)
                    db.session.add(status)
                    click.echo(f"Status de evento '{name}' criado.")
                else:
                    click.echo(f"Status de evento '{name}' já existe.")
            
            click.echo("Verificando e criando status padrão de tarefa (Pendente, Em Andamento, Concluída, Cancelada)...")
            default_task_statuses = {'Pendente': 'Tarefa aguardando início ou atribuição.', 'Em Andamento': 'Tarefa em progresso.', 'Concluída': 'Tarefa concluída com sucesso.', 'Cancelada': 'Tarefa foi cancelada.'}
            for name, desc in default_task_statuses.items():
                if not Status.query.filter_by(name=name, type='task').first():
                    status = Status(name=name, type='task', description=desc)
                    db.session.add(status)
                    click.echo(f"Status de tarefa '{name}' criado.")
                else:
                    click.echo(f"Status de tarefa '{name}' já existe.")

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
                # CORREÇÃO AQUI: Adicionado 'print(' que estava faltando.
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

    # Handlers de erro para páginas não encontradas e erros internos do servidor.
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    return app

# Cria a instância da aplicação Flask.
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)