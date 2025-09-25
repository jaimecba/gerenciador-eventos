# C:\gerenciador-eventos\routes.py

from flask import render_template, url_for, flash, redirect, request, Blueprint, jsonify, current_app, abort, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from werkzeug.security import generate_password_hash
from extensions import db, mail

# IMPORTAÇÕES DE FORMS ATUALIZADAS
from forms import (RegistrationForm, LoginForm, EventForm, CategoryForm, StatusForm,
                   UpdateAccountForm, RequestResetForm, ResetPasswordForm, SearchForm,
                   TaskForm, UserForm, TaskCategoryForm, GroupForm, AssignUsersToGroupForm,
                   EventPermissionForm, CommentForm, AttachmentForm) # <-- ATUALIZADO: Importar AttachmentForm

# Importar as funções auxiliares diretamente do forms
# Importar as funções auxiliares diretamente do forms
from forms import get_users, get_task_categories, get_task_statuses, get_roles, AdminRoleForm

# IMPORTAÇÕES DE MODELS ATUALIZADAS
# Importação de models.py, assumindo que está no mesmo nível que routes.py
from models import (User, Role, Event, Task, TaskAssignment, ChangeLogEntry, Status,
                    Category, PasswordResetToken, TaskHistory, Group,
                    UserGroup, EventPermission, Comment, TaskCategory, Attachment, Notification) # <-- ADICIONADO Notification
from sqlalchemy import func, or_, distinct, false, and_
from datetime import datetime, date, timedelta
import json
from sqlalchemy.orm import joinedload, selectinload # Adicionado selectinload
import uuid
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory
import os
from utils.changelog_utils import diff_dicts
from functools import wraps # Importado para o decorator permission_required
from functools import wraps # Importado para o decorator permission_required

from decorators import admin_required, project_manager_required, role_required

# <<<--- DEFINIÇÃO DO BLUEPRINT 'MAIN' --->>>
main = Blueprint('main', __name__)

# =========================================================================
# Decorator de Permissão Genérico
# =========================================================================
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa estar logado para acessar esta página.', 'info')
                return redirect(url_for('main.login'))
            
            # Verifica se o current_user tem a permissão específica via sua propriedade @property
            if not getattr(current_user, permission_name, False):
                flash('Você não tem permissão para realizar esta ação.', 'danger')
                return redirect(url_for('main.home')) # Ou outra página de erro/redirecionamento
            return f(*args, **kwargs)
        return decorated_function
    return decorator
# =========================================================================
# FIM: Decorator de Permissão Genérico
# =========================================================================


# --- FUNÇÃO AUXILIAR PARA ENVIAR E-MAIL DE REDEFINIÇÃO DE SENHA ---
def send_reset_email(user):
    active_tokens = PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).all()
    for token_obj in active_tokens:
        db.session.delete(token_obj)
    db.session.commit()

    token_uuid_str = str(uuid.uuid4())
    expires_in_seconds = 3600

    reset_token_db_entry = PasswordResetToken(
        user_id=user.id,
        token_uuid=token_uuid_str,
        expiration_date=datetime.utcnow() + timedelta(seconds=expires_in_seconds),
        is_used=False
    )
    db.session.add(reset_token_db_entry)
    db.session.commit()

    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset-salt')
    signed_token = s.dumps(token_uuid_str)

    msg = Message('Redefinição de Senha - Gerenciador de Eventos',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    msg.body = f'''Para redefinir sua senha, visite o seguinte link:
{url_for('main.reset_token', token=signed_token, _external=True)}

Se você não solicitou isso, ignore este e-mail e nenhuma alteração será feita em sua conta.
'''
    mail.send(msg)
    current_app.logger.info(f"Email de redefinição enviado para {user.email} com token {token_uuid_str[:8]}...")
# --- FIM FUNÇÃO AUXILIAR ---

# =========================================================================
# NOVO: FUNÇÕES AUXILIARES DE NOTIFICAÇÃO
# =========================================================================

def send_notification_email(recipient_email, subject, body, html_body=None):
    """Envia um e-mail de notificação."""
    try:
        msg = Message(subject,
                      sender=current_app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[recipient_email])
        msg.body = body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        current_app.logger.info(f"Email de notificação enviado para {recipient_email} com assunto '{subject}'.")
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email de notificação para {recipient_email}: {e}", exc_info=True)
        return False

def create_in_app_notification(user_id, message, link_url=None, related_object_type=None, related_object_id=None):
    """Cria uma notificação in-app para um usuário."""
    try:
        notification = Notification(
            user_id=user_id,
            message=message,
            link_url=link_url,
            related_object_type=related_object_type,
            related_object_id=related_object_id
        )
        db.session.add(notification)
        # Não commit aqui, o commit principal da transação da rota fará isso.
        # db.session.commit()
        current_app.logger.info(f"Notificação in-app criada para user {user_id}: '{message[:50]}'.")
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao criar notificação in-app para user {user_id}: {e}", exc_info=True)
        db.session.rollback() # Rollback em caso de erro na notificação, mas o comentário já pode ter sido salvo.
# Idealmente, tudo seria em uma única transação, mas por simplicidade aqui.
        return False

# =========================================================================
# FIM: FUNÇÕES AUXILIARES DE NOTIFICAÇÃO
# =========================================================================

# Defina quantos itens você quer por página (para o ChangeLog)
LOGS_PER_PAGE = 10

# --- FUNÇÃO AUXILIAR PARA FILTRAGEM E PAGINAÇÃO DE EVENTOS ---
def get_filtered_events(user, search_query, page, per_page, event_status_name=None):
    """
    Função auxiliar para construir a query de eventos com base no status, pesquisa e permissões do usuário.
    Retorna um objeto de paginação de eventos.
    """
    base_query = Event.query.options(
        joinedload(Event.status),
        joinedload(Event.category),
        joinedload(Event.author)
    )

    if user.is_authenticated:
        if not user.is_admin: # Admins veem tudo, sem precisar de permissões explícitas
            # Para usuários não-admin, eventos só são visíveis se o usuário for autor
            # OU se o usuário estiver atribuído a alguma tarefa naquele evento.
            # Também filtra para mostrar apenas eventos 'Ativos' por padrão, a menos que outro status seja especificado.

            active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()

            # Condição base para visibilidade (autor OU tarefa atribuída) - Comparando IDs dos usuários
            visibility_condition = or_(
                Event.author_id == user.id, # Comparação por ID
                Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == user.id)) # Comparação por ID
            )

            # Aplica o filtro de status, considerando o pedido do usuário "apenas nos eventos ativos"
            if event_status_name: # Se um status específico foi solicitado (ex: "Realizado", "Arquivado")
                status_filter_obj = Status.query.filter_by(name=event_status_name, type='event').first()
                if status_filter_obj:
                    base_query = base_query.filter(and_(visibility_condition, Event.status == status_filter_obj))
                else:
                    current_app.logger.warning(f"Status de Evento '{event_status_name}' solicitado, mas não encontrado para o tipo 'event' no banco de dados.")
                    # Mensagem flash com escape de caracteres
                    flash(f"Status '{event_status_name}' para eventos não encontrado. A busca pode não ser precisa.", 'warning')
                    return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)
            else: # Se nenhum status específico foi solicitado, default para 'Ativo'
                if active_status_obj:
                    base_query = base_query.filter(and_(visibility_condition, Event.status == active_status_obj))
                else:
                    # Se nem 'Ativo' foi encontrado, e nenhum status específico foi pedido, não mostra eventos.
                    current_app.logger.warning("Status 'Ativo' para eventos não encontrado. Eventos não serão filtrados por status ativo e podem não ser visíveis.")
                    # Mensagem flash com escape de caracteres
                    flash("Status 'Ativo' para eventos não encontrado. A busca pode não ser precisa.", 'warning')
                    return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)

        # else: Admin vê todos os eventos sem filtro de permissão, a não ser que um status específico seja solicitado
        elif event_status_name: # Para admin, se um status específico foi solicitado
            status_filter_obj = Status.query.filter_by(name=event_status_name, type='event').first()
            if status_filter_obj:
                base_query = base_query.filter(Event.status == status_filter_obj)
            else:
                current_app.logger.warning(f"Status de Evento '{event_status_name}' solicitado para admin, mas não encontrado para o tipo 'event' no banco de dados.")
                # Mensagem flash com escape de caracteres
                flash(f"Status '{event_status_name}' para eventos não encontrado. A busca pode não ser precisa.", 'warning')
                return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)

    else: # Se não está autenticado, não deve ver eventos
        return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)
    search_query_text = request.args.get('search', '')
    if search_query_text:
        base_query = base_query.filter(
            or_(
                Event.title.ilike(f'%{search_query_text}%'),
                Event.description.ilike(f'%{search_query_text}%'),
                Event.location.ilike(f'%{search_query_text}%')
            )
        )

    base_query = base_query.order_by(Event.due_date.asc())

    return base_query.paginate(page=page, per_page=per_page, error_out=False)


@main.route("/")
@main.route("/home")
@login_required
def home():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    # Para a página inicial, agora, para usuários não-admin, o default é mostrar
    # apenas eventos ativos com tarefas vinculadas. get_filtered_events já cuida disso.
    events = get_filtered_events(current_user, search_query, page, per_page)

    return render_template('home.html', events=events, title='Todos os Eventos Ativos com Minhas Tarefas', search_query=search_query, current_filter='active')
@main.route("/events/active")
@login_required
def active_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    # Esta rota continua solicitando explicitamente eventos ativos
    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Ativo')
    return render_template('home.html', events=events, title='Eventos Ativos', search_query=search_query, current_filter='active')
    

@main.route("/calendar_view")
@login_required
def calendar_view():
    return render_template('calendar.html', title='Calendário')


@main.route("/events/completed")
@login_required
def completed_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Realizado')

    return render_template('home.html', events=events, title='Eventos Realizados', search_query=search_query, current_filter='completed')

@main.route("/events/archived")
@login_required
def archived_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Arquivado')
    return render_template('home.html', events=events, title='Eventos Arquivados', search_query=search_query, current_filter='archived')
# --- FIM DAS ROTAS DE LISTAGEM DE EVENTOS MODIFICADAS ---

# ----------------------------------------------------
# ROTAS DE AUTENTICAÇÃO
# ----------------------------------------------------

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user_role = Role.query.filter_by(name='User').first()

        if not user_role:
            flash("Erro interno: O papel 'User' não foi encontrado. Contate o administrador.", 'danger')
            return render_template('register.html', title='Registrar', form=form)

        hashed_password = generate_password_hash(form.password.data)

        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            role_obj=user_role
        )

        db.session.add(user)
        db.session.commit()

        flash('Sua conta foi criada com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registrar', form=form)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.active_events'))

    form = LoginForm()

    if request.method == 'POST':
        print(f"\n--- DEBUG: Tentativa de Login ---")
        print(f"--- DEBUG: E-mail recebido (form.email.data): '{form.email.data}' ---")
        print(f"--- DEBUG: Senha preenchida? {bool(form.password.data)} ---")

    if form.validate_on_submit():
        print(f"--- DEBUG: Formulário de Login validado com sucesso! ---")
        user = User.query.filter_by(email=form.email.data).first()
        print(f"--- DEBUG: Buscando usuário com e-mail: '{form.email.data}' ---")

        if user:
            print(f"--- DEBUG: Usuário encontrado: Username='{user.username}', Email='{user.email}' ---")
            if user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)

                next_page = request.args.get('next')
                if not next_page or next_page == url_for('main.home'):
                    redirect_url = url_for('main.active_events')
                else:
                    redirect_url = next_page

                flash('Login bem-sucedido!', 'success')
                print(f"--- DEBUG: Senha corresponde. Login bem-sucedido. Redirecionando para: {redirect_url} ---")
                return redirect(redirect_url)
            else:
                flash('Login mal-sucedido. Por favor, verifique seu e-mail e senha.', 'danger')
                print(f"--- DEBUG: Senha não corresponde para o usuário '{user.email}'. ---")
        else:
            flash('Login mal-sucedido. Por favor, verifique seu e-mail e senha.', 'danger')
            print(f"--- DEBUG: Usuário com e-mail '{form.email.data}' NÃO encontrado no banco de dados. ---")
    else:
        print(f"--- DEBUG: Validação do formulário de Login FALHOU. Erros: {form.errors} ---")
        if request.method == 'POST':
            flash('Login mal-sucedido. Por favor, verifique seu e-mail e senha.', 'danger')

    return render_template('login.html', title='Login', form=form)

@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('main.home'))

@main.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        # save_picture é uma função auxiliar que deve ser definida ou importada
        # Caso não esteja definida, essa linha pode causar um erro.
        # Por enquanto, vou manter o que estava no seu código.
        if form.picture.data and form.picture.data.filename:
            # save_picture(form.picture.data) # Descomente e implemente se necessário
            pass # Apenas um placeholder se save_picture não estiver definida
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Sua conta foi atualizada!', 'success')
        return redirect(url_for('main.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    # Certifique-se de que current_user.image_file está definido para evitar erro
    image_file = url_for('static', filename='profile_pics/' + (current_user.image_file if current_user.image_file else 'default.jpg'))
    return render_template('account.html', title='Minha Conta',
                           image_file=image_file, form=form)

@main.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
            flash('Um e-mail foi enviado com instruções para redefinir sua senha. Verifique sua caixa de entrada (e SPAM).', 'info')
            return redirect(url_for('main.login'))
        else:
            flash('Não há conta com este email. Você pode se registrar primeiro.', 'warning')
    return render_template('reset_request.html', title='Redefinir Senha', form=form)

@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        flash('Você já está logado. Por favor, deslogue para redefinir a senha.', 'info')
        return redirect(url_for('main.home'))

    user = None
    reset_token_db_entry = None
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset-salt')

    try:
        token_uuid_from_link = s.loads(token, max_age=3600)
        reset_token_db_entry = PasswordResetToken.query.filter_by(token_uuid=token_uuid_from_link).first()

        if not reset_token_db_entry:
            flash('Link de redefinição de senha inválido ou não encontrado. Por favor, solicite um novo.', 'danger')
            return redirect(url_for('main.reset_request'))

        if reset_token_db_entry.is_used:
            flash('Este link de redefinição de senha já foi utilizado.', 'danger')
            return redirect(url_for('main.reset_request'))

        if reset_token_db_entry.is_expired():
            flash('Este link de redefinição de senha expirou. Por favor, solicite um novo.', 'danger')
            return redirect(url_for('main.reset_request'))

        user = User.query.get(reset_token_db_entry.user_id)
        if not user:
            flash('Erro: Usuário associado ao token não encontrado.', 'danger')
            return redirect(url_for('main.reset_request'))

    except SignatureExpired:
        flash('Seu link de redefinição de senha expirou. Por favor, solicite um novo.', 'danger')
        return redirect(url_for('main.reset_request'))
    except (BadTimeSignature, BadSignature):
        flash('Token de redefinição de senha inválido. Por favor, solicite um novo.', 'danger')
        return redirect(url_for('main.reset_request'))
    except Exception as e:
        current_app.logger.error(f"Erro inesperado ao processar token de redefinição: {e}", exc_info=True)
        flash('Ocorreu um erro inesperado. Tente novamente ou entre em contato com o suporte.', 'danger')
        return redirect(url_for('main.reset_request'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        try:
            reset_token_db_entry.is_used = True
            db.session.commit()

            user.set_password(form.password.data)
            db.session.commit()

            ChangeLogEntry.log_update(
                user_id=user.id,
                record_type='User',
                record_id=user.id,
                old_data={},
                new_data={},
                description=f"Senha do usuário '{user.username}' redefinida com sucesso."
            )
            db.session.commit()

            flash('Sua senha foi redefinida com sucesso! Você já pode fazer login.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao redefinir senha do usuário {user.id}: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado. Por favor, tente novamente.', 'danger')
            return redirect(url_for('main.reset_request'))

    return render_template('reset_token.html', title='Redefinir Senha', form=form)


# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# Rotas de Eventos
# =========================================================================
@main.route("/event/new", methods=['GET', 'POST'])
@login_required
def new_event():
    # Verificação de permissão para criar eventos
    can_create_event_permission = (
        current_user.is_admin or
        (current_user.role_obj and current_user.role_obj.can_create_event)
    )

    if not can_create_event_permission:
        flash('Você não tem permissão para criar novos eventos.', 'danger')
        abort(403) # Forbidden

    form = EventForm()

    available_categories = Category.query.all()
    available_event_statuses = Status.query.filter_by(type='event').all()

    if not available_event_statuses:
        flash("Nenhum status de evento disponível. Por favor, crie pelo menos um status do tipo 'Evento' na administração (Ex: Ativo, Pendente, etc.)", 'warning')
    if not available_categories:
        flash('Nenhuma categoria de evento disponível. Por favor, crie pelo menos uma categoria na administração.', 'warning')


    if form.validate_on_submit():
        # Busca os objetos completos Category e Status usando os IDs do formulário
        category_obj = Category.query.get(form.category.data)
        status_obj = Status.query.get(form.status.data)

        if not category_obj or not status_obj:
            flash('Categoria ou Status de evento inválido.', 'danger')
            return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Novo Evento')


        event = Event(title=form.title.data,
                      description=form.description.data,
                      due_date=form.due_date.data,
                      end_date=form.end_date.data,
                      location=form.location.data,
                      author=current_user,
                      category=category_obj, # Atribui o objeto Category
                      status=status_obj)    # Atribui o objeto Status
        db.session.add(event)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'Event', event.id, new_data=event.to_dict(), description=f"Evento '{event.title}' criado.")
        db.session.commit()
        flash('Seu evento foi criado!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Novo Evento')

@main.route("/event/<int:event_id>")
@login_required
def event(event_id): # <-- ESTA É A ROTA PARA event.html
    # Eager loading para tarefas e seus atribuídos para evitar problemas de N+1 queries.
    # Adicionado .joinedload(Attachment.uploader) para carregar o uploader do anexo
    event_obj = Event.query.options(
        joinedload(Event.tasks).joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Event.tasks).joinedload(Task.attachments).joinedload(Attachment.uploader), # --- Eager load attachments and their uploaders ---
        joinedload(Event.author), # Load event author for permission checks
        joinedload(Event.event_permissions).joinedload(EventPermission.role), # Load event permissions and their roles
        joinedload(Event.event_permissions).joinedload(EventPermission.user),
        joinedload(Event.event_permissions).joinedload(EventPermission.group),
    ).get_or_404(event_id)

    # Revalidação da permissão de visualização do evento
    can_view_event = False
    if current_user.is_authenticated:
        is_admin = current_user.is_admin
        is_event_author = (event_obj.author_id == current_user.id) # Comparação por ID

        if is_admin: # Admins podem sempre visualizar
            can_view_event = True
        elif is_event_author: # Autor do evento
            can_view_event = True
        else:
            # Usuário não é admin nem autor, mas pode estar atribuído a alguma tarefa no evento
            # Comparando IDs dos usuários nas atribuições
            if any(current_user.id == assignment.user_id for task in event_obj.tasks for assignment in task.assignees_associations):
                can_view_event = True
            # Verifica permissões de visualização específicas para o evento
            if not can_view_event:
                for ep in event_obj.event_permissions:
                    if ep.user_id == current_user.id and ep.role and ep.role.can_view_event:
                        can_view_event = True
                        break
                    if ep.group and ep.group_id in [ug.group_id for ug in current_user.user_groups] and ep.role and ep.role.can_view_event:
                        can_view_event = True
                        break

    if not can_view_event:
        flash('Você não tem permissão para visualizar este evento.', 'danger')
        abort(403) # Ou return redirect(url_for('main.home')) para uma experiência mais suave

    # --- Lógica de filtragem de tarefas para o usuário atual ---
    filtered_active_tasks = []
    filtered_completed_tasks = []

    if is_admin or is_event_author:
        filtered_active_tasks = sorted([task for task in event_obj.tasks if not task.is_completed], key=lambda t: t.due_date)
        filtered_completed_tasks = sorted([task for task in event_obj.tasks if task.is_completed], key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)
    else:
        # Usuário COMUM (não admin, não autor) só vê as tarefas a que está diretamente atribuído
        for task in event_obj.tasks:
            # task.assignees é uma @property que acessa a lista de usuários atribuídos.
            # Graças ao joinedload acima, esta chamada não fará uma nova consulta ao DB para cada tarefa.
            # Comparando IDs dos usuários
            if current_user.id in [assignee.id for assignee in task.assignees]:
                if not task.is_completed:
                    filtered_active_tasks.append(task)
                else:
                    filtered_completed_tasks.append(task)

        # Classificar as listas filtradas
        filtered_active_tasks.sort(key=lambda t: t.due_date)
        filtered_completed_tasks.sort(key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)

    current_date = date.today()

    # --- Permissões para controle de botões de EVENTO no template ---
    # Permissão para Gerenciar Permissões do Evento
    can_manage_event_permissions = is_admin or is_event_author
    if not can_manage_event_permissions: # Só verifica individual/grupo se não for admin/autor
        for ep in event_obj.event_permissions:
            if ep.user_id == current_user.id and ep.role and ep.role.can_manage_permissions: # Comparação por ID
                can_manage_event_permissions = True
                break
            # user_groups é uma relação, não precisa de .filter_by
            if ep.group and ep.group in [ug.group for ug in current_user.user_groups] and ep.role and ep.role.can_manage_permissions:
                can_manage_event_permissions = True
                break

    # Permissão para Editar/Deletar Evento
    can_edit_event = is_admin or is_event_author
    if not can_edit_event: # Só verifica individual/grupo se não for admin/autor
        for ep in event_obj.event_permissions:
            if ep.user_id == current_user.id and ep.role and ep.role.can_edit_event: # Comparação por ID
                can_edit_event = True
                break
            # user_groups é uma relação, não precisa de .filter_by
            if ep.group and ep.group in [ug.group for ug in current_user.user_groups] and ep.role and ep.role.can_edit_event:
                can_edit_event = True
                break

    # Permissão para Criar Tarefas no Evento
    can_create_tasks = is_admin or is_event_author or \
                       (current_user.role_obj and current_user.role_obj.can_create_task)

    # --- Permissão para upload de anexo ---
    can_upload_attachments = current_user.is_admin or \
                             (current_user.role_obj and current_user.role_obj.can_upload_attachments)
    # --- Permissão para gerenciar (excluir) anexos ---
    can_manage_attachments = current_user.is_admin or \
                             (current_user.role_obj and current_user.role_obj.can_manage_attachments)

    # Instancia o formulário de comentário para passar ao template
    comment_form = CommentForm()
    # Instancia o formulário de anexo para passar ao template
    attachment_form = AttachmentForm()

    return render_template('event.html',
                           title=event_obj.title,
                           event=event_obj,
                           active_tasks=filtered_active_tasks,
                           completed_tasks=filtered_completed_tasks,
                           current_date=current_date,
                           is_admin=is_admin, # Já definida acima
                           is_event_author=is_event_author, # Já definida acima
                           can_manage_event_permissions=can_manage_event_permissions,
                           can_edit_event=can_edit_event,
                           can_create_tasks=can_create_tasks,
                           # --- Passa as permissões e o formulário de anexo ---
                           can_upload_attachments=can_upload_attachments,
                           can_manage_attachments=can_manage_attachments,
                           attachment_form=attachment_form,
                           # --- FIM NOVO ---
                           comment_form=comment_form # Passa o formulário de comentário
                           )


@main.route("/event/<int:event_id>/update", methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    event_obj = Event.query.get_or_404(event_id)

    # Verificação de permissão de edição
    can_edit_event = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id: # Comparação por ID
            can_edit_event = True
        elif current_user.is_admin: # Admins podem sempre editar
            can_edit_event = True
        else:
            # Verifica permissão individual
            if EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.user_id == current_user.id,
                    EventPermission.role.has(Role.can_edit_event == True)
                )
            ).first():
                can_edit_event = True
            # Verifica permissão via grupo
            user_group_ids = [ug.group_id for ug in current_user.user_groups]
            if user_group_ids and EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.group_id.in_(user_group_ids),
                    EventPermission.role.has(Role.can_edit_event == True)
                )
            ).first():
                can_edit_event = True

    if not can_edit_event:
        abort(403) # Forbidden

    old_data = event_obj.to_dict()

    form = EventForm(obj=event_obj)
    if form.validate_on_submit():
        event_obj.title = form.title.data
        event_obj.description = form.description.data
        event_obj.due_date = form.due_date.data
        event_obj.end_date = form.end_date.data
        event_obj.location = form.location.data

        # Busca os objetos Category e Status
        category_obj = Category.query.get(form.category.data)
        status_obj = Status.query.get(form.status.data)

        if not category_obj or not status_obj:
            flash('Categoria ou Status de evento inválido.', 'danger')
            return render_template('create_edit_event.html', title='Atualizar Evento', form=form, legend='Atualizar Evento')

        event_obj.category = category_obj # Atribui o objeto Category
        event_obj.status = status_obj     # Atribui o objeto Status
        db.session.commit()

        ChangeLogEntry.log_update(current_user.id, 'Event', event_obj.id, old_data=old_data, new_data=event_obj.to_dict(), description=f"Evento '{event_obj.title}' atualizado.")
        db.session.commit()
        flash('Seu evento foi atualizado!', 'success')
        return redirect(url_for('main.event', event_id=event_obj.id))
    elif request.method == 'GET':
        # Preenche os campos do formulário para o método GET
        form.title.data = event_obj.title
        form.description.data = event_obj.description
        form.due_date.data = event_obj.due_date
        form.end_date.data = event_obj.end_date
        form.location.data = event_obj.location
        form.category.data = event_obj.category.id if event_obj.category else None
        form.status.data = event_obj.status.id if event_obj.status else None
    return render_template('create_edit_event.html', title='Atualizar Evento',
                           form=form, legend='Atualizar Evento')

@main.route("/event/<int:event_id>/delete", methods=['POST'])
@login_required
def delete_event(event_id):
    event_obj = Event.query.get_or_404(event_id)

    # Verificação de permissão de edição (se pode editar, pode deletar)
    can_edit_event = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id: # Comparação por ID
            can_edit_event = True
        elif current_user.is_admin: # Admins podem sempre deletar
            can_edit_event = True
        else:
            if EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.user_id == current_user.id,
                    EventPermission.role.has(Role.can_edit_event == True)
                )
            ).first():
                can_edit_event = True
            user_group_ids = [ug.group_id for ug in current_user.user_groups]
            if user_group_ids and EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.group_id.in_(user_group_ids),
                    EventPermission.role.has(Role.can_edit_event == True)
                )
            ).first():
                can_edit_event = True

    if not can_edit_event:
        abort(403) # Forbidden

    old_data = event_obj.to_dict()

    db.session.delete(event_obj)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'Event', event_obj.id, old_data=old_data, description=f"Evento '{event_obj.title}' deletado.")
    db.session.commit()
    flash('Seu evento foi deletado!', 'success')
    return redirect(url_for('main.home'))

@main.route("/search")
@login_required
def search():
    form = SearchForm()
    results = []
    query = request.args.get('query')

    if query:
        # Start with base query for events, including eager loading for relationships
        events_query = Event.query.options(
            joinedload(Event.status),
            joinedload(Event.category),
            joinedload(Event.author)
        )

        # Apply text search conditions
        events_query = events_query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%')
            )
        )

        # Apply visibility rules directly to the query
        if not current_user.is_admin:
            active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()

            # Usando IDs para comparação
            visibility_condition = or_(
                Event.author_id == current_user.id,
                Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id))
            )

            if active_status_obj:
                events_query = events_query.filter(and_(visibility_condition, Event.status == active_status_obj))
            else: # Fallback if 'Ativo' status is not found
                events_query = events_query.filter(visibility_condition)
                # Mensagem flash com escape de caracteres
                flash("Status 'Ativo' para eventos não encontrado. A busca pode não ser precisa.", 'warning')
        # Execute the query to get viewable events
        viewable_events = events_query.all()

        for event_obj in viewable_events:
            results.append({
                'type': 'Evento',
                'title': event_obj.title,
                'description': event_obj.description,
                'link': url_for('main.event', event_id=event_obj.id)
            })

        # Tasks search remains the same (already filtered by TaskAssignment.user == current_user)
        tasks = Task.query.filter(
            Task.title.ilike(f'%{query}%') |
            Task.description.ilike(f'%{query}%') |
            Task.notes.ilike(f'%{query}%')
        ).join(TaskAssignment).filter(TaskAssignment.user_id == current_user.id).all()

        for task_obj in tasks:
            results.append({
                'type': 'Tarefa',
                'title': task_obj.title,
                'description': task_obj.description,
                'link': url_for('main.task_detail', task_id=task_obj.id) # ATUALIZADO: Aponta para a nova rota de detalhes da tarefa
            })

    return render_template('search_results.html', title='Resultados da Busca', form=form, results=results, query=query)


# =========================================================================
# Rotas de Categorias
# =========================================================================
@main.route("/category/new", methods=['GET', 'POST'])
@login_required
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, description=form.description.data)
        db.session.add(category)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'Category', category.id, new_data=category.to_dict(), description=f"Categoria '{category.name}' criada.")
        db.session.commit()
        flash('Categoria criada com sucesso!', 'success')
        return redirect(url_for('main.list_categories'))
    return render_template('create_edit_category.html', title='Nova Categoria', form=form, legend='Nova Categoria')

@main.route("/categories")
@login_required
def list_categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('list_categories.html', categories=categories, title='Categorias de Eventos')

@main.route("/category/<int:category_id>/update", methods=['GET', 'POST'])
@login_required
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category, original_name=category.name)
    if form.validate_on_submit():
        old_data = category.to_dict()
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Category', category.id, old_data=old_data, new_data=category.to_dict(), description=f"Categoria '{category.name}' atualizada.")
        db.session.commit()
        flash('Categoria atualizada com sucesso!', 'success')
        return redirect(url_for('main.list_categories'))
    elif request.method == 'GET':
        pass
    return render_template('create_edit_category.html', title='Atualizar Categoria', form=form, legend='Atualizar Categoria')
@main.route("/category/<int:category_id>/delete", methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.events.first():
        flash('Não é possível excluir esta categoria, pois ela está associada a eventos.', 'danger')
        return redirect(url_for('main.list_categories'))

    old_data = category.to_dict()
    db.session.delete(category)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'Category', category.id, old_data=old_data, description=f"Categoria '{old_data.get('name', 'Nome Desconhecido')}' deletada.")
    db.session.commit()
    flash('Categoria deletada com sucesso!', 'success')
    return redirect(url_for('main.list_categories'))

# =========================================================================
# Rotas de Status (Agora gerenciando o modelo Status consolidado)
# =========================================================================
@main.route("/status/new", methods=['GET', 'POST'])
@login_required
@admin_required
def new_status():
    form = StatusForm()
    if form.validate_on_submit():
        status = Status(name=form.name.data, type=form.type.data, description=form.description.data)
        db.session.add(status)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'Status', status.id, new_data=status.to_dict(), description=f"Status '{status.name}' ({status.type}) criado.")
        db.session.commit()
        flash('Status criado com sucesso!', 'success')
        return redirect(url_for('main.list_statuses'))
    return render_template('create_edit_status.html', title='Novo Status', form=form, legend='Novo Status')

@main.route("/statuses")
@login_required
@admin_required
def list_statuses():
    statuses = Status.query.order_by(Status.type, Status.name).all()
    return render_template('list_statuses.html', statuses=statuses, title='Status (Eventos e Tarefas)')
@main.route("/status/<int:status_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required
def update_status(status_id):
    status_obj = Status.query.get_or_404(status_id)
    form = StatusForm(obj=status_obj, original_name=status_obj.name, original_type=status_obj.type)
    if form.validate_on_submit():
        old_data = status_obj.to_dict()
        status_obj.name = form.name.data
        status_obj.type = form.type.data
        status_obj.description = form.description.data
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Status', status_obj.id, old_data=old_data, new_data=status_obj.to_dict(), description=f"Status '{status_obj.name}' ({status_obj.type}) atualizado.")
        db.session.commit()
        flash('Status atualizado com sucesso!', 'success')
        return redirect(url_for('main.list_statuses'))
    elif request.method == 'GET':
        pass
    return render_template('create_edit_status.html', title='Atualizar Status', form=form, legend='Atualizar Status')

@main.route("/status/<int:status_id>/delete", methods=['POST'])
@login_required
@admin_required
def delete_status(status_id):
    status_obj = Status.query.get_or_404(status_id)

    if Event.query.filter_by(status=status_obj).first() or Task.query.filter_by(task_status=status_obj).first():
        flash(f"Não é possível deletar o status '{status_obj.name}' porque ele está associado a eventos ou tarefas. Desvincule-o primeiro.", 'danger')
        return redirect(url_for('main.list_statuses'))

    old_data = status_obj.to_dict()
    db.session.delete(status_obj)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'Status', status_obj.id, old_data=old_data, description=f"Status '{status_obj.name}' ({status_obj.type}) deletado.")
    db.session.commit()
    flash('Status deletado com sucesso!', 'success')
    return redirect(url_for('main.list_statuses'))


# =========================================================================
# =========================================================================
# =========================================================================
# Rotas de TaskCategory
# =========================================================================
@main.route("/task_category/new", methods=['GET', 'POST'])
@login_required
@admin_required
def new_task_category():
    form = TaskCategoryForm()
    if form.validate_on_submit():
        task_category = TaskCategory(name=form.name.data, description=form.description.data)
        db.session.add(task_category)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'TaskCategory', task_category.id, new_data=task_category.to_dict(), description=f"Categoria de Tarefa '{task_category.name}' criada.")
        db.session.commit()
        flash('Categoria de Tarefa criada com sucesso!', 'success')
        return redirect(url_for('main.list_task_categories'))
    return render_template('create_edit_task_category.html', title='Nova Categoria de Tarefa', form=form, legend='Nova Categoria de Tarefa')

@main.route("/task_categories")
@login_required
@admin_required
def list_task_categories():
    task_categories = TaskCategory.query.order_by(TaskCategory.name).all()
    return render_template('list_task_categories.html', task_categories=task_categories, title='Categorias de Tarefas')

@main.route("/task_category/<int:task_category_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required
def update_task_category(task_category_id):
    task_category = TaskCategory.query.get_or_404(task_category_id)
    form = TaskCategoryForm(obj=task_category, original_name=task_category.name)
    if form.validate_on_submit():
        old_data = task_category.to_dict()
        task_category.name = form.name.data
        task_category.description = form.description.data
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'TaskCategory', task_category.id, old_data=old_data, new_data=task_category.to_dict(), description=f"Categoria de Tarefa '{task_category.name}' atualizada.")
        db.session.commit()
        flash('Categoria de Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('main.list_task_categories'))
    elif request.method == 'GET':
        pass
    return render_template('create_edit_task_category.html', title='Atualizar Categoria de Tarefa', form=form, legend='Atualizar Categoria de Tarefa')

@main.route("/task_category/<int:task_category_id>/delete", methods=['POST'])
@login_required
@admin_required
def delete_task_category(task_category_id):
    task_category = TaskCategory.query.get_or_404(task_category_id)
    if Task.query.filter_by(task_category=task_category).first():
        flash('Não é possível excluir esta categoria de tarefa, pois ela está associada a tarefas.', 'danger')
        return redirect(url_for('main.list_task_categories'))

    old_data = task_category.to_dict()
    db.session.delete(task_category)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'TaskCategory', task_category.id, old_data=old_data, description=f"Categoria de Tarefa '{old_data.get('name', 'Nome Desconhecido')}' excluída.")
    db.session.commit()
    flash('Categoria de Tarefa excluída!', 'success')
    return redirect(url_for('main.list_task_categories'))

# =========================================================================
# Rotas de Tarefas
# =========================================================================
@main.route("/event/<int:event_id>/task/new", methods=['GET', 'POST'])
@login_required
def new_task(event_id):
    event_obj = Event.query.get_or_404(event_id)

    # Verificação de permissão para criar tarefas
    can_create_task_permission = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or # Comparação por ID
        (current_user.role_obj and current_user.role_obj.can_create_task)
    )

    if not can_create_task_permission:
        flash('Você não tem permissão para criar tarefas para este evento.', 'danger')
        abort(403) # Forbidden

    form = TaskForm()
    form.event.data = event_obj

    available_task_categories = get_task_categories()
    available_task_statuses = get_task_statuses()
    available_users = get_users() # Chamada para obter usuários

    if not available_task_statuses:
        flash("Nenhum status de tarefa disponível. Por favor, crie pelo menos um status do tipo 'Tarefa' na administração (Ex: Pendente, Concluída, etc.)", 'warning')
    if not available_task_categories:
        flash('Nenhuma categoria de tarefa disponível. Por favor, crie pelo menos uma categoria na administração.', 'warning')
    if not available_users:
        flash('Não há usuários ativos cadastrados no sistema para atribuir tarefas. Crie usuários ou ative-os no painel de administração.', 'warning')

    if form.validate_on_submit():
        print(f"--- DEBUG: new_task - Formulário validado com sucesso! ---")
        try:
            # Busca os objetos completos TaskCategory e Status usando os IDs do formulário
            selected_task_category_id = form.task_category.data
            task_category_obj = TaskCategory.query.get(selected_task_category_id) if selected_task_category_id != 0 else None

            selected_task_status_id = form.status.data
            task_status_obj = Status.query.get(selected_task_status_id)

            if not task_status_obj: # A categoria pode ser opcional (None)
                flash('Status de tarefa selecionado inválido.', 'danger')
                return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event_obj)

            task = Task(
                title=form.title.data,
                description=form.description.data,
                due_date=form.due_date.data,
                original_due_date=form.due_date.data,
                event=event_obj,
                task_category=task_category_obj, # Atribui o objeto TaskCategory
                task_status=task_status_obj,     # Atribui o objeto Status
                notes=form.notes.data,
                cloud_storage_link=form.cloud_storage_link.data,
                link_notes=form.link_notes.data
            )

            db.session.add(task)
            db.session.flush() # flush para que o task.id seja gerado ANTES de criar os TaskAssignment

            print(f"--- DEBUG: new_task - Tarefa adicionada à sessão e ID gerado: {task.id} ---")

            selected_assignee_ids = form.assignees.data
            print(f"--- DEBUG: new_task - Usuários selecionados no formulário (IDs): {selected_assignee_ids} ---")

            if not selected_assignee_ids:
                 print("--- DEBUG: new_task - Nenhum usuário selecionado para atribuição. ---")

            # === CORREÇÃO APLICADA AQUI ===
            # Adiciona os usuários selecionados criando objetos TaskAssignment
            for user_id in selected_assignee_ids:
                user_obj = User.query.get(user_id)
                if user_obj:
                    new_assignment = TaskAssignment(task=task, user=user_obj) # CRIA O OBJETO TaskAssignment
                    task.assignees_associations.append(new_assignment) # E O ADICIONA À RELAÇÃO CORRETA
                    print(f"--- DEBUG: new_task - Atribuindo TaskAssignment: Tarefa '{task.title}' para Usuário '{user_obj.username}' ---")
            # === FIM DA CORREÇÃO ===
            
            # Não precisamos mais do db.session.commit() aqui. Tudo será comitado no final.
            print("--- DEBUG: new_task - Atribuições processadas. Preparando para commit final. ---")

            history_description = f'Tarefa "{task.title}" criada.'
            history_new_value = {
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'status': task.task_status.name if task.task_status else 'N/A',
                'task_category': task.task_category.name if task.task_category else 'N/A',
                'event_title': task.event.title if task.event else 'N/A'
            }
            history_entry = TaskHistory(
                task_id=task.id,
                action_type='creation',
                description=history_description,
                old_value=None,
                new_value=json.dumps(history_new_value),
                user_id=current_user.id,
                comment=f"Criada por {current_user.username}"
            )
            db.session.add(history_entry)
            
            # === Unificando o commit do ChangeLogEntry com o commit principal ===
            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Task',
                record_id=task.id,
                new_data=task.to_dict(),
                description=f"Tarefa '{task.title}' criada no evento '{event_obj.title}'."
            )
            
            db.session.commit() # Commit ÚNICO para tudo!
            print("--- DEBUG: new_task - Transação comitada com sucesso! ---") # Mantido para verificar o commit final

            flash('Sua tarefa foi criada!', 'success')
            return redirect(url_for('main.event', event_id=event_obj.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao criar a tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar tarefa: {e}", exc_info=True)
            print(f"--- DEBUG: new_task - ERRO: {e} ---")
    else:
        print(f"--- DEBUG: new_task - Validação do formulário FALHOU. Erros: {form.errors} ---")
    return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event_obj)

# =========================================================================
# =========================================================================
# =========================================================================
# NOVA ROTA: task_detail (Página de detalhes completa da Tarefa)
# =========================================================================
@main.route("/task/<int:task_id>")
@login_required
def task_detail(task_id):
    # Carrega a tarefa com eager loading para anexos e seus uploaders
    task_obj = Task.query.options(
        joinedload(Task.attachments).joinedload(Attachment.uploader),
        joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Task.task_status),
        joinedload(Task.task_category),
        joinedload(Task.event).joinedload(Event.author),
        joinedload(Task.comments).joinedload(Comment.author) # Carrega comentários e seus autores
    ).get_or_404(task_id)

    event_obj = task_obj.event

    # Verificação de permissão para visualizar a tarefa
    can_view_task = False
    if current_user.is_authenticated:
        if current_user.is_admin:
            can_view_task = True
        elif event_obj.author_id == current_user.id: # Autor do evento
            can_view_task = True
        elif current_user.id in [u.id for u in task_obj.assignees]: # Atribuído à tarefa
            can_view_task = True
        else:
            # Verifica permissões específicas do evento
            for ep in event_obj.event_permissions:
                if ep.user_id == current_user.id and ep.role and ep.role.can_view_event:
                    can_view_task = True
                    break
                if ep.group and ep.group_id in [ug.group_id for ug in current_user.user_groups] and ep.role and ep.role.can_view_event:
                    can_view_task = True
                    break

    if not can_view_task:
        flash('Você não tem permissão para visualizar esta tarefa.', 'danger')
        abort(403)

    # Verificações de permissão para ações na tarefa
    can_edit_task = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.id in [u.id for u in task_obj.assignees]) or
        (current_user.role_obj and current_user.role_obj.can_edit_task)
    )

    can_delete_task = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.role_obj and current_user.role_obj.can_delete_task)
    )

    can_complete_task = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.id in [u.id for u in task_obj.assignees]) or
        (current_user.role_obj and current_user.role_obj.can_complete_task)
    )

    can_uncomplete_task = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.id in [u.id for u in task_obj.assignees]) or
        (current_user.role_obj and current_user.role_obj.can_uncomplete_task)
    )

    can_view_task_history = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.id in [u.id for u in task_obj.assignees]) or
        (current_user.role_obj and current_user.role_obj.can_view_task_history)
    )

    can_manage_task_comments = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or
        (current_user.id in [u.id for u in task_obj.assignees]) or
        (current_user.role_obj and current_user.role_obj.can_manage_task_comments)
    )

    can_upload_attachments = (
        current_user.is_admin or
        (current_user.role_obj and current_user.role_obj.can_upload_attachments)
    )

    can_manage_attachments = (
        current_user.is_admin or
        (current_user.role_obj and current_user.role_obj.can_manage_attachments)
    )

    # Formulários
    comment_form = CommentForm()
    attachment_form = AttachmentForm()

    # Calcula dias restantes para o prazo
    current_date = date.today()
    days_left = (task_obj.due_date.date() - current_date).days if task_obj.due_date else 0

    return render_template('task_detail.html',
                           title=f'Tarefa: {task_obj.title}',
                           task=task_obj,
                           event=event_obj,
                           current_date=current_date,
                           days_left=days_left,
                           can_edit_task=can_edit_task,
                           can_delete_task=can_delete_task,
                           can_complete_task=can_complete_task,
                           can_uncomplete_task=can_uncomplete_task,
                           can_view_task_history=can_view_task_history,
                           can_manage_task_comments=can_manage_task_comments,
                           can_upload_attachments=can_upload_attachments,
                           can_manage_attachments=can_manage_attachments,
                           comment_form=comment_form,
                           attachment_form=attachment_form)


# =========================================================================
# FIM DA NOVA ROTA task_detail
# =========================================================================


# =========================================================================
# ROTA PARA SERVIR ARQUIVOS DE ÁUDIO UPLOADED
# =========================================================================
@main.route("/uploads/audio/<path:filename>")
@login_required
def serve_audio_file(filename):
    """Serve arquivos de áudio uploaded."""
    # Adicione verificações de permissão mais granulares se desejar,
    # por exemplo, verificar se o current_user tem acesso ao evento/tarefa ao qual o áudio pertence.
    # Por enquanto, apenas exige login.
    return send_from_directory(current_app.config['UPLOAD_FOLDER_AUDIO'], filename)


# =========================================================================
# ATUALIZADO: Rota API para buscar E ADICIONAR comentários de uma tarefa
# AGORA SUPORTA GET e POST e espera 'content' no POST e retorna 'content'
# para GET e POST
# =========================================================================
@main.route('/api/comments/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def get_or_add_task_comments_api(task_id):
    task = Task.query.options(joinedload(Task.assignees_associations).joinedload(TaskAssignment.user), joinedload(Task.event).joinedload(Event.author)).get_or_404(task_id)

    # --- Verificação de permissão geral para comentários (GET e POST) ---
    can_manage_or_view_comments = (
        current_user.is_admin or
        task.event.author_id == current_user.id or
        current_user.id in [u.id for u in task.assignees] or # CORRIGIDO AQUI
        (current_user.role_obj and (current_user.role_obj.can_view_task_history or current_user.role_obj.can_manage_task_comments))
    )
    if not can_manage_or_view_comments:
        return jsonify({'message': 'Você não tem permissão para gerenciar comentários desta tarefa.'}), 403

    if request.method == 'GET':
        # --- Lógica GET (Buscar Comentários) ---
        comments = Comment.query.filter_by(task_id=task.id).options(joinedload(Comment.author)).order_by(Comment.timestamp.asc()).all()
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content, # Campo no seu modelo é 'content'
                'timestamp': comment.timestamp.isoformat(),
                'user': comment.author.username if comment.author else 'Usuário Desconhecido', # Nome do campo no seu modelo é 'author'
                'date': comment.timestamp.strftime('%d/%m/%Y %H:%M') # Formato para o frontend
            })
        return jsonify(comments_data)

    elif request.method == 'POST':
        # --- Lógica POST (Adicionar Comentário) ---
        # Permissão específica para adicionar (se for mais restrita que ver)
        can_add_comment = (
            current_user.is_admin or
            task.event.author_id == current_user.id or
            current_user.id in [u.id for u in task.assignees] or # CORRIGIDO AQUI
            (current_user.role_obj and current_user.role_obj.can_manage_task_comments)
        )
        if not can_add_comment:
            return jsonify({'message': 'Você não tem permissão para adicionar comentários a esta tarefa.'}), 403
        
        data = request.get_json()
        comment_text = data.get('content', '').strip() 

        if not comment_text:
            return jsonify({'message': 'O texto do comentário não pode ser vazio.'}), 400

        try:
            new_comment = Comment(
                content=comment_text,
                task_id=task.id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(new_comment)
            db.session.commit()

            # Log no ChangeLogEntry
            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Comment',
                record_id=new_comment.id,
                new_data=new_comment.to_dict(), # Adapte se new_comment.to_dict() não existir ou for diferente
                description=f"Comentário adicionado por '{current_user.username}' na tarefa '{task.title}'."
            )
            
            # =====================================================================
            # NOVO: LÓGICA DE NOTIFICAÇÕES (APÓS COMENTÁRIO ADICIONADO COM SUCESSO)
            # =====================================================================
            notification_message_template = f"'{current_user.username}' comentou na tarefa '{task.title}'."
            notification_link = url_for('main.task_detail', task_id=task.id, _external=True)

            recipients_to_notify = set() # Usar set para evitar duplicidade de usuários
            
            # 1. Notificar todos os atribuídos à tarefa (exceto o próprio autor do comentário)
            for assignee in task.assignees:
                if assignee.id != current_user.id:
                    recipients_to_notify.add(assignee)
            
            # 2. Notificar o autor do evento (se não for o autor do comentário e não estiver já na lista de atribuídos)
            if task.event.author_id != current_user.id and task.event.author not in recipients_to_notify:
                recipients_to_notify.add(task.event.author)

            for recipient in recipients_to_notify:
                # Cria notificação in-app
                create_in_app_notification(
                    user_id=recipient.id,
                    message=notification_message_template,
                    link_url=notification_link,
                    related_object_type='Task',
                    related_object_id=task.id
                )
                
                # Envia email (opcional)
                email_subject = f"[Gerenciador de Eventos] Novo Comentário na Tarefa: {task.title}"
                email_body = f"Olá {recipient.username},\n\n{current_user.username} comentou na tarefa '{task.title}' do evento '{task.event.title}'.\n\nComentário: {comment_text}\n\nPara ver o comentário e a tarefa, clique aqui: {notification_link}\n\nAtenciosamente,\nSua Equipe de Gerenciamento de Eventos"
                send_notification_email(recipient.email, email_subject, email_body)
            
            db.session.commit() # Commit das notificações in-app e do ChangeLog (se não houver um commit anterior para o ChangeLog)
            # =====================================================================
            # FIM: LÓGICA DE NOTIFICAÇÕES
            # =====================================================================

            # Retorna o comentário recém-criado para que o frontend possa atualizá-lo
            formatted_date = new_comment.timestamp.strftime('%d/%m/%Y %H:%M')
            return jsonify({
                'id': new_comment.id,
                'user': current_user.username,
                'date': formatted_date,
                'content': new_comment.content, # Agora é 'content' para consistência
                'message': 'Comentário adicionado com sucesso!'
            }), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar comentário à tarefa {task_id}: {e}", exc_info=True)
            return jsonify({'message': f'Erro interno do servidor ao adicionar comentário: {str(e)}'}), 500

# =========================================================================
# FIM DA ROTA API DE COMENTÁRIOS ATUALIZADA
# =========================================================================


# =========================================================================
# Rota para adicionar comentário a uma tarefa (foi substituída pela rota API acima)
# Esta rota /events/<int:event_id>/tasks/<int:task_id>/comments/add NÃO É MAIS NECESSÁRIA
# Está comentada para referência futura, mas o frontend não a utiliza.
# =========================================================================
# =========================================================================
# @main.route('/events/<int:event_id>/tasks/<int:task_id>/comments/add', methods=['POST'])
# @login_required
# def add_comment(event_id, task_id):
#     event = Event.query.get_or_404(event_id)
#     task = Task.query.get_or_404(task_id)

#     if not (current_user.is_admin or
#             task.event.author_id == current_user.id or
#             current_user.id in [u.id for u in task.assignees] or
#             (current_user.role_obj and current_user.role_obj.can_manage_task_comments)):
#         return jsonify({'success': False, 'message': 'Você não tem permissão para adicionar comentários.'}), 403

#     form = CommentForm()
#     if form.validate_on_submit():
#         new_comment = Comment(
#             content=form.content.data,
#             task_id=task.id,
#             user_id=current_user.id,
#             timestamp=datetime.now()
#         )
#         db.session.add(new_comment)
#         db.session.commit()

#         ChangeLogEntry.log_creation(
#             user_id=current_user.id,
#             record_type='Comment',
#             record_id=new_comment.id,
#             new_data=new_comment.to_dict(),
#             description=f"Comentário adicionado por '{current_user.username}' na tarefa '{task.title}'."
#         )
#         db.session.commit()

#         return jsonify({'success': True, 'message': 'Comentário adicionado com sucesso!'})
#     else:
#         return jsonify({'success': False, 'errors': form.errors, 'message': 'Erros de validação.'}), 400

# =========================================================================
# FIM NOVAS ROTAS DE COMENTÁRIOS
# =========================================================================

@main.route("/task/<int:task_id>/update", methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task_obj = Task.query.get_or_404(task_id)
    event_obj = task_obj.event

    # Verificação de permissão para editar tarefas
    can_edit_task_permission = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_edit_task)
    )

    if not can_edit_task_permission:
        flash('Você não tem permissão para editar esta tarefa.', 'danger')
        abort(403) # Forbidden

    form = TaskForm(obj=task_obj)
    form.event.data = event_obj

    available_task_categories = get_task_categories()
    available_task_statuses = get_task_statuses()
    available_users = get_users()

    if not available_task_statuses:
        flash("Nenhum status de tarefa disponível. Por favor, crie pelo menos um status do tipo 'Tarefa' na administração (Ex: Pendente, Concluída, etc.)", 'warning')
    if not available_task_categories:
        flash('Nenhuma categoria de tarefa disponível. Por favor, crie pelo menos uma categoria na administração.', 'warning')
    if not available_users:
        flash('Não há usuários ativos cadastrados no sistema para atribuir tarefas. Crie usuários ou ative-os no painel de administração.', 'warning')

    if request.method == 'GET':
        # Preenche os campos do formulário com os dados existentes para o método GET
        form.title.data = task_obj.title
        form.description.data = task_obj.description
        form.notes.data = task_obj.notes
        form.due_date.data = task_obj.due_date
        form.cloud_storage_link.data = task_obj.cloud_storage_link
        form.link_notes.data = task_obj.link_notes

        # Preenche o SelectField para task_category com o ID
        form.task_category.data = task_obj.task_category.id if task_obj.task_category else 0
        # Preenche o SelectMultipleField para assignees com uma lista de IDs
        form.assignees.data = [u.id for u in task_obj.assignees]
        # Preenche o SelectField para status com o ID
        form.status.data = task_obj.task_status.id if task_obj.task_status else None
    
    if form.validate_on_submit():
        print(f"--- DEBUG: update_task - Formulário validado com sucesso! ---")
        try:
            old_task_data_for_changelog = task_obj.to_dict()

            old_task_data_for_history = {
                'title': task_obj.title,
                'description': task_obj.description,
                'notes': task_obj.notes,
                'due_date': task_obj.due_date,
                'task_status_id': task_obj.task_status_id,
                'task_category_id': task_obj.task_category_id,
                'cloud_storage_link': task_obj.cloud_storage_link,
                'link_notes': task_obj.link_notes,
                'assignees_ids': sorted([u.id for u in task_obj.assignees]) if task_obj.assignees else []
            }
            old_status_name = task_obj.task_status.name if task_obj.task_status else 'N/A'
            old_category_name = task_obj.task_category.name if task_obj.task_category else 'N/A'
            old_assignee_names = sorted([u.username for u in task_obj.assignees]) if task_obj.assignees else []

            task_obj.title = form.title.data
            task_obj.description = form.description.data
            task_obj.notes = form.notes.data
            task_obj.due_date = form.due_date.data # DateTimeField agora
            task_obj.cloud_storage_link = form.cloud_storage_link.data
            task_obj.link_notes = form.link_notes.data

            # --- CORREÇÃO APLICADA AQUI para task_category ---
            selected_category_id = form.task_category.data
            if selected_category_id == 0:  # Se a opção padrão "Selecione uma Categoria..." foi escolhida
                task_obj.task_category = None # Define a categoria como nula
            else:
                task_category_obj = TaskCategory.query.get(selected_category_id)
                if task_category_obj:
                    task_obj.task_category = task_category_obj
                else:
                    flash('Categoria de tarefa selecionada inválida.', 'danger')
                    return render_template('create_edit_task.html', title='Atualizar Tarefa',
                                           form=form, legend='Atualizar Tarefa', event=event_obj, task=task_obj)
            # --- FIM CORREÇÃO para task_category ---

            # --- CORREÇÃO APLICADA AQUI para task_status ---
            selected_status_id = form.status.data
            task_status_obj = Status.query.get(selected_status_id)
            if task_status_obj:
                task_obj.task_status = task_status_obj
            else:
                flash('Status de tarefa selecionado inválido.', 'danger')
                return render_template('create_edit_task.html', title='Atualizar Tarefa',
                                       form=form, legend='Atualizar Tarefa', event=event_obj, task=task_obj)
            # --- FIM CORREÇÃO para task_status ---

            # === CORREÇÃO APLICADA AQUI para assignees (relação muitos-para-muitos) ===
            selected_assignee_ids = form.assignees.data # Isso será uma lista de IDs inteiros

            # Verifica se os atribuídos mudaram para evitar operações desnecessárias
            current_assignee_ids = sorted([u.id for u in task_obj.assignees]) if task_obj.assignees else []
            assignees_changed = current_assignee_ids != sorted(selected_assignee_ids)

            if assignees_changed:
                # CORREÇÃO: Manipulando a relação assignees_associations para limpar e adicionar TaskAssignment
                task_obj.assignees_associations.clear() # Limpa as atribuições existentes na tabela de associação
                print(f"--- DEBUG: update_task - Limpas atribuições existentes para a tarefa {task_obj.id}. ---")

                if selected_assignee_ids:
                    # Busca todos os objetos User correspondentes aos IDs selecionados
                    assignee_users = User.query.filter(User.id.in_(selected_assignee_ids)).all()
                    for user_obj in assignee_users:
                        new_assignment = TaskAssignment(task=task_obj, user=user_obj) # CRIA O OBJETO TaskAssignment
                        task_obj.assignees_associations.append(new_assignment) # E O ADICIONA À RELAÇÃO CORRETA
                        print(f"--- DEBUG: update_task - Adicionando nova atribuição (TaskAssignment): Tarefa '{task_obj.title}' para Usuário '{user_obj.username}' ---")
                else:
                    print("--- DEBUG: update_task - Nenhum usuário selecionado para atribuição. ---")
            # === FIM DA CORREÇÃO ===

            # db.session.commit() # Removido commit intermediário. Tudo será comitado no final.
            print("--- DEBUG: update_task - Transação principal de dados processada. Preparando para histórico e commit final. ---")

            new_task_data_for_changelog = task_obj.to_dict()

            new_task_data_for_history = {
                'title': task_obj.title,
                'description': task_obj.description,
                'notes': task_obj.notes,
                'due_date': task_obj.due_date,
                'task_status_id': task_obj.task_status_id,
                'task_category_id': task_obj.task_category_id,
                'cloud_storage_link': task_obj.cloud_storage_link,
                'link_notes': task_obj.link_notes,
                'assignees_ids': sorted([u.id for u in task_obj.assignees]) if task_obj.assignees else []
            }
            new_status_name = task_obj.task_status.name if task_obj.task_status else 'N/A'
            new_category_name = task_obj.task_category.name if task_obj.task_category else 'N/A'
            new_assignee_names = sorted([u.username for u in task_obj.assignees]) if task_obj.assignees else []

            changes_logged_in_history = False

            if old_task_data_for_history['title'] != new_task_data_for_history['title']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Título da tarefa alterado',
                    old_value=json.dumps({'title': old_task_data_for_history['title']}),
                    new_value=json.dumps({'title': new_task_data_for_history['title']}),
                    user_id=current_user.id,
                    comment=f"Título alterado de '{old_task_data_for_history['title']}' para '{new_task_data_for_history['title']}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['description'] != new_task_data_for_history['description']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Descrição da tarefa alterada',
                    old_value=json.dumps({'description': old_task_data_for_history['description']}),
                    new_value=json.dumps({'description': new_task_data_for_history['description']}),
                    user_id=current_user.id,
                    comment=f"Descrição alterada."
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['notes'] != new_task_data_for_history['notes']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Notas da tarefa alteradas',
                    old_value=json.dumps({'notes': old_task_data_for_history['notes']}),
                    new_value=json.dumps({'notes': new_task_data_for_history['notes']}),
                    user_id=current_user.id,
                    comment=f"Notas alteradas."
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            old_due_date_str = old_task_data_for_history['due_date'].strftime('%Y-%m-%d %H:%M') if old_task_data_for_history['due_date'] else None
            new_due_date_str = new_task_data_for_history['due_date'].strftime('%Y-%m-%d %H:%M') if new_task_data_for_history['due_date'] else None

            if old_due_date_str != new_due_date_str:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Data de vencimento alterada',
                    old_value=json.dumps({'due_date': old_due_date_str}),
                    new_value=json.dumps({'due_date': new_due_date_str}),
                    user_id=current_user.id,
                    comment=f"Data de vencimento alterada de '{old_due_date_str or 'N/A'}' para '{new_due_date_str or 'N/A'}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['task_status_id'] != new_task_data_for_history['task_status_id']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Status da tarefa alterado',
                    old_value=json.dumps({'status': old_status_name}),
                    new_value=json.dumps({'status': new_status_name}),
                    user_id=current_user.id,
                    comment=f"Status alterado de '{old_status_name}' para '{new_status_name}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['task_category_id'] != new_task_data_for_history['task_category_id']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Categoria da tarefa alterada',
                    old_value=json.dumps({'task_category': old_category_name}),
                    new_value=json.dumps({'task_category': new_category_name}),
                    user_id=current_user.id,
                    comment=f"Categoria da tarefa alterada de '{old_category_name}' para '{new_category_name}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['cloud_storage_link'] != new_task_data_for_history['cloud_storage_link']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Link de armazenamento na nuvem alterado',
                    old_value=json.dumps({'link': old_task_data_for_history['cloud_storage_link']}),
                    new_value=json.dumps({'link': new_task_data_for_history['cloud_storage_link']}),
                    user_id=current_user.id,
                    comment=f"Link de armazenamento alterado."
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if old_task_data_for_history['link_notes'] != new_task_data_for_history['link_notes']:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Notas do link alteradas',
                    old_value=json.dumps({'notes': old_task_data_for_history['link_notes']}),
                    new_value=json.dumps({'notes': new_task_data_for_history['link_notes']}),
                    user_id=current_user.id,
                    comment=f"Notas do link alteradas."
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            if assignees_changed:
                history_entry = TaskHistory(
                    task_id=task_obj.id,
                    action_type='updated',
                    description='Responsáveis pela tarefa alterados',
                    old_value=json.dumps({'assignees': old_assignee_names}),
                    new_value=json.dumps({'assignees': new_assignee_names}),
                    user_id=current_user.id,
                    comment=f"Responsáveis alterados de '{', '.join(old_assignee_names) or 'Nenhum'}' para '{', '.join(new_assignee_names) or 'Nenhum'}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            # if changes_logged_in_history: # Não precisamos mais deste if, tudo é comitado junto.
            #     db.session.commit()

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task_obj.id,
                old_data=old_task_data_for_changelog,
                new_data=new_task_data_for_changelog,
                description=f"Tarefa '{task_obj.title}' atualizada no evento '{task_obj.event.title}'."
            )
            db.session.commit() # Commit ÚNICO para tudo!

            flash('Sua tarefa foi atualizada!', 'success')
            return redirect(url_for('main.event', event_id=task_obj.event.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao atualizar a tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar tarefa: {e}", exc_info=True)
            print(f"--- DEBUG: update_task - ERRO: {e} ---")

    else:
        print(f"--- DEBUG: update_task - Validação do formulário FALHOU. Erros: {form.errors} ---")
    return render_template('create_edit_task.html', title='Atualizar Tarefa', form=form, legend='Atualizar Tarefa', task=task_obj, event=event_obj)

@main.route("/task/<int:task_id>/delete", methods=['POST'])
@login_required
def delete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)
    event_obj = task_obj.event

    # Verificação de permissão para deletar tarefas
    can_delete_task_permission = (
        current_user.is_admin or
        event_obj.author_id == current_user.id or # Comparação por ID
        (current_user.role_obj and current_user.role_obj.can_delete_task)
    )

    if not can_delete_task_permission:
        flash('Você não tem permissão para excluir esta tarefa.', 'danger')
        abort(403) # Forbidden

    try:
        old_data = task_obj.to_dict()

        if task_obj.audio_path:
            audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path)
            if os.path.exists(audio_filepath):
                os.remove(audio_filepath)
                current_app.logger.info(f"Áudio '{task_obj.audio_path}' removido para tarefa {task_id}.")

        # --- NOVO: Deletar anexos físicos e do DB associados à tarefa ---
        for attachment in task_obj.attachments:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER_ATTACHMENTS'], attachment.unique_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"Anexo '{attachment.unique_filename}' removido para tarefa {task_id}.")
            db.session.delete(attachment)
        # --- FIM NOVO ---

        db.session.delete(task_obj)
        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_id,
            old_data=old_data,
            description=f"Tarefa '{old_data.get('title', 'Título Desconhecido')}' excluída do evento '{task_obj.event.title}'."
        )
        db.session.commit()

        flash('Sua tarefa foi excluída!', 'success')
        return redirect(url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao excluir a tarefa: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao excluir tarefa: {e}", exc_info=True)
        return redirect(url_for('main.event', event_id=task_obj.event.id))

# =========================================================================
# =========================================================================
# =========================================================================
# =========================================================================
# NOVA ROTA: CONCLUIR TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/complete", methods=['POST'])
@login_required
def complete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)
    comment = request.form.get('completion_comment')

    # Autorização para concluir tarefa
    can_complete_task_permission = (
        current_user.is_admin or
        task_obj.event.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_complete_task)
    )

    if not can_complete_task_permission:
        flash('Você não tem permissão para concluir esta tarefa.', 'danger')
        abort(403)

    if task_obj.is_completed:
        flash('Esta tarefa já está concluída.', 'info')
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))

    try:
        old_data_for_changelog = task_obj.to_dict()

        task_obj.is_completed = True
        task_obj.completed_at = datetime.utcnow()
        task_obj.completed_by_id = current_user.id

        completed_status = Status.query.filter_by(name='Concluída', type='task').first()
        if completed_status:
            task_obj.task_status = completed_status
        else:
            flash("Status 'Concluída' para tarefas não encontrado, por favor, crie-o no admin.", 'warning')
        history_entry = TaskHistory(
            task_id=task_obj.id,
            action_type='conclusao',
            description=f'Tarefa "{task_obj.title}" marcada como concluída.',
            old_value=json.dumps({'is_completed': False, 'completed_at': None, 'completed_by_id': None, 'task_status': old_data_for_changelog.get('task_status_name')}),
            new_value=json.dumps({'is_completed': True, 'completed_at': task_obj.completed_at.isoformat(), 'completed_by_id': task_obj.completed_by_id, 'task_status': completed_status.name if completed_status else 'N/A'}),
            user_id=current_user.id,
            comment=comment
        )
        db.session.add(history_entry)
        db.session.commit()

        new_data_for_changelog = task_obj.to_dict()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_obj.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f"Tarefa '{task_obj.title}' concluída por {current_user.username}." + (f" Comentário: '{comment}'" if comment else '')
        )
        db.session.commit()

        flash('Tarefa concluída com sucesso!', 'success')
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao concluir a tarefa: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao concluir tarefa {task_id}: {e}", exc_info=True)
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))

# =========================================================================
# NOVA ROTA: DESFAZER CONCLUSÃO DA TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/uncomplete", methods=['POST'])
@login_required
def uncomplete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)

    # Autorização para desfazer conclusão de tarefa
    can_uncomplete_task_permission = (
        current_user.is_admin or
        task_obj.event.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_uncomplete_task)
    )

    if not can_uncomplete_task_permission:
        flash('Você não tem permissão para reverter a conclusão desta tarefa.', 'danger')
        abort(403)

    if not task_obj.is_completed:
        flash('Esta tarefa não está concluída.', 'info')
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))

    try:
        old_data_for_changelog = task_obj.to_dict()

        task_obj.is_completed = False
        task_obj.completed_at = None
        task_obj.completed_by_id = None

        pending_status = Status.query.filter_by(name='Pendente', type='task').first()
        if pending_status:
            task_obj.task_status = pending_status
        else:
            flash("Status 'Pendente' para tarefas não encontrado, por favor, crie-o no admin.", 'warning')
        history_entry = TaskHistory(
            task_id=task_obj.id,
            action_type='uncompletion',
            description=f'Tarefa "{task_obj.title}" marcada como não concluída.',
            old_value=json.dumps({'is_completed': True, 'completed_at': old_data_for_changelog.get('completed_at'), 'completed_by_id': old_data_for_changelog.get('completed_by_id'), 'task_status': old_data_for_changelog.get('task_status_name')}),
            new_value=json.dumps({'is_completed': False, 'completed_at': None, 'completed_by_id': None, 'task_status': pending_status.name if pending_status else 'N/A'}),
            user_id=current_user.id,
            comment=f"Desfeito por {current_user.username}"
        )
        db.session.add(history_entry)
        db.session.commit()

        new_data_for_changelog = task_obj.to_dict()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_obj.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f"Tarefa '{task_obj.title}' marcada como não concluída por {current_user.username}."
        )
        db.session.commit()

        flash('Tarefa marcada como não concluída!', 'info')
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao marcar a tarefa como não concluída: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao desmarcar tarefa {task_id}: {e}", exc_info=True)
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))

# =========================================================================
# NOVA ROTA: VISUALIZAR HISTÓRICO DA TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/history")
@login_required
def task_history_view(task_id):
    task_obj = Task.query.get_or_404(task_id)

    # Autorização para visualizar histórico de tarefa
    can_view_task_history_permission = (
        current_user.is_admin or
        task_obj.event.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_view_task_history)
    )

    if not can_view_task_history_permission:
        flash('Você não tem permissão para visualizar o histórico desta tarefa.', 'danger')
        abort(403)

    # Carrega o autor da entrada do histórico para exibir o nome de usuário
    history_records = task_obj.history.options(joinedload(TaskHistory.author)).order_by(TaskHistory.timestamp.desc()).all()
    return render_template('task_history.html', title=f'Histórico da Tarefa: {task_obj.title}', task=task_obj, history_records=history_records)
# =========================================================================
# FIM NOVA ROTA: VISUALIZAR HISTÓRICO DA TAREFA
# =========================================================================


# =========================================================================
# Rotas de Grupos
# =========================================================================
@main.route("/group/new", methods=['GET', 'POST'])
@login_required
@admin_required
def new_group():
    form = GroupForm()
    if form.validate_on_submit():
        group = Group(name=form.name.data, description=form.description.data)
        db.session.add(group)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'Group', group.id, new_data=group.to_dict(), description=f"Grupo '{group.name}' criado.")
        db.session.commit()
        flash('Grupo criado com sucesso!', 'success')
        return redirect(url_for('main.list_groups'))
    return render_template('create_edit_group.html', title='Novo Grupo', form=form, legend='Novo Grupo')
@main.route("/groups")
@login_required
@admin_required
def list_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template('list_groups.html', groups=groups, title='Gerenciar Grupos')

@main.route("/group/<int:group_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required
def update_group(group_id):
    group = Group.query.get_or_404(group_id)
    form = GroupForm(obj=group, original_name=group.name)
    if form.validate_on_submit():
        old_data = group.to_dict()
        group.name = form.name.data
        group.description = form.description.data
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Group', group.id, old_data=old_data, new_data=group.to_dict(), description=f"Grupo '{group.name}' atualizado.")
        db.session.commit()
        flash('Grupo atualizado com sucesso!', 'success')
        return redirect(url_for('main.list_groups'))
    elif request.method == 'GET':
        pass
    return render_template('create_edit_group.html', title='Atualizar Grupo', form=form, legend='Atualizar Grupo')

@main.route("/group/<int:group_id>/delete", methods=['POST'])
@login_required
@admin_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    if group.event_permissions.first() or group.users_in_group.first():
        flash('Não é possível excluir este grupo, pois ele está associado a permissões de eventos ou usuários. Desvincule-o primeiro.', 'danger')
        return redirect(url_for('main.list_groups'))

    old_data = group.to_dict()
    db.session.delete(group)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'Group', group.id, old_data=old_data, description=f"Grupo '{old_data.get('name', 'Nome Desconhecido')}' deletado.")
    db.session.commit()
    flash('Grupo deletado com sucesso!', 'success')
    return redirect(url_for('main.list_groups'))

@main.route("/group/<int:group_id>/members", methods=['GET', 'POST'])
@login_required
@admin_required
def manage_group_members(group_id):
    group = Group.query.get_or_404(group_id)
    form = AssignUsersToGroupForm()

    if form.validate_on_submit():
        current_member_ids = {ug.user_id for ug in group.users_in_group}
        new_member_ids = set(form.users.data) # form.users.data já é uma lista de IDs

        # Usuários a serem removidos
        for user_id_to_remove in current_member_ids - new_member_ids:
            user_group = UserGroup.query.filter_by(group_id=group.id, user_id=user_id_to_remove).first()
            if user_group:
                user_obj = User.query.get(user_id_to_remove) # Pega o objeto User para o changelog
                db.session.delete(user_group)
                ChangeLogEntry.log_deletion(
                    user_id=current_user.id,
                    record_type='Group',
                    record_id=group.id,
                    old_data={'user_id': user_id_to_remove, 'username': user_obj.username if user_obj else 'Desconhecido'},
                    description=f"Usuário '{user_obj.username if user_obj else 'Desconhecido'}' removido do grupo '{group.name}'."
                )

        # Usuários a serem adicionados
        for user_id_to_add in new_member_ids - current_member_ids:
            user_obj = User.query.get(user_id_to_add) # Pega o objeto User
            if user_obj:
                user_group = UserGroup(group=group, user=user_obj)
                db.session.add(user_group)
                ChangeLogEntry.log_creation(
                        user_id=current_user.id,
                        record_type='Group',
                        record_id=group.id,
                        new_data={'user_id': user_id_to_add, 'username': user_obj.username},
                        description=f"Usuário '{user_obj.username}' adicionado ao grupo '{group.name}'."
                    )

        db.session.commit()
        flash('Membros do grupo atualizados com sucesso!', 'success')
        return redirect(url_for('main.manage_group_members', group_id=group.id))
    elif request.method == 'GET':
        form.users.data = [ug.user_id for ug in group.users_in_group] # Preenche com IDs
        # Lembre-se que o AssignUsersToGroupForm usa MultipleCheckboxField.
        # Se você estiver usando um Select2 aqui, esta linha de preenchimento de .data
        # funcionará, mas a renderização no template pode precisar de um loop
        # como o que sugeri para o create_edit_task.html antes da mudança para Select2.

    return render_template('manage_group_members.html', title=f'Membros do Grupo: {group.name}', group=group, form=form)
# =========================================================================
# Rotas de Permissões de Eventos
# =========================================================================
@main.route("/event/<int:event_id>/permissions", methods=['GET', 'POST'])
@login_required
def manage_event_permissions(event_id):
    event_obj = Event.query.get_or_404(event_id)

    # Verificação de permissão para gerenciar permissões
    can_manage = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id: # Comparação por ID
            can_manage = True
        elif current_user.is_admin: # Admins podem sempre gerenciar
            can_manage = True
        else:
            # Verifica permissão individual
            if EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.user_id == current_user.id,
                    EventPermission.role.has(Role.can_manage_permissions == True)
                )
            ).first():
                can_manage = True
            # Verifica permissão via grupo
            user_group_ids = [ug.group_id for ug in current_user.user_groups]
            if user_group_ids and EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.group_id.in_(user_group_ids),
                    EventPermission.role.has(Role.can_manage_permissions == True)
                )
            ).first():
                can_manage = True

    if not can_manage:
        abort(403) # Forbidden

    form = EventPermissionForm()
    form.event.data = event_obj # Preenche o campo de evento do formulário

    if form.validate_on_submit():
        user_id = form.user.data if form.user.data != 0 else None # Converte 0 para None
        group_id = form.group.data if form.group.data != 0 else None # Converte 0 para None
        role_obj = Role.query.get(form.role.data) # Obter o objeto Role

        existing_permission = EventPermission.query.filter(
            and_(
                EventPermission.event_id == event_obj.id,
                or_(
                    (EventPermission.user_id == user_id) if user_id else false(), # Comparação por ID
                    (EventPermission.group_id == group_id) if group_id else false() # Comparação por ID
                )
            )
        ).first()

        if existing_permission:
            old_data = existing_permission.to_dict()
            existing_permission.role = role_obj # Atualiza a role
            db.session.commit()
            target_name = (User.query.get(user_id).username if user_id else Group.query.get(group_id).name) if (user_id or group_id) else "N/A"
            ChangeLogEntry.log_update(current_user.id, 'EventPermission', existing_permission.id, old_data=old_data, new_data=existing_permission.to_dict(), description=f"Permissão para {target_name} no evento '{event_obj.title}' atualizada para a role '{role_obj.name}'.")
            flash('Permissão atualizada com sucesso!', 'success')
        else:
            user_obj = User.query.get(user_id) if user_id else None
            group_obj = Group.query.get(group_id) if group_id else None
            
            permission = EventPermission(event=event_obj, user=user_obj, group=group_obj, role=role_obj) # Atribui a role
            db.session.add(permission)
            db.session.commit()
            target_name = (user_obj.username if user_obj else group_obj.name) if (user_obj or group_obj) else "N/A"
            ChangeLogEntry.log_creation(current_user.id, 'EventPermission', permission.id, new_data=permission.to_dict(), description=f"Permissão para {target_name} no evento '{event_obj.title}' criada com a role '{role_obj.name}'.")
            flash('Permissão adicionada com sucesso!', 'success')
        db.session.commit() # Commit final após log
        return redirect(url_for('main.manage_event_permissions', event_id=event_obj.id))

    permissions = EventPermission.query.filter_by(event=event_obj).all()
    return render_template('manage_event_permissions.html', title=f'Gerenciar Permissões: {event_obj.title}', event=event_obj, form=form, permissions=permissions)

@main.route("/event_permission/<int:permission_id>/delete", methods=['POST'])
@login_required
def delete_event_permission(permission_id):
    permission = EventPermission.query.get_or_404(permission_id)
    event_obj = permission.event

    # Verificação de permissão para gerenciar permissões
    can_manage = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id: # Comparação por ID
            can_manage = True
        elif current_user.is_admin:
            can_manage = True
        else:
            if EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.user_id == current_user.id,
                    EventPermission.role.has(Role.can_manage_permissions == True)
                )
            ).first():
                can_manage = True
            user_group_ids = [ug.group_id for ug in current_user.user_groups]
            if user_group_ids and EventPermission.query.filter(
                and_(
                    EventPermission.event_id == event_obj.id,
                    EventPermission.group_id.in_(user_group_ids),
                    EventPermission.role.has(Role.can_manage_permissions == True)
                )
            ).first():
                can_manage = True

    if not can_manage:
        abort(403)

    event_id = event_obj.id

    if permission.user:
        target_name = permission.user.username
    elif permission.group:
        target_name = permission.group.name
    else:
        target_name = "usuário/grupo desconhecido"

    event_title = permission.event.title

    old_data = permission.to_dict()

    db.session.delete(permission)

    ChangeLogEntry.log_deletion(
        current_user.id,
        'EventPermission',
        permission_id,
        old_data=old_data,
        description=f"Permissão para {target_name} no evento '{event_title}' deletada."
    )

    db.session.commit()

    flash('Permissão removida com sucesso!', 'success')
    return redirect(url_for('main.manage_event_permissions', event_id=event_id))

# =========================================================================
# Rotas de ChangeLog (Auditoria)
# =========================================================================
@main.route("/changelog")
@login_required
@admin_required
def changelog():
    page = request.args.get('page', 1, type=int)

    changelogs_pagination = ChangeLogEntry.query.order_by(ChangeLogEntry.timestamp.desc()).paginate(
        page=page, per_page=LOGS_PER_PAGE, error_out=False
    )

    serialized_changelogs_items = []

    for log_entry in changelogs_pagination.items:
        old_data = log_entry.old_data if log_entry.old_data is not None else {}
        new_data = log_entry.new_data if log_entry.new_data is not None else {}

        differences = diff_dicts(old_data, new_data)

        log_data_for_js = {
            'id': log_entry.id,
            'user': log_entry.user.username if log_entry.user else 'Desconhecido',
            'timestamp': log_entry.timestamp.isoformat(),
            'record_type': log_entry.record_type,
            'record_id': log_entry.record_id,
            'action': log_entry.action,
            'description': log_entry.description,
            'old_data': old_data,
            'new_data': new_data,
            'differences': differences
        }
        serialized_changelogs_items.append(log_data_for_js)

    return render_template(
        'changelog.html',
        title='Histórico de Alterações',
        changelogs=changelogs_pagination,
        serialized_changelogs_items=serialized_changelogs_items
    )


# Rota para o painel administrativo
@main.route('/admin_panel')
@login_required
@admin_required
def admin_panel():
    return render_template('admin_panel.html', title='Painel Administrativo')

# Rotas de Gerenciamento de Usuários
@main.route('/admin/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template('list_users.html', title='Gerenciar Usuários', users=users)

@main.route('/admin/user/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    form = UserForm(is_new_user=True)

    if form.validate_on_submit():
        print(f"--- DEBUG: new_user - Formulário validado com sucesso! ---")
        try:
            # form.role_obj.data já é o objeto Role
            user_role = form.role_obj.data
            if not user_role: # Redundante se o campo é DataRequired, mas seguro.
                flash(f'Erro: O papel não foi encontrado ou selecionado.', 'danger')
                return render_template('create_edit_user.html', title='Novo Usuário', form=form, legend='Criar Novo Usuário')

            user = User(username=form.username.data, email=form.email.data, role_obj=user_role)
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()
            print(f"--- DEBUG: new_user - Usuário '{user.username}' criado com sucesso! ---")

            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='User',
                record_id=user.id,
                new_data=user.to_dict(),
                description=f"Usuário '{user.username}' (ID: {user.id}) criado."
            )
            db.session.commit()

            flash(f"Usuário '{user.username}' criado com sucesso!", 'success')
            return redirect(url_for('main.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar usuário: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar usuário: {e}", exc_info=True)
            print(f"--- DEBUG: new_user - ERRO: {e} ---")
    else:
        print(f"--- DEBUG: new_user - Validação do formulário FALHOU. Erros: {form.errors} ---")

    return render_template('create_edit_user.html', title='Novo Usuário', form=form, legend='Criar Novo Usuário')

@main.route('/admin/user/<int:user_id>/update', methods=['GET', 'POST'])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    # Passa o objeto Role do usuário para o formulário
    form = UserForm(obj=user, original_username=user.username, original_email=user.email, is_new_user=False, role_obj=user.role_obj)
    if form.validate_on_submit():
        print(f"--- DEBUG: update_user - Formulário validado com sucesso! ---")
        try:
            old_data = user.to_dict()

            user.username = form.username.data
            user.email = form.email.data

            # form.role_obj.data já é o objeto Role
            new_role_obj = form.role_obj.data
            if not new_role_obj: # Redundante se o campo é DataRequired, mas seguro.
                flash(f'Erro: O papel não foi encontrado ou selecionado.', 'danger')
                return render_template('create_edit_user.html', title='Atualizar Usuário', form=form, legend='Atualizar Usuário', user=user)
            user.role_obj = new_role_obj

            if form.password.data:
                user.set_password(form.password.data)

            db.session.commit()

            new_data = user.to_dict()

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='User',
                record_id=user.id,
                old_data=old_data,
                new_data=new_data,
                description=f"Usuário '{user.username}' (ID: {user.id}) editado. Nova role: {user.role_obj.name}."
            )
            db.session.commit()

            flash(f"Usuário '{user.username}' atualizado com sucesso!", 'success')
            return redirect(url_for('main.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao atualizar usuário: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar usuário: {e}", exc_info=True)
            print(f"--- DEBUG: update_user - ERRO: {e} ---")
    else:
        print(f"--- DEBUG: update_task - Validação do formulário FALHOU. Erros: {form.errors} ---")
    return render_template('create_edit_user.html', title='Atualizar Usuário', form=form, legend='Atualizar Usuário', user=user)

@main.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Você não pode deletar sua própria conta através do painel de administração.', 'danger')
        return redirect(url_for('main.list_users'))

    if Event.query.filter_by(author=user).first() or TaskAssignment.query.filter_by(user=user).first() or Comment.query.filter_by(author=user).first(): # Verifica se o usuário é autor de comentários
        flash(f"Não é possível deletar o usuário '{user.username}' porque ele está associado a eventos, tarefas ou comentários. Desvincule-o primeiro.", 'danger')
        return redirect(url_for('main.list_users'))

    try:
        old_data = user.to_dict()

        db.session.delete(user)

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='User',
            record_id=user_id,
            old_data=old_data,
            description=f"Usuário '{old_data.get('username', 'Nome Desconhecido')}' (ID: {user_id}) deletado."
        )
        db.session.commit()

        flash(f"Usuário '{user.username}' deletado com sucesso!", 'success')
        return redirect(url_for('main.list_users'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao deletar usuário: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao deletar usuário: {e}", exc_info=True)
        return redirect(url_for('main.list_users'))

# Rotas de teste (apenas para desenvolvimento)
@main.route("/teste")
def teste():
    return render_template("teste.html")

@main.route("/teste2")
def teste2():
    return "<h1>Olá do Teste 2!</h1>"

# --- NOVAS ROTAS DE API PARA GERENCIAMENTO DE ÁUDIO EM TAREFAS ---
@main.route("/api/task/<int:task_id>/upload_audio", methods=['POST'])
@login_required
def upload_task_audio(task_id):
    task_obj = Task.query.get_or_404(task_id)

    # Autorização para upload de áudio
    can_upload_task_audio_permission = (
        current_user.is_admin or
        task_obj.event.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_upload_task_audio)
    )

    if not can_upload_task_audio_permission:
        return jsonify({'message': 'Você não tem permissão para adicionar áudio a esta tarefa.'}), 403

    if 'audio_file' not in request.files:
        return jsonify({'message': 'Nenhum arquivo de audio fornecido.'}), 400

    audio_file = request.files['audio_file']
    audio_duration = request.form.get('duration_seconds', type=int)

    if audio_file.filename == '':
        return jsonify({'message': 'Nenhum arquivo selecionado.'}), 400

    if audio_file and audio_duration is not None:
        unique_filename = f"{uuid.uuid4()}.{secure_filename(audio_file.filename).rsplit('.', 1)[1].lower()}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], unique_filename)

        try:
            old_task_data_for_history = {
                'audio_path': task_obj.audio_path,
                'audio_duration_seconds': task_obj.audio_duration_seconds
            }
            if task_obj.audio_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path)):
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path))

            audio_file.save(upload_path)

            old_data_for_changelog = task_obj.to_dict()

            task_obj.audio_path = unique_filename
            task_obj.audio_duration_seconds = audio_duration
            db.session.commit()

            history_entry = TaskHistory(
                task_id=task_obj.id,
                action_type='audio_updated',
                description='Áudio da tarefa atualizado',
                old_value=json.dumps(old_task_data_for_history),
                new_value=json.dumps({
                    'audio_path': unique_filename,
                    'audio_duration_seconds': audio_duration
                }),
                user_id=current_user.id,
                comment=f"Áudio de {audio_duration}s adicionado/atualizado na tarefa."
            )
            db.session.add(history_entry)
            db.session.commit()

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task_obj.id,
                old_data=old_data_for_changelog,
                new_data=task_obj.to_dict(), # Usar task_obj.to_dict() para new_data atualizado
                description=f"Áudio adicionado/atualizado na tarefa '{task_obj.title}'. Duração: {audio_duration}s."
            )
            db.session.commit()

            return jsonify({
                'message': 'Áudio salvo com sucesso!',
                'audio_filename': unique_filename,
                'audio_url_base': url_for('main.serve_audio_file', filename=unique_filename)
            }), 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar áudio da tarefa {task_id}: {e}", exc_info=True)
            return jsonify({'message': f'Erro ao salvar áudio: {str(e)}'}), 500

    return jsonify({'message': 'Requisição inválida.'}), 400

@main.route("/api/task/<int:task_id>/delete_audio", methods=['DELETE'])
@login_required
def delete_task_audio(task_id):
    task_obj = Task.query.get_or_404(task_id)

    # Autorização para deletar áudio
    can_delete_task_audio_permission = (
        current_user.is_admin or
        task_obj.event.author_id == current_user.id or # Comparação por ID
        (current_user.id in [u.id for u in task_obj.assignees]) or # CORRIGIDO AQUI
        (current_user.role_obj and current_user.role_obj.can_delete_task_audio)
    )

    if not can_delete_task_audio_permission:
        flash('Você não tem permissão para remover áudio desta tarefa.', 'danger')
        return jsonify({'message': 'Você não tem permissão para remover áudio desta tarefa.'}), 403

    if not task_obj.audio_path:
        return jsonify({'message': 'Nenhum áudio para remover nesta tarefa.'}), 404

    audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path)

    try:
        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)

        old_data_for_changelog = task_obj.to_dict()
        
        # Registra no histórico de tarefas
        history_entry = TaskHistory(
            task_id=task_obj.id,
            action_type='audio_deleted',
            description='Áudio da tarefa excluído',
            old_value=json.dumps({'audio_path': task_obj.audio_path, 'audio_duration_seconds': task_obj.audio_duration_seconds}),
            new_value=json.dumps({'audio_path': None, 'audio_duration_seconds': None}),
            user_id=current_user.id,
            comment=f"Áudio '{task_obj.audio_path}' excluído da tarefa."
        )
        db.session.add(history_entry)

        task_obj.audio_path = None
        task_obj.audio_duration_seconds = None
        db.session.commit()

        new_data_for_changelog = task_obj.to_dict()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_obj.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f"Áudio excluído da tarefa '{task_obj.title}'."
        )
        db.session.commit()

        return jsonify({'message': 'Áudio removido com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar áudio da tarefa {task_id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao deletar áudio: {str(e)}'}), 500


# =========================================================================
# =========================================================================
# NOVAS ROTAS PARA ANEXOS DE TAREFAS
# =========================================================================

# Rota para servir arquivos de anexo (para download)
@main.route("/uploads/attachments/<path:filename>")
@login_required
def serve_attachment_file(filename):
    # ATENÇÃO: Aqui você pode adicionar lógica de permissão mais granulares se desejar,
    # por exemplo, verificar se o current_user tem acesso ao evento/tarefa ao qual o anexo pertence.
    # Por enquanto, apenas exige login.
    return send_from_directory(current_app.config['UPLOAD_FOLDER_ATTACHMENTS'], filename)


@main.route("/task/<int:task_id>/attachment/upload", methods=['POST'])
@login_required
@permission_required('can_upload_attachments')
def upload_attachment(task_id):
    task_obj = Task.query.get_or_404(task_id)
    form = AttachmentForm()

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        
        # Validar tamanho do arquivo (ex: 20MB) - Boa prática de segurança
        MAX_FILE_SIZE_MB = 20 # Alterado para 20MB
        
        # Gerar um nome de arquivo único para evitar colisões
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = str(uuid.uuid4()) + ('.' + file_extension if file_extension else '')
        
        # Definir o caminho completo para salvar o arquivo
        upload_folder_path = current_app.config['UPLOAD_FOLDER_ATTACHMENTS']
        os.makedirs(upload_folder_path, exist_ok=True) # Garante que a pasta exista
        upload_path = os.path.join(upload_folder_path, unique_filename)
        
        try:
            file.save(upload_path) # Salva o arquivo no sistema de arquivos

            # Verifica o tamanho real do arquivo APÓS salvar para maior precisão
            actual_filesize = os.path.getsize(upload_path)
            if actual_filesize > MAX_FILE_SIZE_MB * 1024 * 1024:
                os.remove(upload_path) # Deleta o arquivo se for muito grande
                flash(f'O arquivo excede o tamanho máximo permitido de {MAX_FILE_SIZE_MB}MB.', 'danger')
                return redirect(url_for('main.task_detail', task_id=task_obj.id))

            # Criar registro no banco de dados
            attachment = Attachment(
                task_id=task_obj.id,
                filename=filename,
                unique_filename=unique_filename,
                storage_path=upload_path, # Guarda o caminho no servidor
                mimetype=file.mimetype,
                filesize=actual_filesize, # Usar o tamanho real
                uploaded_by_user_id=current_user.id
            )
            db.session.add(attachment)
            db.session.commit()

            # Log da criação do anexo
            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Attachment',
                record_id=attachment.id,
                new_data=attachment.to_dict(),
                description=f"Anexo '{filename}' adicionado à tarefa '{task_obj.title}' por {current_user.username}."
            )
            db.session.commit()
            
            # Mensagem de sucesso e REDIRECIONAMENTO
            flash('Anexo enviado com sucesso!', 'success')
            return redirect(url_for('main.task_detail', task_id=task_obj.id))

        except Exception as e:
            db.session.rollback()
            # Se houve erro no DB, tentar remover o arquivo físico se ele foi salvo
            if os.path.exists(upload_path):
                os.remove(upload_path)
            current_app.logger.error(f"Erro ao salvar anexo para tarefa {task_obj.id}: {e}", exc_info=True)
            # Mensagem de erro e REDIRECIONAMENTO
            flash(f'Erro ao salvar anexo: {str(e)}', 'danger')
            return redirect(url_for('main.task_detail', task_id=task_obj.id))
    
    # Se a validação do formulário falhar (ex: nenhum arquivo selecionado)
    errors = {field: [str(error) for error in errors] for field, errors in form.errors.items()}
    # Exibe cada erro de validação do formulário com flash
    for field, field_errors in errors.items():
        for error in field_errors:
            flash(f'Erro no campo {field}: {error}', 'danger')
    # REDIRECIONAMENTO AQUI
    return redirect(url_for('main.task_detail', task_id=task_obj.id))


# Rota para download de anexo
@main.route("/attachment/<int:attachment_id>/download")
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    task_obj = attachment.task

    # Verificação de permissão para download:
    can_download = False

    if current_user.is_admin:
        can_download = True
    elif attachment.uploaded_by_user_id == current_user.id: # Uploader pode baixar seu próprio anexo
        can_download = True
    elif task_obj.event.author_id == current_user.id: # Autor do evento pode baixar
        can_download = True
    elif current_user.id in [u.id for u in task_obj.assignees]: # CORRIGIDO AQUI
        can_download = True
    elif current_user.role_obj and current_user.role_obj.can_view_event: # Tem permissão global de role para ver eventos
        can_download = True
    else:
        # Verifica permissões de visualização específicas para o evento
        for ep in task_obj.event.event_permissions:
            if ep.user_id == current_user.id and ep.role and ep.role.can_view_event:
                can_download = True
                break
            if ep.group and ep.group_id in [ug.group_id for ug in current_user.user_groups] and ep.role and ep.role.can_view_event:
                can_download = True
                break

    if not can_download:
        flash('Você não tem permissão para baixar este anexo.', 'danger')
        abort(403) # Forbidden

    try:
        # Retorna o arquivo
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER_ATTACHMENTS'],
            attachment.unique_filename,
            as_attachment=True, # Força o download
            download_name=attachment.filename # Usa o nome original do arquivo para download
        )
    except FileNotFoundError:
        flash('O arquivo de anexo não foi encontrado no servidor.', 'danger')
        current_app.logger.error(f"Arquivo de anexo não encontrado: {attachment.unique_filename}")
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        flash(f'Ocorreu um erro ao baixar o arquivo: {str(e)}', 'danger')
        current_app.logger.error(f"Erro ao servir anexo {attachment.unique_filename}: {e}", exc_info=True)
        # Redireciona para a página de detalhes da tarefa ou do evento
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))


# Rota para deletar um anexo
@main.route("/attachment/<int:attachment_id>/delete", methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    task_obj = attachment.task

    # Verificação de permissão para deletar anexo:
    can_delete = False
    if current_user.is_admin:
        can_delete = True
    elif attachment.uploaded_by_user_id == current_user.id: # Uploader pode deletar seu próprio anexo
        can_delete = True
    elif current_user.role_obj and current_user.role_obj.can_manage_attachments: # Tem permissão global de role para gerenciar anexos
        can_delete = True
    elif task_obj.event.author_id == current_user.id: # Autor do evento pode deletar anexos em suas tarefas
        can_delete = True
    
    if not can_delete:
        return jsonify({'message': 'Você não tem permissão para excluir este anexo.'}), 403

    # Tenta excluir o arquivo do sistema de arquivos
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER_ATTACHMENTS'], attachment.unique_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            current_app.logger.info(f"Arquivo de anexo '{attachment.unique_filename}' deletado do sistema de arquivos.")
        except Exception as e:
            current_app.logger.error(f"Erro ao excluir arquivo físico {file_path}: {e}", exc_info=True)
            return jsonify({'message': f'Erro ao excluir arquivo do servidor: {str(e)}'}), 500
    else:
        current_app.logger.warning(f"Tentou deletar anexo '{attachment.unique_filename}' mas o arquivo não foi encontrado no disco.")

    # Tenta excluir o registro do banco de dados
    try:
        old_data = attachment.to_dict()
        db.session.delete(attachment)
        db.session.commit()

        # Log da exclusão do anexo
        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Attachment',
            record_id=attachment.id,
            old_data=old_data,
            description=f"Anexo '{attachment.filename}' excluído da tarefa '{task_obj.title}' por {current_user.username}."
        )
        db.session.commit()

        return jsonify({'message': 'Anexo excluído com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir anexo do banco de dados {attachment.id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao excluir anexo do banco de dados: {str(e)}'}), 500


# =========================================================================
# ROTA API PARA RETORNAR EVENTOS E TAREFAS PARA O CALENDÁRIO
# =========================================================================
@main.route("/api/calendar_events", methods=['GET'])
@login_required
def calendar_events_feed():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    # Convert start and end to datetime objects
    start = datetime.fromisoformat(start_str) if start_str else None
    end = datetime.fromisoformat(end_str) if end_str else None

    events_for_calendar = []

    # --- Fetch Events ---
    # Eager loading para evitar N+1 queries e para as verificações de permissão
    events_query = Event.query.options(
        joinedload(Event.author),
        joinedload(Event.status),
        joinedload(Event.category),
        joinedload(Event.event_permissions).joinedload(EventPermission.role),
        joinedload(Event.event_permissions).joinedload(EventPermission.user),
        joinedload(Event.event_permissions).joinedload(EventPermission.group),
        joinedload(Event.tasks).joinedload(Task.assignees_associations).joinedload(TaskAssignment.user)
    )

    if not current_user.is_admin:
        # Condições para visibilidade do evento para usuários não-admin
        event_conditions = [
            Event.author_id == current_user.id,
            # Usuário é atribuído a alguma tarefa dentro do evento
            Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id)),
            # Permissão explícita para o usuário visualizar o evento
            Event.event_permissions.any(and_(
                EventPermission.user_id == current_user.id,
                EventPermission.role.has(Role.can_view_event == True)
            ))
        ]

        # Permissão explícita para os grupos do usuário visualizarem o evento
        if current_user.user_groups:
            user_group_ids = [ug.group_id for ug in current_user.user_groups]
            event_conditions.append(
                Event.event_permissions.any(and_(
                    EventPermission.group_id.in_(user_group_ids),
                    EventPermission.role.has(Role.can_view_event == True)
                ))
            )

        events_query = events_query.filter(or_(*event_conditions))

    # Filtrar por data (due_date ou end_date devem estar dentro do range do calendário)
    if start and end:
        events_query = events_query.filter(
            or_(
                # Evento começa dentro do range
                and_(Event.due_date >= start, Event.due_date <= end),
                # Evento termina dentro do range
                and_(Event.end_date >= start, Event.end_date <= end),
                # Evento abrange todo o range de datas
                and_(Event.due_date < start, Event.end_date > end),
                # Evento de um dia que cai dentro do range
                and_(Event.due_date >= start, Event.due_date <= end, Event.end_date == None)
            )
        )

    all_visible_events = events_query.all()

    for event_obj in all_visible_events:
        # Cores para Eventos
        event_color = "#3788d8" # Azul padrão
        if event_obj.status and event_obj.status.name == 'Realizado':
            event_color = "#28a745" # Verde para realizado
        elif event_obj.status and event_obj.status.name == 'Arquivado':
            event_color = "#6c757d" # Cinza para arquivado
        elif event_obj.due_date and event_obj.due_date < datetime.utcnow() and not event_obj.is_completed:
            event_color = "#dc3545" # Vermelho para atrasado (se due_date passou e não está completo)

        events_for_calendar.append({
            'id': f"event-{event_obj.id}", # Adiciona 'event-' para diferenciar de tarefas se IDs se sobrepuserem
            'title': event_obj.title,
            'start': event_obj.due_date.isoformat(),
            'end': (event_obj.end_date + timedelta(days=1)).isoformat() if event_obj.end_date else (event_obj.due_date + timedelta(days=1)).isoformat(), # FullCalendar end é exclusivo
            'url': url_for('main.event', event_id=event_obj.id),
            'color': event_color,
            'extendedProps': {
                'description': event_obj.description,
                'type': 'Evento',
                'location': event_obj.location,
                'status': event_obj.status.name if event_obj.status else 'N/A'
            },
            'allDay': not (event_obj.due_date.time() != datetime.min.time() or (event_obj.end_date and event_obj.end_date.time() != datetime.min.time()))
        })

    # --- Fetch Tasks ---
    # Tarefas visíveis são aquelas diretamente atribuídas ao usuário logado (ou todas se for admin)
    tasks_query = Task.query.options(
        joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Task.event),
        joinedload(Task.task_status)
    )

    if not current_user.is_admin:
        tasks_query = tasks_query.filter(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id))

    # Filtrar por data (apenas due_date para tarefas)
    if start and end:
        tasks_query = tasks_query.filter(
            and_(Task.due_date >= start, Task.due_date <= end)
        )

    all_visible_tasks = tasks_query.all()

    for task_obj in all_visible_tasks:
        # Cores para Tarefas
        task_color = "#ffc107" # Amarelo padrão (Pendente)
        if task_obj.is_completed:
            task_color = "#28a745" # Verde para concluído
        elif task_obj.due_date and task_obj.due_date < datetime.utcnow() and not task_obj.is_completed:
            task_color = "#dc3545" # Vermelho para atrasado
        
        events_for_calendar.append({
            'id': f"task-{task_obj.id}", # Adiciona 'task-' para diferenciar de eventos se IDs se sobrepuserem
            'title': task_obj.title,
            'start': task_obj.due_date.isoformat(),
            'end': (task_obj.due_date + timedelta(minutes=60)).isoformat(), # Padrão de 1h de duração para tarefas
            'url': url_for('main.task_detail', task_id=task_obj.id),
            'color': task_color,
            'extendedProps': {
                'description': task_obj.description,
                'type': 'Tarefa',
                'event_title': task_obj.event.title if task_obj.event else 'N/A',
                'status': task_obj.task_status.name if task_obj.task_status else 'N/A'
            },
            'allDay': not (task_obj.due_date.time() != datetime.min.time()) # Se due_date não tem parte de tempo, é allDay
        })
    
    return jsonify(events_for_calendar)

# =========================================================================
# NOVAS ROTAS DE NOTIFICAÇÕES
# =========================================================================
@main.route("/notifications")
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    
    # Marcar todas as notificações como lidas ao serem visualizadas
    # Esta é uma abordagem simples. Em sistemas maiores, pode-se usar AJAX para marcar individualmente.
    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
    db.session.commit()

    return render_template('notifications.html', title='Minhas Notificações', notifications=notifications)

@main.route("/notification/<int:notification_id>/mark_read", methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        abort(403) # Não permitir que um usuário marque a notificação de outro
    
    notification.is_read = True
    db.session.commit()
    flash('Notificação marcada como lida.', 'success')
    return redirect(url_for('main.list_notifications'))

@main.route("/api/notifications/unread_count")
@login_required
def unread_notifications_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})
# =========================================================================
# FIM: NOVAS ROTAS DE NOTIFICAÇÕES
# =========================================================================