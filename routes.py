# routes.py
# Arquivo completo e corrigido, com a linha 3281 devidamente ajustada.

from flask import render_template, url_for, flash, redirect, request, Blueprint, jsonify, current_app, abort, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from werkzeug.security import generate_password_hash
from extensions import db, mail
from datetime import datetime, date, timedelta
import json
from sqlalchemy.orm import joinedload, selectinload
import uuid
from werkzeug.utils import secure_filename
import os
from utils.changelog_utils import diff_dicts
from functools import wraps
import re
from utils.push_notification_sender import send_push_to_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, distinct, false, and_

# IMPORTAÇÕES DOS DECORATORS DO SEU NOVO ARQUIVO decorators.py
from decorators import role_required, admin_required, project_manager_required, permission_required

# IMPORTAÇÕES DE FORMS
from forms import (RegistrationForm, LoginForm, EventForm, CategoryForm, StatusForm,
                   UpdateAccountForm, RequestResetForm, ResetPasswordForm, SearchForm,
                   TaskForm, UserForm, TaskCategoryForm, GroupForm, AssignUsersToGroupForm,
                   EventPermissionForm, CommentForm, AttachmentForm)
from forms import AdminRoleForm

# IMPORTAÇÕES DE MODELS (ATUALIZADO com os novos modelos de checklist)
from models import (User, Role, Event, Task, TaskAssignment, ChangeLogEntry, Status,
                    Category, PasswordResetToken, TaskHistory, Group,
                    UserGroup, EventPermission, Comment, TaskCategory, Attachment, Notification,
                    PushSubscription, TaskSubcategory, ChecklistTemplate, ChecklistItemTemplate,
                    TaskChecklist, TaskChecklistItem, CustomFieldTypeEnum)

# Importe o objeto Flask-WTF CSRFProtect se você não o tiver configurado globalmente
from flask_wtf.csrf import generate_csrf

# <<<--- DEFINIÇÃO DO BLUEPRINT 'MAIN' --->>>
main = Blueprint('main', __name__, static_folder='static')


# =========================================================================================
# ROTAS DA APLICAÇÃO (AGORA PARTE DO BLUEPRINT 'MAIN')
# =========================================================================================

# =========================================================================================
# ROTAS PARA APROVAÇÃO/REPROVAÇÃO DE ARTE EM ANEXOS
# =========================================================================================

@main.route('/attachment/<int:attachment_id>/approve_art', methods=['POST'])
@login_required
@permission_required('can_approve_art') # Usando o decorator consolidado
def approve_attachment_art(attachment_id):
    """
    Rota para aprovar a arte de um anexo.
    Requer permissão can_approve_art.
    """
    attachment = Attachment.query.get_or_404(attachment_id)

    feedback_data = request.get_json()
    art_feedback = feedback_data.get('feedback', '').strip()

    old_data_for_log = attachment.to_dict() # Capture all old data for comprehensive log
    
    attachment.art_approval_status = 'approved'
    attachment.art_approved_by_id = current_user.id
    attachment.art_approval_timestamp = datetime.utcnow()
    attachment.art_feedback = art_feedback if art_feedback else None

    try:
        db.session.add(attachment) # Add if it's not already tracked or state changed
        db.session.commit()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Attachment',
            record_id=attachment.id,
            old_data=old_data_for_log,
            new_data=attachment.to_dict(), # Capture all new data
            description=f'Arte do anexo "{attachment.filename}" aprovada.'
        )
        db.session.commit()

        flash(f'Arte do anexo "{attachment.filename}" aprovada com sucesso!', 'success')
        return jsonify({'success': True, 'message': 'Arte aprovada!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao aprovar arte do anexo {attachment_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Erro ao aprovar arte: {str(e)}'}), 500


@main.route('/attachment/<int:attachment_id>/reject_art', methods=['POST'])
@login_required
@permission_required('can_approve_art') # Usando o decorator consolidado
def reject_attachment_art(attachment_id):
    """
    Rota para reprovar a arte de um anexo.
    Requer permissão can_approve_art.
    """
    attachment = Attachment.query.get_or_404(attachment_id)

    feedback_data = request.get_json()
    art_feedback = feedback_data.get('feedback', '').strip()

    old_data_for_log = attachment.to_dict()

    attachment.art_approval_status = 'rejected'
    attachment.art_approved_by_id = current_user.id
    attachment.art_approval_timestamp = datetime.utcnow()
    attachment.art_feedback = art_feedback if art_feedback else 'Reprovado sem feedback específico.'

    try:
        db.session.add(attachment)
        db.session.commit()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Attachment',
            record_id=attachment.id,
            old_data=old_data_for_log,
            new_data=attachment.to_dict(),
            description=f'Arte do anexo "{attachment.filename}" reprovada.'
        )
        db.session.commit()

        flash(f'Arte do anexo "{attachment.filename}" reprovada com sucesso!', 'danger')
        return jsonify({'success': True, 'message': 'Arte reprovada!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao reprovar arte do anexo {attachment_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Erro ao reprovar arte: {str(e)}'}), 500


# =========================================================================
# FUNÇÕES AUXILIARES DE NOTIFICAÇÃO
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
        # Nao commit aqui, espera o commit da transacao maior
        current_app.logger.info(f"Notificação in-app criada para user {user_id}: '{message[:50]}'.")
        return True
    except Exception as e:
        db.session.rollback() # Rollback para a notificação em caso de erro
        current_app.logger.error(f"Erro ao criar notificação in-app para user {user_id}: {e}", exc_info=True)
        return False
# =========================================================================
# FIM: FUNÇÕES AUXILIARES DE NOTIFICAÇÃO
# =========================================================================

# Defina quantos itens você quer por página (para o ChangeLog)
LOGS_PER_PAGE = 10

# =========================================================================
# Função auxiliar para verificar se um usuário pode visualizar um evento
# =========================================================================
def _can_view_event_helper(user, event):
    # 1. Admin sempre pode ver
    if user.is_admin:
        return True
    # 2. Usuário é o autor do evento
    if user.id == event.author_id:
        return True
    # 3. Usuário está atribuído a alguma tarefa dentro do evento
    if any(assignment.user_id == user.id for task in event.tasks for assignment in task.assignees_associations):
        return True
    # 4. Há uma permissão direta (user-only) para o usuário neste evento
    direct_permission = next((p for p in event.event_permissions if p.user_id == user.id), None)
    if direct_permission:
        return True
    
    return False

# =========================================================================
# FUNÇÃO AUXILIAR PARA ENVIAR E-MAIL DE REDEFINIÇÃO DE SENHA
# =========================================================================
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


# --- FUNÇÃO AUXILIAR PARA FILTRAGEM E PAGINAÇÃO DE EVENTOS ---
def get_filtered_events(user, search_query, page, per_page, event_filter_type=None, publication_status='all'):
    """
    Função auxiliar para construir a query de eventos com base no status, pesquisa e permissões do usuário.
    Retorna um objeto de paginação de eventos.
    event_filter_type: None (Home), 'Ativo', 'Realizado', 'Arquivado'
    publication_status: 'all', 'published', 'unpublished' # NOVO
    """
    current_app.logger.debug(f"\n--- DEBUG get_filtered_events para {user.username} (Admin: {user.is_admin}) --- ")
    current_app.logger.debug(f"--- DEBUG: event_filter_type solicitado: {event_filter_type} --- ")
    current_app.logger.debug(f"--- DEBUG: publication_status solicitado: {publication_status} --- ")
    base_query = Event.query.options(
        joinedload(Event.event_status),
        joinedload(Event.category),
        joinedload(Event.author),
        joinedload(Event.event_permissions),
        joinedload(Event.tasks).joinedload(Task.assignees_associations)
    )

    if not user.is_authenticated:
        current_app.logger.debug("--- DEBUG: Usuário não autenticado. Retornando query vazia. ---")
        return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)

    base_query = base_query.filter(Event.is_cancelled == False)
    current_app.logger.debug("--- DEBUG: Filtrando por Event.is_cancelled == False ---")

    active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
    realizado_status_obj = Status.query.filter_by(name='Realizado', type='event').first()
    arquivado_status_obj = Status.query.filter_by(name='Arquivado', type='event').first()

    if not active_status_obj:
        current_app.logger.warning("Status 'Ativo' para eventos não encontrado. Eventos podem não ser filtrados corretamente.")
        flash("Status 'Ativo' para eventos não encontrado. Por favor, crie-o na administração (tipo 'event').", 'danger')
        return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)

    if user.is_admin:
        current_app.logger.debug("--- DEBUG: Lógica para ADMINISTRADOR --- ")
        if event_filter_type == 'Ativo':
            if active_status_obj:
                base_query = base_query.filter(Event.event_status == active_status_obj)
                current_app.logger.debug(f"--- DEBUG: Admin filtrando por status 'Ativo' (ID: {active_status_obj.id}). ---")
        elif event_filter_type == 'Realizado':
            if realizado_status_obj:
                base_query = base_query.filter(Event.event_status == realizado_status_obj)
                current_app.logger.debug(f"--- DEBUG: Admin filtrando por status 'Realizado' (ID: {realizado_status_obj.id}). ---")
            else:
                flash("Status 'Realizado' para eventos não encontrado.", 'warning')
                current_app.logger.debug("--- DEBUG: Admin tentou filtrar por 'Realizado' mas status não encontrado. ---")
                return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)
        elif event_filter_type == 'Arquivado':
            if arquivado_status_obj:
                base_query = base_query.filter(Event.event_status == arquivado_status_obj)
                current_app.logger.debug(f"--- DEBUG: Admin filtrando por status 'Arquivado' (ID: {arquivado_status_obj.id}). ---")
            else:
                flash("Status 'Arquivado' para eventos não encontrado.", 'warning')
                current_app.logger.debug("--- DEBUG: Admin tentou filtrar por 'Arquivado' mas status não encontrado. ---")
                return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)
        else:
            current_app.logger.debug("--- DEBUG: Admin não especificou filtro de status ou solicitou 'Todos' (home). Mostrando todos os não cancelados. ---")
    else:
        current_app.logger.debug("--- DEBUG: Lógica para NÃO-ADMINISTRADOR --- ")
        
        if event_filter_type == 'Realizado' or event_filter_type == 'Arquivado':
            current_app.logger.info(f"Non-admin user {user.username} tried to access {event_filter_type} events. Denied as per rules.")
            flash(f"Você não tem permissão para visualizar eventos '{event_filter_type}'.", 'danger')
            return Event.query.filter(false()).paginate(page=page, per_per=per_page, error_out=False)
        base_query = base_query.filter(
            Event.is_published == True,
            Event.event_status == active_status_obj
        )
        current_app.logger.debug("--- DEBUG: Non-admin base query conditions: Event.is_published == True AND Event.is_cancelled == False AND Event.event_status.name == 'Ativo' ---")
        
        is_author_condition = Event.author_id == user.id
        current_app.logger.debug(f"--- DEBUG:   - Condição 'É Autor': Event.author_id == {user.id}")
        is_assigned_to_task_condition = Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == user.id))
        current_app.logger.debug(f"--- DEBUG:   - Condição 'Atribuído a Tarefa': Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == {user.id}))")
        has_direct_permission_condition = Event.event_permissions.any(EventPermission.user_id == user.id)
        current_app.logger.debug(f"--- DEBUG:   - Condição 'Permissão Direta no Evento': Event.event_permissions.any(EventPermission.user_id == {user.id})")
        visibility_conditions_for_user = or_(
            is_author_condition,
            is_assigned_to_task_condition,
            has_direct_permission_condition
        )
        base_query = base_query.filter(visibility_conditions_for_user)
        current_app.logger.debug(f"--- DEBUG: Non-admin query final filter (visibilidade): ({is_author_condition} OR {is_assigned_to_task_condition} OR {has_direct_permission_condition})")

    if publication_status == 'published':
        base_query = base_query.filter(Event.is_published == True)
        current_app.logger.debug("--- DEBUG: Aplicado filtro de publicação: Event.is_published == True ---")
    elif publication_status == 'unpublished':
        base_query = base_query.filter(Event.is_published == False)
        current_app.logger.debug("--- DEBUG: Aplicado filtro de publicação: Event.is_published == False ---")
    else:
        current_app.logger.debug("--- DEBUG: Filtro de publicação: 'all' (nenhum filtro adicional aplicado) ---")
    
    search_query_text = request.args.get('search', '')
    if search_query_text:
        base_query = base_query.filter(
            or_(
                Event.title.ilike(f'%{search_query_text}%'),
                Event.description.ilike(f'%{search_query_text}%'),
                Event.location.ilike(f'%{search_query_text}%')
            )
        )
        current_app.logger.debug(f"--- DEBUG: Adicionado filtro de busca: '{search_query_text}' ---")
    base_query = base_query.order_by(Event.due_date.asc())
    
    count_before_pagination = base_query.count()
    current_app.logger.debug(f"--- DEBUG: Total de eventos encontrados antes da paginação para user {user.username}: {count_before_pagination} ---")
    
    pagination_result = base_query.paginate(page=page, per_page=per_page, error_out=False)
    current_app.logger.debug(f"--- DEBUG: Eventos na página {page}: {len(pagination_result.items)} ---")
    
    return pagination_result

# NOVO: Função auxiliar para contagens de eventos por status de publicação
def get_event_publication_counts(user, event_filter_type=None):
    """
    Retorna as contagens de eventos para 'all', 'published' e 'unpublished',
    respeitando as permissões do usuário e o tipo de filtro (ativo, realizado, etc.).
    """
    base_query = Event.query.filter(Event.is_cancelled == False)

    if not user.is_admin:
        active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
        if not active_status_obj:
             return {'all': 0, 'published': 0, 'unpublished': 0}
        visibility_conditions_for_user = or_(
            Event.author_id == current_user.id,
            Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id)),
            Event.event_permissions.any(EventPermission.user_id == current_user.id)
        )
        base_query = base_query.filter(
            visibility_conditions_for_user,
            Event.event_status == active_status_obj
        )
        if event_filter_type and event_filter_type != 'Ativo' and event_filter_type != 'Todos' and event_filter_type != None:
             return {'all': 0, 'published': 0, 'unpublished': 0}
        
    else:
        if event_filter_type == 'Ativo':
            active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
            if active_status_obj:
                base_query = base_query.filter(Event.event_status == active_status_obj)
        elif event_filter_type == 'Realizado':
            realizado_status_obj = Status.query.filter_by(name='Realizado', type='event').first()
            if realizado_status_obj:
                base_query = base_query.filter(Event.event_status == realizado_status_obj)
        elif event_filter_type == 'Arquivado':
            arquivado_status_obj = Status.query.filter_by(name='Arquivado', type='event').first()
            if arquivado_status_obj:
                base_query = base_query.filter(Event.event_status == arquivado_status_obj)
    total_events = base_query.count()
    published_events = base_query.filter(Event.is_published == True).count()
    unpublished_events = base_query.filter(Event.is_published == False).count()
    return {
        'all': total_events,
        'published': published_events,
        'unpublished': unpublished_events
    }


# Nova rota para fornecer a chave pública VAPID ao frontend
@main.route('/api/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """Retorna a chave pública VAPID para o frontend."""
    vapid_public_key = current_app.config.get('VAPID_PUBLIC_KEY')
    if not vapid_public_key:
        current_app.logger.error("VAPID_PUBLIC_KEY não configurada no aplicativo.")
        return jsonify({'error': 'VAPID Public Key not configured'}), 500
    return jsonify({'vapid_public_key': vapid_public_key})


@main.route("/home")
@login_required
def home():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    
    publication_status = request.args.get('publication_status', 'all')
    events = get_filtered_events(current_user, search_query, page, per_page, event_filter_type=None, publication_status=publication_status)
    publication_counts = get_event_publication_counts(current_user, event_filter_type=None)
    title_text = 'Meus Eventos Ativos' if not current_user.is_admin else 'Todos os Eventos'
    return render_template('home.html', events=events, title=title_text, search_query=search_query,
                           current_filter='home', publication_status=publication_status,
                           publication_counts=publication_counts)
    

@main.route("/events/active")
@login_required
def active_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    publication_status = request.args.get('publication_status', 'all')
    
    events = get_filtered_events(current_user, search_query, page, per_page, event_filter_type='Ativo', publication_status=publication_status)
    publication_counts = get_event_publication_counts(current_user, event_filter_type='Ativo')
    return render_template('home.html', events=events, title='Eventos Ativos', search_query=search_query, 
                           current_filter='active', publication_status=publication_status,
                           publication_counts=publication_counts)
    

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
    publication_status = request.args.get('publication_status', 'all')
    events = get_filtered_events(current_user, search_query, page, per_page, event_filter_type='Realizado', publication_status=publication_status)
    publication_counts = get_event_publication_counts(current_user, event_filter_type='Realizado')

    return render_template('home.html', events=events, title='Eventos Realizados', search_query=search_query, 
                           current_filter='completed', publication_status=publication_status,
                           publication_counts=publication_counts)


@main.route("/events/archived")
@login_required
def archived_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5
    publication_status = request.args.get('publication_status', 'all')
    events = get_filtered_events(current_user, search_query, page, per_page, event_filter_type='Arquivado', publication_status=publication_status)
    publication_counts = get_event_publication_counts(current_user, event_filter_type='Arquivado')
    return render_template('home.html', events=events, title='Eventos Arquivados', search_query=search_query, 
                           current_filter='archived', publication_status=publication_status,
                           publication_counts=publication_counts)


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
        current_app.logger.debug(f"\n--- DEBUG: Tentativa de Login ---")
        current_app.logger.debug(f"--- DEBUG: E-mail recebido (form.email.data): '{form.email.data}' ---")
        current_app.logger.debug(f"--- DEBUG: Senha preenchida? {bool(form.password.data)} ---")
        if form.validate_on_submit():
            current_app.logger.debug(f"--- DEBUG: Formulário de Login validado com sucesso! ---")
            user = User.query.filter_by(email=form.email.data).first()
            current_app.logger.debug(f"--- DEBUG: Usuário encontrado: Username='{user.username}', Email='{user.email}' ---")
            if user:
                if user.check_password(form.password.data):
                    login_user(user, remember=form.remember.data)
                    next_page = request.args.get('next')
                    if not next_page or next_page == url_for('main.home'):
                        redirect_url = url_for('main.active_events')
                    else:
                        redirect_url = next_page
                    flash('Login bem-sucedido!', 'success')
                    current_app.logger.debug(f"--- DEBUG: Senha corresponde. Login bem-sucedido. Redirecionando para: {redirect_url} ---")
                    return redirect(redirect_url)
                else:
                    flash('Login mal-sucedido. Por favor, verifique seu e-mail e senha.', 'danger')
                    current_app.logger.debug(f"--- DEBUG: Senha não corresponde para o usuário '{user.email}'. ---")
            else:
                flash('Login mal-sucedido. Por favor, verifique seu e-mail e senha.', 'danger')
                current_app.logger.debug(f"--- DEBUG: Usuário com e-mail '{form.email.data}' NÃO encontrado no banco de dados. ---")
        else:
            current_app.logger.debug(f"--- DEBUG: Validação do formulário de Login FALHOU. Erros: {form.errors} ---")
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
        if form.picture.data and form.picture.data.filename:
            pass # Apenas um placeholder se save_picture não estiver definida
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Sua conta foi atualizada!', 'success')
        return redirect(url_for('main.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
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
                user_id=current_user.id,
                record_type='User',
                record_id=user.id,
                old_data={}, # Senha não é logada diretamente por segurança, mas a ação é
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
# ROTAS DE KANBAN
# =========================================================================
@main.route('/kanban_board', methods=['GET'])
@login_required
def kanban_board():
    """
    Rota para exibir o quadro Kanban de tarefas.
    Permite filtrar por evento e/ou usuário atribuído.
    """
    # 1. ORDEM DAS COLUNAS: Definir a ordem desejada para os status das colunas
    desired_order_names = ['Não iniciado', 'Em Andamento', 'Pendente', 'Concluído', 'Cancelado']
    
    # Busca TODOS os status do tipo 'task' do banco de dados
    all_task_statuses_from_db = Status.query.filter_by(type='task').all()
    
    # Cria um mapa de nome para objeto Status para fácil acesso
    status_objects_map = {status.name: status for status in all_task_statuses_from_db}

    # Cria uma lista ORDENADA de dados de coluna para o template.
    # Garante que todas as colunas apareçam na ordem desejada, mesmo que não existam no DB.
    kanban_columns_data = []
    for name in desired_order_names:
        status_obj = status_objects_map.get(name)
        kanban_columns_data.append({
            'name': name,
            'id': status_obj.id if status_obj else None, # ID será None se o status não existir
            'obj': status_obj # O objeto Status (ou None)
        })

    # Prepare um dicionário para armazenar tarefas agrupadas por nome de status (string)
    # Inicializa o dicionário com todos os nomes desejados, garantindo que mesmo colunas vazias sejam consideradas
    tasks_by_status_name = {name: [] for name in desired_order_names} 
    
    # Obter parâmetros de filtro da URL
    current_event_id = request.args.get('event_id', type=int)
    current_assignee_id = request.args.get('assignee_id', type=int)
    
    # Consulta base de tarefas, carregando dados relacionados para exibição no card
    query = Task.query.options(
        joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Task.event),
        joinedload(Task.task_status_rel) 
    )

    # Lógica de filtragem
    if current_event_id:
        query = query.filter(Task.event_id == current_event_id)
    if current_assignee_id:
        query = query.filter(Task.assignees_associations.any(TaskAssignment.user_id == current_assignee_id))

    # Lógica de permissão de visualização (similar a _can_view_event_helper, mas para tarefas)
    if not current_user.is_admin:
        user_visibility_conditions = or_(
            Task.creator_id == current_user.id,
            Task.event.has(Event.author_id == current_user.id),
            Task.assignees_associations.any(TaskAssignment.user_id == current_user.id),
            Task.event.has(Event.event_permissions.any(EventPermission.user_id == current_user.id))
        )
        query = query.filter(user_visibility_conditions)

    all_tasks = query.order_by(Task.due_date.asc().nulls_last(), Task.id.desc()).all()

    for task in all_tasks:
        if task.task_status_rel and task.task_status_rel.name in tasks_by_status_name:
            tasks_by_status_name[task.task_status_rel.name].append(task)
    
    now_utc = datetime.utcnow() # Garante que now_utc seja um objeto datetime completo para o template

    # Instanciar TaskForm para o modal de nova tarefa
    form = TaskForm()
    # Popular as queries para os QuerySelectFields do formulário
    form.event.query = Event.query.order_by(Event.title).all()
    form.task_category.query = TaskCategory.query.order_by(TaskCategory.name).all()
    form.task_subcategory.query = TaskSubcategory.query.order_by(TaskSubcategory.name).all()
    form.task_status_rel.query = Status.query.filter_by(type='task').order_by(Status.id).all()
    form.assignees.query = User.query.order_by(User.username).all()

    return render_template('kanban.html',
                           title='Quadro Kanban de Tarefas',
                           tasks_by_status=tasks_by_status_name,
                           kanban_columns_data=kanban_columns_data, # Passa a lista ORDENADA de dados de coluna
                           current_event_id=current_event_id,
                           current_assignee_id=current_assignee_id,
                           all_events=Event.query.order_by(Event.title).all(), # Passar todos os eventos para o filtro
                           all_users=User.query.order_by(User.username).all(), # Passar todos os usuários para o filtro
                           now_utc=now_utc,
                           csrf_token=generate_csrf(),
                           form=form 
                          )

@main.route('/api/tasks/<int:task_id>/update_status', methods=['POST'])
@login_required
@permission_required('can_edit_task')
def api_update_task_status(task_id):
    task = Task.query.get_or_404(task_id)

    data = request.get_json()
    new_status_id = data.get('new_status_id')
    new_status_name = data.get('new_status_name')  # Novo campo para nome do status
    
    if not new_status_id:
        current_app.logger.warning(f"DEBUG: api_update_task_status - Novo status não fornecido para tarefa {task_id}.")
        return jsonify({'success': False, 'message': 'Novo status não fornecido.'}), 400
    
    # Lidar com status não configurados (como "Não iniciado")
    if isinstance(new_status_id, str) and not new_status_id.isdigit():
        # CORREÇÃO: Não permitir mover para "Não iniciado" pois viola a restrição NOT NULL
        if 'Não iniciado' in str(new_status_name or new_status_id):
            current_app.logger.warning(f"DEBUG: api_update_task_status - Tentativa de mover tarefa {task_id} para 'Não iniciado' bloqueada (violaria restrição NOT NULL).")
            return jsonify({
                'success': False, 
                'message': 'Não é possível mover tarefas para "Não iniciado" pois este status não está configurado no banco de dados. Por favor, configure este status na administração.'
            }), 400
        else:
            current_app.logger.warning(f"DEBUG: api_update_task_status - Status não configurado '{new_status_name or new_status_id}' não suportado para tarefa {task_id}.")
            return jsonify({'success': False, 'message': f'Status "{new_status_name or new_status_id}" não está configurado no sistema.'}), 400
    
    # Status configurado - buscar pelo ID
    try:
        status_id = int(new_status_id)
        new_status = Status.query.get(status_id)
    except (ValueError, TypeError):
        current_app.logger.warning(f"DEBUG: api_update_task_status - ID de status inválido '{new_status_id}' para tarefa {task_id}.")
        return jsonify({'success': False, 'message': 'ID de status inválido.'}), 400
    
    if not new_status:
        current_app.logger.warning(f"DEBUG: api_update_task_status - Status ID {new_status_id} não encontrado para tarefa {task_id}.")
        return jsonify({'success': False, 'message': 'Status não encontrado.'}), 400

    old_task_data_for_log = task.to_dict()
    current_app.logger.debug(f"DEBUG: api_update_task_status - Atualizando status da tarefa {task_id} de '{task.task_status_rel.name if task.task_status_rel else 'N/A'}' para '{new_status.name}'.")

    task.task_status_id = new_status_id
    task.updated_at = datetime.utcnow()

    # Lógica para gerenciar is_completed com base no novo status
    if new_status.name == 'Concluído' and not task.is_completed:
        current_app.logger.debug(f"DEBUG: api_update_task_status - Tarefa {task_id} marcada como concluída.")
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        task.completed_by_id = current_user.id
        if task.checklist:
            for item in task.checklist.items:
                item.is_completed = True
    elif new_status.name != 'Concluído' and task.is_completed:
        current_app.logger.debug(f"DEBUG: api_update_task_status - Tarefa {task_id} desmarcada como concluída.")
        task.is_completed = False
        task.completed_at = None
        task.completed_by_id = None
        if task.checklist:
            for item in task.checklist.items:
                item.is_completed = False

    try:
        db.session.commit() # Commit da atualização da tarefa e itens de checklist (se houver)
        current_app.logger.debug(f"DEBUG: api_update_task_status - PRIMEIRO db.session.commit() BEM-SUCEDIDO para tarefa {task_id}.")

        # Logar a alteração no ChangeLogEntry
        ChangeLogEntry.log_update(
            current_user.id,
            'Task',
            task.id,
            old_task_data_for_log,
            task.to_dict(),
            description=f'Status da tarefa "{task.title}" alterado para "{new_status.name}" via Kanban.'
        )
        current_app.logger.debug(f"DEBUG: api_update_task_status - Log de alteração de status adicionado. Tentando o SEGUNDO commit...")
        db.session.commit() # Commit do ChangeLogEntry
        current_app.logger.debug(f"DEBUG: api_update_task_status - SEGUNDO db.session.commit() BEM-SUCEDIDO. Tarefa {task_id} DEVE ESTAR persistida.")

        return jsonify({'success': True, 'message': f'Status da tarefa "{task.title}" atualizado para "{new_status.name}".'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"DEBUG: api_update_task_status - ERRO GERAL capturado ao atualizar status da tarefa {task_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Erro ao atualizar status: {str(e)}'}), 500


# ROTA PARA CRIAR TAREFAS VIA AJAX NO KANBAN
@main.route('/api/tasks/create', methods=['POST'])
@login_required
@permission_required('can_create_task') # Exemplo de permissão para criar tarefa
def create_task_from_kanban():
    form = TaskForm() # Instancia o formulário

    # É CRUCIAL popular as queries dos QuerySelectFields para que a validação do WTForms funcione
    # O request.get_json() não popula os formulários WTForms automaticamente.
    # Precisamos popula-los manualmente para que QuerySelectField consiga mapear IDs para objetos
    # antes de form.validate_on_submit() ser chamado.
    form.event.query = Event.query.order_by(Event.title).all()
    form.task_category.query = TaskCategory.query.order_by(TaskCategory.name).all()
    form.task_subcategory.query = TaskSubcategory.query.order_by(TaskSubcategory.name).all()
    form.task_status_rel.query = Status.query.filter_by(type='task').order_by(Status.id).all()
    form.assignees.query = User.query.order_by(User.username).all()

    # Como o formulário é enviado via AJAX como JSON, precisamos carregá-lo manualmente.
    # O `process()` método ajuda a carregar dados em QuerySelectField e outros.
    if request.is_json:
        data = request.get_json()
        # Processa os dados JSON no formulário
        form.process(data=data)
        
        # O campo 'due_date' precisa ser convertido de string para date manualmente
        if 'due_date' in data and data['due_date']:
            try:
                form.due_date.data = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            except ValueError:
                form.due_date.errors.append('Formato de data inválido. Use AAAA-MM-DD.')

        # Manualmente definir o dado para task_status_rel usando o ID do campo oculto
        # Isso permite que form.validate() possa verificar se um status válido foi fornecido
        if 'kanban_status_id_hidden' in data and data['kanban_status_id_hidden']:
            status_id_from_kanban = data['kanban_status_id_hidden']
            status_obj_for_validation = Status.query.get(status_id_from_kanban)
            if status_obj_for_validation:
                form.task_status_rel.data = status_obj_for_validation
            else:
                form.task_status_rel.errors.append('Status da tarefa inválido.')


    if form.validate(): # Use form.validate() sem on_submit para dados JSON
        try:
            # Agora form.task_status_rel.data já deve conter o objeto Status
            task_category_obj = form.task_category.data
            task_subcategory_obj = form.task_subcategory.data if form.task_subcategory.data else None
            task_status_obj = form.task_status_rel.data

            if not task_category_obj or not task_status_obj:
                return jsonify({'success': False, 'message': 'Categoria de tarefa ou Status de tarefa inválido.'}), 400
            
            new_task = Task(
                title=form.title.data,
                description=form.description.data,
                due_date=form.due_date.data,
                event_id=form.event.data.id if form.event.data else None,
                task_category_id=form.task_category.data.id,
                task_subcategory_id=form.task_subcategory.data.id if form.task_subcategory.data else None,
                task_status_id=task_status_obj.id, # Usando o ID do objeto Status
                creator_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                priority=form.priority.data # Adicionado o campo priority
            )
            db.session.add(new_task)
            db.session.flush() # Para obter o ID da nova_tarefa antes de criar as atribuições

            # Lógica para atribuir usuários
            if form.assignees.data:
                # form.assignees.data já é uma lista de objetos User se processado corretamente
                # Mas do JS ele vem como string JSON de IDs, então precisamos parsear
                selected_assignee_ids = form.assignees.data # Isso já deve ser um objeto Python (lista de IDs) se process(data=data) funcionou
                if isinstance(selected_assignee_ids, list): # Verifica se já é uma lista de IDs
                    for user_id in selected_assignee_ids:
                        user_obj = User.query.get(user_id)
                        if user_obj:
                            assignment = TaskAssignment(task_id=new_task.id, user_id=user_obj.id)
                            db.session.add(assignment)
                else: # Fallback caso form.process não tenha convertido corretamente
                    try:
                        parsed_assignees = json.loads(selected_assignee_ids)
                        for user_id in parsed_assignees:
                            user_obj = User.query.get(user_id)
                            if user_obj:
                                assignment = TaskAssignment(task_id=new_task.id, user_id=user_obj.id)
                                db.session.add(assignment)
                    except (json.JSONDecodeError, TypeError):
                        current_app.logger.error(f"Erro ao processar assignees: {selected_assignee_ids} não é JSON válido ou lista.")


            db.session.commit()

            # Logar a criação no ChangeLogEntry
            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Task',
                record_id=new_task.id,
                new_data=new_task.to_dict(),
                description=f"Tarefa '{new_task.title}' criada via Kanban Quick Add."
            )
            db.session.commit()

            # Preparar dados para o frontend
            # Precisamos recarregar a tarefa para obter a relação de assignees que foi adicionada
            db.session.refresh(new_task) 
            assignee_names = [assignment.user.username for assignment in new_task.assignees_associations] 
            event_title = new_task.event.title if new_task.event else None
            
            task_data = {
                'id': new_task.id,
                'title': new_task.title,
                'description': new_task.description,
                'due_date': new_task.due_date.strftime('%Y-%m-%d'), # Formato para JS
                'due_date_formatted': new_task.due_date.strftime('%d/%m/%Y'), # Formato para exibição
                'is_completed': new_task.is_completed, 
                'assignees': assignee_names,
                'event_id': new_task.event_id,
                'event_title': event_title,
                'status_id': new_task.task_status_id,
                'status_name': new_task.task_status_rel.name,
                'creator_id': new_task.creator_id,
                'priority': new_task.priority, # Incluir prioridade
                'now_utc_date': datetime.utcnow().date().strftime('%Y-%m-%d') # Para comparação de data no JS
            }

            return jsonify({'success': True, 'message': 'Tarefa criada com sucesso!', 'task': task_data}), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar tarefa via Kanban Quick Add: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Erro interno do servidor: {str(e)}'}), 500
    else:
        # Se a validação do formulário falhar, retorne os erros
        errors = {}
        for fieldName, errorMessages in form.errors.items():
            errors[fieldName] = errorMessages
        current_app.logger.warning(f"Erro de validação ao criar tarefa via Kanban: {errors}")
        return jsonify({'success': False, 'message': 'Erro de validação', 'errors': errors}), 400


# =========================================================================
# Rotas de Eventos
# =========================================================================
@main.route("/event/new", methods=['GET', 'POST'])
@login_required
@permission_required('can_create_event')
def new_event():
    form = EventForm()
    available_categories = Category.query.all()
    available_event_statuses = Status.query.filter_by(type='event').all()
    if not available_event_statuses:
        flash("Nenhum status de evento disponível. Por favor, crie pelo menos um status do tipo 'Evento' na administração (Ex: Ativo, Pendente, etc.)", 'warning')
    if not available_categories:
        flash('Nenhuma categoria de evento disponível. Por favor, crie pelo menos uma categoria na administração.', 'warning')
    
    if form.validate_on_submit():
        try:
            category_obj = form.category.data
            event_status_obj = form.event_status.data

            if not category_obj:
                flash('Por favor, selecione uma Categoria válida.', 'danger')
                return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Novo Evento')
            
            if not event_status_obj:
                flash('Por favor, selecione um Status de Evento válido.', 'danger')
                return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Novo Evento')

            event = Event(
                title=form.title.data,
                description=form.description.data,
                due_date=form.due_date.data,
                end_date=form.end_date.data,
                location=form.location.data,
                author_id=current_user.id,
                category_id=category_obj.id,
                status_id=event_status_obj.id
            )
            db.session.add(event)
            db.session.commit()

            ChangeLogEntry.log_creation(current_user.id, 'Event', event.id, new_data=event.to_dict(), description=f"Evento '{event.title}' criado.")
            
            flash('Seu evento foi criado!', 'success')
            return redirect(url_for('main.home'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar novo evento: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao criar o evento: {str(e)}. Por favor, tente novamente.', 'danger')
            return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Novo Evento')


@main.route("/event/<int:event_id>")
@login_required
def event(event_id):
    event_obj = Event.query.options(
        joinedload(Event.tasks).joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Event.tasks).joinedload(Task.checklist).joinedload(TaskChecklist.items).joinedload(TaskChecklistItem.attachments).joinedload(Attachment.uploader),
        joinedload(Event.author),
        joinedload(Event.event_permissions)
    ).get_or_404(event_id)

    if not _can_view_event_helper(current_user, event_obj):
        flash('Você não tem permissão para visualizar este evento.', 'danger')
        abort(403)

    filtered_active_tasks = []
    filtered_completed_tasks = []
    is_admin = current_user.is_admin
    is_event_author = (event_obj.author_id == current_user.id)
    
    has_explicit_event_permission = any(p.user_id == current_user.id for p in event_obj.event_permissions)
    if is_admin or is_event_author or has_explicit_event_permission:
        all_event_tasks = event_obj.tasks
        filtered_active_tasks = sorted([task for task in all_event_tasks if not task.is_completed], key=lambda t: t.due_date if t.due_date else datetime.min)
        filtered_completed_tasks = sorted([task for task in all_event_tasks if task.is_completed], key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)
    else:
        for task in event_obj.tasks:
            if any(assignment.user_id == current_user.id for assignment in task.assignees_associations):
                if not task.is_completed:
                    filtered_active_tasks.append(task)
                else:
                    filtered_completed_tasks.append(task)
        filtered_active_tasks.sort(key=lambda t: t.due_date if t.due_date else datetime.min)
        filtered_completed_tasks.sort(key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)

    current_date = date.today()
    days_left = (task_obj.due_date.date() - current_date).days if 'task_obj' in locals() and task_obj.due_date else 0

    can_manage_event_permissions = is_admin or is_event_author
    can_edit_event = is_admin or is_event_author
    can_create_tasks = is_admin or is_event_author or \
                       (current_user.role_obj and current_user.role_obj.can_create_task)
    can_upload_attachments = current_user.is_admin or \
                             (current_user.role_obj and current_user.role_obj.can_upload_attachments)
    can_manage_attachments = current_user.is_admin or \
                             (current_user.role_obj and current_user.role_obj.can_manage_attachments)

    comment_form = CommentForm()
    attachment_form = AttachmentForm()
    return render_template('event.html',
                           title=event_obj.title,
                           event=event_obj,
                           active_tasks=filtered_active_tasks,
                           completed_tasks=filtered_completed_tasks,
                           current_date=current_date,
                           is_admin=is_admin,
                           is_event_author=is_event_author,
                           can_manage_event_permissions=can_manage_event_permissions,
                           can_edit_event=can_edit_event,
                           can_create_tasks=can_create_tasks,
                           can_upload_attachments=can_upload_attachments,
                           can_manage_attachments=can_manage_attachments,
                           attachment_form=attachment_form,
                           comment_form=comment_form,
                           can_publish_event=current_user.can_publish_event,
                           can_cancel_event=current_user.can_cancel_event,
                           can_duplicate_event=current_user.can_duplicate_event,
                           can_view_event_registrations=current_user.can_view_event_registrations,
                           can_view_event_reports=current_user.can_view_event_reports
                           )


@main.route("/event/<int:event_id>/update", methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    event_obj = Event.query.get_or_404(event_id)

    can_edit_event = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id:
            can_edit_event = True
        elif current_user.is_admin:
            can_edit_event = True
    if not can_edit_event:
        abort(403)

    old_data = event_obj.to_dict()
    form = EventForm(obj=event_obj)
    if form.validate_on_submit():
        event_obj.title = form.title.data
        event_obj.description = form.description.data
        event_obj.due_date = form.due_date.data
        event_obj.end_date = form.end_date.data
        event_obj.location = form.location.data

        # Corrigido: QuerySelectField retorna o objeto diretamente, não o ID
        category_obj = form.category.data
        event_status_obj = form.event_status.data 
        if not category_obj or not event_status_obj: 
            flash('Categoria ou Status de evento inválido.', 'danger')
            return render_template('create_edit_event.html', title='Atualizar Evento', form=form, legend='Atualizar Evento')
        event_obj.category = category_obj
        event_obj.event_status = event_status_obj 
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Event', event_obj.id, old_data=old_data, new_data=event_obj.to_dict(), description=f"Evento '{event_obj.title}' atualizado.")
        db.session.commit()
        flash('Seu evento foi atualizado!', 'success')
        return redirect(url_for('main.event', event_id=event_obj.id))
    elif request.method == 'GET':
        form.title.data = event_obj.title
        form.description.data = event_obj.description
        form.due_date.data = event_obj.due_date
        form.end_date.data = event_obj.end_date
        form.location.data = event_obj.location
        form.category.data = event_obj.category 
        form.event_status.data = event_obj.event_status 
    return render_template('create_edit_event.html', title='Atualizar Evento',
                           form=form, legend='Atualizar Evento')


@main.route("/event/<int:event_id>/delete", methods=['POST'])
@login_required
def delete_event(event_id):
    event_obj = Event.query.get_or_404(event_id)

    can_edit_event = False
    if current_user.is_authenticated:
        if event_obj.author_id == current_user.id:
            can_edit_event = True
        elif current_user.is_admin:
            can_edit_event = True
    if not can_edit_event:
        abort(403)

    old_data = event_obj.to_dict()
    db.session.delete(event_obj)
    db.session.commit()
    ChangeLogEntry.log_deletion(current_user.id, 'Event', event_obj.id, old_data=old_data, description=f"Evento '{old_data.get('title', 'Nome Desconhecido')}' deletado.")
    db.session.commit()
    flash('Seu evento foi deletado!', 'success')
    return redirect(url_for('main.home'))


# =========================================================================
# NOVAS ROTAS DE AÇÕES DE EVENTO
# =========================================================================
@main.route("/event/<int:event_id>/registrations")
@login_required
@permission_required('can_view_event_registrations') # Usando o decorator consolidado
def view_event_registrations(event_id):
    event = Event.query.get_or_404(event_id)
    
    participants = [] # Lógica para buscar participantes
    return render_template('event_registrations.html', event=event, participants=participants, title=f"Participantes de {event.title}")

@main.route("/event/<int:event_id>/publish", methods=['POST'])
@login_required
@permission_required('can_publish_event') # Usando o decorator consolidado
def publish_event(event_id):
    event = Event.query.get_or_404(event_id)
    old_data = event.to_dict()
    event.is_published = True
    try:
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Event', event.id, old_data=old_data, new_data=event.to_dict(), description=f"Evento '{event.title}' publicado.")
        db.session.commit()
        # flash('Evento publicado com sucesso!', 'success') # Removido
        return jsonify({'success': True, 'message': 'Evento publicado com sucesso!'}), 200 # <-- MODIFICADO
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao publicar evento {event_id}: {e}", exc_info=True)
        # flash(f'Erro ao publicar evento: {str(e)}', 'danger') # Removido
        return jsonify({'success': False, 'message': f'Erro ao publicar evento: {str(e)}'}), 500 # <-- MODIFICADO


@main.route("/event/<int:event_id>/unpublish", methods=['POST'])
@login_required
@permission_required('can_publish_event') # Usando o decorator consolidado
def unpublish_event(event_id):
    event = Event.query.get_or_404(event_id)
    old_data = event.to_dict()
    event.is_published = False
    try:
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Event', event.id, old_data=old_data, new_data=event.to_dict(), description=f"Evento '{event.title}' despublicado.")
        db.session.commit()
        # flash('Evento despublicado com sucesso!', 'warning') # Removido
        return jsonify({'success': True, 'message': 'Evento despublicado com sucesso!'}), 200 # <-- MODIFICADO
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao despublicar evento {event_id}: {e}", exc_info=True)
        # flash(f'Erro ao despublicar evento: {str(e)}', 'danger') # Removido
        return jsonify({'success': False, 'message': f'Erro ao despublicar evento: {str(e)}'}), 500 # <-- MODIFICADO


@main.route("/event/<int:event_id>/duplicate", methods=['POST'])
@login_required
@permission_required('can_duplicate_event') # Usando o decorator consolidado
def duplicate_event(event_id):
    try:
        original_event = Event.query.get_or_404(event_id)
        new_event = Event(
            title=f"Cópia de {original_event.title}",
            description=original_event.description,
            due_date=original_event.due_date,
            end_date=original_event.end_date,
            location=original_event.location,
            author_id=current_user.id,
            category_id=original_event.category_id,
            status_id=original_event.status_id,
            is_published=False,
            is_cancelled=False
        )
        db.session.add(new_event)
        db.session.commit()
        ChangeLogEntry.log_creation(current_user.id, 'Event', new_event.id, new_data=new_event.to_dict(), description=f"Evento '{original_event.title}' duplicado para '{new_event.title}'.")
        db.session.commit()
        # flash(f'Evento "{new_event.title}" duplicado com sucesso! Edite-o agora.', 'success') # Removido
        return jsonify({'success': True, 'message': f'Evento "{new_event.title}" duplicado com sucesso!'}), 200 # <-- MODIFICADO
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao duplicar evento {event_id}: {e}", exc_info=True)
        # flash(f'Erro ao duplicar evento: {str(e)}', 'danger') # Removido
        return jsonify({'success': False, 'message': f'Erro ao duplicar evento: {str(e)}'}), 500 # <-- MODIFICADO


@main.route("/event/<int:event_id>/reports")
@login_required
@permission_required('can_view_event_reports') # Usando o decorator consolidado
def event_reports(event_id):
    event = Event.query.get_or_404(event_id)
    
    report_data = {'event_title': event.title, 'some_metric': 123, 'another_metric': 45.6} # Lógica para gerar dados do relatório
    return render_template('event_reports.html', event=event, report_data=report_data, title=f"Relatórios de {event.title}")

@main.route("/event/<int:event_id>/cancel", methods=['POST'])
@login_required
@permission_required('can_cancel_event') # Usando o decorator consolidado
def cancel_event(event_id):
    event = Event.query.get_or_404(event_id)
    old_data = event.to_dict()
    event.is_cancelled = True
    try:
        db.session.commit()
        ChangeLogEntry.log_update(current_user.id, 'Event', event.id, old_data=old_data, new_data=event.to_dict(), description=f"Evento '{event.title}' cancelado.")
        db.session.commit()
        # flash(f'Evento "{event.title}" foi cancelado.', 'warning') # Removido
        return jsonify({'success': True, 'message': f'Evento "{event.title}" foi cancelado.'}), 200 # <-- MODIFICADO
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao cancelar evento {event_id}: {e}", exc_info=True)
        # flash(f'Erro ao cancelar evento: {str(e)}', 'danger') # Removido
        return jsonify({'success': False, 'message': f'Erro ao cancelar evento: {str(e)}'}), 500 # <-- MODIFICADO


# =========================================================================
# FIM NOVAS ROTAS DE AÇÕES DE EVENTO
# =========================================================================


@main.route("/search")
@login_required
def search():
    form = SearchForm()
    results = []
    query = request.args.get('query')
    if query:
        events_query = Event.query.options(
            joinedload(Event.event_status),
            joinedload(Event.category),
            joinedload(Event.author),
            joinedload(Event.event_permissions),
            joinedload(Event.tasks).joinedload(Task.assignees_associations)
        )
        events_query = events_query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%')
            )
        )
        if not current_user.is_admin:
            active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
            visibility_condition = or_(
                Event.author_id == current_user.id,
                Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id)),
                Event.event_permissions.any(EventPermission.user_id == current_user.id)
            )
            visibility_condition = and_(visibility_condition, Event.is_published == True, Event.is_cancelled == False)
            if active_status_obj:
                events_query = events_query.filter(and_(visibility_condition, Event.event_status == active_status_obj))
            else:
                events_query = events_query.filter(false())
        else:
            events_query = events_query.filter(Event.is_cancelled == False)
        viewable_events = events_query.all()

        for event_obj in viewable_events:
            results.append({
                'type': 'Evento',
                'title': event_obj.title,
                'description': event_obj.description,
                'link': url_for('main.event', event_id=event_obj.id)
            })
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
                'link': url_for('main.task_detail', task_id=task_obj.id)
            })
    return render_template('search_results.html', title='Resultados da Busca', form=form, results=results, query=query)
# =========================================================================
# Rotas de Categorias
# =========================================================================
@main.route("/category/new", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def list_categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('list_categories.html', categories=categories, title='Categorias de Eventos')


@main.route("/category/<int:category_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def list_statuses():
    statuses = Status.query.order_by(Status.type, Status.name).all()
    return render_template('list_statuses.html', statuses=statuses, title='Status (Eventos e Tarefas)')


@main.route("/status/<int:status_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def delete_status(status_id):
    status_obj = Status.query.get_or_404(status_id)
    if Event.query.filter_by(event_status=status_obj).first() or Task.query.filter_by(task_status_rel=status_obj).first(): 
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
# Rotas de TaskCategory
# =========================================================================
@main.route("/task_category/new", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def list_task_categories():
    task_categories = TaskCategory.query.order_by(TaskCategory.name).all()
    return render_template('list_task_categories.html', task_categories=task_categories, title='Categorias de Tarefas')


@main.route("/task_category/<int:task_category_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
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
# API de Subcategorias para Dropdown Dinâmico
# =========================================================================
@main.route("/api/task_subcategories/<int:category_id>", methods=['GET'])
@login_required
def get_task_subcategories_api(category_id):
    subcategories = TaskSubcategory.query.filter_by(task_category_id=category_id).order_by(TaskSubcategory.name).all()
    subcategories_data = [{'id': s.id, 'name': s.name} for s in subcategories]
    return jsonify(subcategories_data)

# =========================================================================
# API de Template de Checklist para Renderização Dinâmica
# =========================================================================

@main.route("/api/checklist_template/<int:subcategory_id>", methods=['GET'])
@login_required
def get_checklist_template_api(subcategory_id):
    sub = TaskSubcategory.query.options(
        joinedload(TaskSubcategory.checklist_template).joinedload(ChecklistTemplate.items)
    ).get_or_404(subcategory_id)

    if not sub.checklist_template:
        return jsonify([]) # Retorna um array vazio se não houver checklist template

    checklist_data = {
        "id": sub.checklist_template.id,
        "name": sub.checklist_template.name,
        "items": []
    }

    for item in sub.checklist_template.items:
        checklist_data["items"].append({
            "id": item.id,
            "label": item.label,
            "field_type": item.field_type.name, # <<<<<<<<<< CORREÇÃO ORIGINAL: MUDANÇA DE .value PARA .name
            "is_required": item.is_required,
            "order": item.order,
            "min_images": item.min_images,
            "max_images": item.max_images,
            "options": item.options,
            "placeholder": item.placeholder
        })
    
    return jsonify(checklist_data)


# =========================================================================
# Rotas de Tarefas
# =========================================================================
@main.route("/event/<int:event_id>/task/new", methods=['GET', 'POST'])
@login_required
@permission_required('can_create_task')
def new_task(event_id):
    event_obj = Event.query.get_or_404(event_id)
    form = TaskForm(event=event_obj)

    # Lógica para popular choices de subcategoria
    # ... (código existente) ...

    if form.validate_on_submit():
        current_app.logger.debug(f"DEBUG: new_task - Formulário VALIDADO para evento {event_id}. Tentando salvar tarefa.")
        try:
            task_category_obj = form.task_category.data
            task_subcategory_obj = form.task_subcategory.data if form.task_subcategory.data else None
            task_status_obj = form.task_status_rel.data 

            if not task_category_obj or not task_status_obj:
                current_app.logger.warning(f"DEBUG: new_task - Categoria ou Status da tarefa inválidos no formulário. Cat: {task_category_obj}, Status: {task_status_obj}")
                flash('Categoria de tarefa ou Status de tarefa inválido.', 'danger')
                # Recarrega as choices da subcategoria em caso de erro de validação para o formulário
                if form.task_category.data:
                    category_id_for_filter = form.task_category.data.id
                    subcategories = TaskSubcategory.query.filter_by(task_category_id=category_id_for_filter).order_by(TaskSubcategory.name).all()
                    form.task_subcategory.choices = [(ts.id, ts.name) for ts in subcategories]
                    form.task_subcategory.choices.insert(0, ('', 'Selecione uma Subcategoria'))
                return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event_obj)
            
            task = Task(
                title=form.title.data,
                description=form.description.data,
                notes=form.notes.data,
                due_date=form.due_date.data,
                original_due_date=form.due_date.data,
                event_id=event_obj.id,
                task_category_id=task_category_obj.id,
                task_subcategory_id=task_subcategory_obj.id if task_subcategory_obj else None,
                task_status_id=task_status_obj.id,
                cloud_storage_link=form.cloud_storage_link.data,
                link_notes=form.link_notes.data,
                creator_id=current_user.id,
                is_completed=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                priority=form.priority.data 
            )
            db.session.add(task)
            db.session.flush() # Para obter o ID da nova_tarefa antes de criar as atribuições
            current_app.logger.debug(f"DEBUG: new_task - Objeto Task criado em sessão com ID temporário: {task.id}. Título: '{task.title}'.")

            # Processar Atribuições
            selected_assignee_ids = [user.id for user in form.assignees.data] 
            if selected_assignee_ids:
                current_app.logger.debug(f"DEBUG: new_task - Atribuindo tarefa aos usuários: {selected_assignee_ids}")
                for user_id in selected_assignee_ids:
                    user_obj = User.query.get(user_id)
                    if user_obj:
                        new_assignment = TaskAssignment(task=task, user=user_obj)
                        task.assignees_associations.append(new_assignment)
            
            # Lógica para criação do Checklist Dinâmico
            if task_subcategory_obj and task_subcategory_obj.checklist_template:
                current_app.logger.debug(f"DEBUG: new_task - Criando checklist para a tarefa a partir do template.")
                task_checklist = TaskChecklist(
                    task_id=task.id,
                    task_subcategory_id=task_subcategory_obj.id
                )
                db.session.add(task_checklist)
                db.session.flush()
                current_app.logger.debug(f"DEBUG: new_task - TaskChecklist criado com ID: {task_checklist.id}.")

                for item_template in task_subcategory_obj.checklist_template.items: 
                    task_checklist_item = TaskChecklistItem(
                        task_checklist_id=task_checklist.id,
                        checklist_item_template_id=item_template.id,
                        label=item_template.label, 
                        custom_label=item_template.label, 
                        custom_field_type=item_template.field_type,
                        is_required=item_template.is_required,
                        order=item_template.order,
                        is_completed=False,
                    )
                    db.session.add(task_checklist_item)
                current_app.logger.debug(f"DEBUG: new_task - Itens do checklist adicionados à sessão.")
                
                ChangeLogEntry.log_creation(
                    current_user.id,
                    'TaskChecklist',
                    task_checklist.id,
                    {'task_id': task.id, 'task_subcategory_id': task_subcategory_obj.id},
                    f'Checklist gerado automaticamente para a tarefa "{task.title}" (Subcategoria: {task_subcategory_obj.name}).'
                )
                current_app.logger.debug(f"DEBUG: new_task - Log de criação do checklist adicionado.")

            db.session.commit() # Commit principal dos dados da tarefa
            current_app.logger.debug(f"DEBUG: new_task - PRIMEIRO db.session.commit() BEM-SUCEDIDO para tarefa ID: {task.id}. Dados principais gravados.")

            ChangeLogEntry.log_creation(
                current_user.id,
                'Task',
                task.id,
                task.to_dict(),
                f'Tarefa "{task.title}" (ID: {task.id}) criada por {current_user.username}.'
            )
            current_app.logger.debug(f"DEBUG: new_task - Log de criação da tarefa adicionado. Tentando o SEGUNDO commit...")
            db.session.commit() # Commit do ChangeLogEntry
            current_app.logger.debug(f"DEBUG: new_task - SEGUNDO db.session.commit() BEM-SUCEDIDO. Task {task.id} DEVE ESTAR persistida no banco.")

            flash('Sua tarefa foi criada com sucesso!', 'success')
            current_app.logger.debug(f"DEBUG: new_task - Mensagem flash de sucesso definida. Redirecionando para task_detail/{task.id}")
            return redirect(url_for('main.task_detail', task_id=task.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"DEBUG: new_task - ERRO GERAL capturado durante a criação da tarefa para evento {event_id}: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao criar a tarefa: {str(e)}. Por favor, tente novamente.', 'danger')
            # ... (recarrega as choices da subcategoria e renderiza o template novamente em caso de erro) ...
            return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event_obj)
    else:
        # Se o formulário não validou, logs dos erros de validação
        if request.method == 'POST': # Apenas para POSTs que falharam na validação
            current_app.logger.warning(f"DEBUG: new_task - Formulário NÃO VALIDADO para evento {event_id}. Erros: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo '{field}': {error}", 'danger')
        else: # É um GET request para exibir o formulário
            current_app.logger.debug(f"DEBUG: new_task - Requisição GET para criar nova tarefa para evento {event_obj.id}.")
            
    return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event_obj)

# =========================================================================
# NOVA ROTA: task_detail (Página de detalhes completa da Tarefa)
# =========================================================================
@main.route("/task/<int:task_id>")
@login_required
def task_detail(task_id):
    task_obj = Task.query.options(
        joinedload(Task.checklist).joinedload(TaskChecklist.items).joinedload(TaskChecklistItem.attachments).joinedload(Attachment.uploader),
        joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Task.task_status_rel),
        joinedload(Task.task_category),
        joinedload(Task.task_subcategory), # Carregar a subcategoria
        joinedload(Task.event).joinedload(Event.author),
        joinedload(Task.event).joinedload(Event.event_permissions),
        joinedload(Task.comments).joinedload(Comment.author),
        # CORREÇÃO AQUI: Usar 'template_item' em vez de 'checklist_item_template'
        joinedload(Task.checklist).joinedload(TaskChecklist.items).joinedload(TaskChecklistItem.template_item),
        joinedload(Task.creator_user_obj), # Carregar o criador da tarefa
        joinedload(Task.attachments)
    ).get_or_404(task_id)
    event_obj = task_obj.event

    if not _can_view_event_helper(current_user, event_obj):
        flash('Você não tem permissão para visualizar este evento.', 'danger')
        abort(403)

    filtered_active_tasks = []
    filtered_completed_tasks = []
    is_admin = current_user.is_admin
    is_event_author = (event_obj.author_id == current_user.id)
    
    has_explicit_event_permission = any(p.user_id == current_user.id for p in event_obj.event_permissions)
    if is_admin or is_event_author or has_explicit_event_permission:
        all_event_tasks = event_obj.tasks
        filtered_active_tasks = sorted([task for task in all_event_tasks if not task.is_completed], key=lambda t: t.due_date if t.due_date else datetime.min)
        filtered_completed_tasks = sorted([task for task in all_event_tasks if task.is_completed], key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)
    else:
        for task in event_obj.tasks:
            if any(assignment.user_id == current_user.id for assignment in task.assignees_associations):
                if not task.is_completed:
                    filtered_active_tasks.append(task)
                else:
                    filtered_completed_tasks.append(task)
        filtered_active_tasks.sort(key=lambda t: t.due_date if t.due_date else datetime.min)
        filtered_completed_tasks.sort(key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)

    current_date = date.today()
    days_left = (task_obj.due_date.date() - current_date).days if task_obj.due_date else 0

    can_manage_event_permissions = is_admin or is_event_author
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
    can_approve_art = current_user.is_admin or (current_user.role_obj and current_user.role_obj.can_approve_art)
    comment_form = CommentForm()
    attachment_form = AttachmentForm()
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
                           can_approve_art=can_approve_art, # Passar permissão de aprovação de arte
                           comment_form=comment_form,
                           attachment_form=attachment_form)


# =========================================================================================
# ROTA PARA SERVIR ARQUIVOS DE ÁUDIO UPLOADED
# =========================================================================================
@main.route("/uploads/audio/<path:filename>")
@login_required
def serve_audio_file(filename):
    """Serve arquivos de audio uploaded."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER_AUDIO'], filename)


# =========================================================================
# ATUALIZADO: Rota API para buscar E ADICIONAR comentários de uma tarefa
# =========================================================================
@main.route('/api/comments/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def get_or_add_task_comments_api(task_id):
    task = Task.query.options(joinedload(Task.assignees_associations).joinedload(TaskAssignment.user), joinedload(Task.event).joinedload(Event.author)).get_or_404(task_id)
    
    can_manage_or_view_comments = (
        current_user.is_admin or
        task.event.author_id == current_user.id or
        current_user.id in [u.id for u in task.assignees] or
        (current_user.role_obj and (current_user.role_obj.can_view_task_history or current_user.role_obj.can_manage_task_comments))
    )
    if not can_manage_or_view_comments:
        return jsonify({'message': 'Você não tem permissão para gerenciar comentários desta tarefa.'}), 403
    if request.method == 'GET':
        comments = Comment.query.filter_by(task_id=task.id).options(joinedload(Comment.author)).order_by(Comment.timestamp.asc()).all()
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'timestamp': comment.timestamp.isoformat(),
                'user': comment.author.username if comment.author else 'Usuário Desconhecido',
                'date': comment.timestamp.strftime('%d/%m/%Y %H:%M')
            })
        return jsonify(comments_data)
    elif request.method == 'POST':
        can_add_comment = (
            current_user.is_admin or
            task.event.author_id == current_user.id or
            current_user.id in [u.id for u in task.assignees] or
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

            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Comment',
                record_id=new_comment.id,
                new_data=new_comment.to_dict(),
                description=f"Comentário adicionado por '{current_user.username}' na tarefa '{task.title}'."
            )
            
            notification_link = url_for('main.task_detail', task_id=task.id, _external=True)
            notified_users_ids = {current_user.id}
            general_recipients = set()
            for assignee in task.assignees:
                if assignee.id not in notified_users_ids:
                    general_recipients.add(assignee)
                    notified_users_ids.add(assignee.id)
            
            if task.event.author_id not in notified_users_ids:
                if task.event.author:
                    general_recipients.add(task.event.author)
                    notified_users_ids.add(task.event.author.id)
            
            comment_notification_message = f"'{current_user.username}' comentou na tarefa '{task.title}'."
            for recipient in general_recipients:
                create_in_app_notification(
                    user_id=recipient.id,
                    message=comment_notification_message,
                    link_url=notification_link,
                    related_object_type='Task',
                    related_object_id=task.id
                )
                push_payload = {
                    'body': comment_notification_message,
                    'title': f'Novo Comentário na Tarefa: {task.title}',
                    'url': notification_link,
                    'type': 'new_comment',
                    'task_id': task.id,
                    'event_id': task.event.id
                }
                send_push_to_user(recipient.id, push_payload)
            
            mentioned_usernames = re.findall(r'@(\w+)', comment_text)
            for username in set(mentioned_usernames):
                mentioned_user = User.query.filter_by(username=username).first()
                if mentioned_user and mentioned_user.id not in notified_users_ids:
                    mention_message = f"Você foi mencionado por '{current_user.username}' no comentário da tarefa '{task.title}'."
                    
                    create_in_app_notification(
                        user_id=mentioned_user.id,
                        message=mention_message,
                        link_url=notification_link,
                        related_object_type='Task',
                        related_object_id=task.id
                    )
                    
                    email_subject = f"[Gerenciador de Eventos] Você foi Mencionado em um Comentário"
                    email_body = f"Olá {mentioned_user.username},\n\n{current_user.username} mencionou você no comentário da tarefa '{task.title}' do evento '{task.event.title}'.\n\nComentário: {comment_text}\n\nPara ver o comentário e a tarefa, clique aqui: {notification_link}\n\nAtenciosamente,\nSua Equipe de Gerenciamento de Eventos"
                    send_notification_email(mentioned_user.email, email_subject, email_body)

                    push_payload = {
                        'body': mention_message,
                        'title': f'Você foi Mencionado na Tarefa: {task.title}',
                        'url': notification_link,
                        'type': 'task_mention',
                        'task_id': task.id,
                        'event_id': task.event.id
                    }
                    send_push_to_user(mentioned_user.id, push_payload)
                    
                    notified_users_ids.add(mentioned_user.id)
            db.session.commit()
            
            formatted_date = new_comment.timestamp.strftime('%d/%m/%Y %H:%M')
            return jsonify({
                'id': new_comment.id,
                'user': current_user.username,
                'date': formatted_date,
                'content': new_comment.content,
                'message': 'Comentário adicionado com sucesso!'
            }), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar comentário à tarefa {task_id}: {e}", exc_info=True)
            return jsonify({'message': f'Erro interno do servidor ao adicionar comentário: {str(e)}'}), 500


@main.route("/task/<int:task_id>/update", methods=['GET', 'POST'])
@login_required
@permission_required('can_edit_task') # Usando o decorator consolidado
def update_task(task_id):
    task_obj = Task.query.options(
        joinedload(Task.checklist).joinedload(TaskChecklist.items).joinedload(TaskChecklistItem.template_item) 
    ).get_or_404(task_id)
    event_obj = task_obj.event

    form = TaskForm(obj=task_obj, event=event_obj) # O 'obj=task_obj' já pré-carrega muitos campos

    if request.method == 'GET':
        current_app.logger.debug(f"DEBUG: update_task - Requisição GET para atualizar tarefa {task_id}. Pré-preenchendo formulário.")
        # Preencher os campos restantes ou corrigir para QuerySelectField
        # ... (código existente para pré-popular o formulário) ...

    # No POST (form.validate_on_submit), os campos QuerySelectField.data retornam os objetos selecionados
    if form.validate_on_submit():
        current_app.logger.debug(f"DEBUG: update_task - Formulário VALIDADO para tarefa {task_id}. Tentando salvar alterações.")
        try:
            old_task_data_for_changelog = task_obj.to_dict()
            old_subcategory_id = task_obj.task_subcategory_id
            old_assignee_ids = sorted([u.id for u in task_obj.assignees])

            task_obj.title = form.title.data
            task_obj.description = form.description.data
            task_obj.notes = form.notes.data
            task_obj.due_date = form.due_date.data
            task_obj.cloud_storage_link = form.cloud_storage_link.data
            task_obj.link_notes = form.link_notes.data
            task_obj.audio_path = form.audio_path.data
            task_obj.audio_duration_seconds = form.audio_duration_seconds.data
            task_obj.updated_at = datetime.utcnow()
            task_obj.priority = form.priority.data # Atualiza a prioridade
            current_app.logger.debug(f"DEBUG: update_task - Atributos da tarefa {task_id} atualizados na sessão.")

            # Corrigido: QuerySelectField retorna o objeto diretamente, não o ID
            task_category_obj = form.task_category.data
            task_subcategory_obj = form.task_subcategory.data if form.task_subcategory.data else None
            task_status_obj = form.task_status_rel.data

            if not task_category_obj or not task_status_obj:
                current_app.logger.warning(f"DEBUG: update_task - Categoria ou Status da tarefa inválidos no formulário para tarefa {task_id}.")
                flash('Categoria de tarefa ou Status de tarefa inválido.', 'danger')
                # Recarrega as choices da subcategoria em caso de erro de validação para o formulário
                if form.task_category.data:
                    category_id_for_choices = form.task_category.data.id
                    form.task_subcategory.choices = [(ts.id, ts.name) for ts in TaskSubcategory.query.filter(TaskSubcategory.task_category_id == category_id_for_choices).order_by(TaskSubcategory.name).all()]
                    form.task_subcategory.choices.insert(0, ('', 'Selecione uma Subcategoria'))
                return render_template('create_edit_task.html', title='Atualizar Tarefa',
                                       form=form, legend='Atualizar Tarefa', event=event_obj, task=task_obj)
            
            task_obj.task_category_id = task_category_obj.id
            task_obj.task_subcategory_id = task_subcategory_obj.id if task_subcategory_obj else None
            task_obj.task_status_id = task_status_obj.id
            current_app.logger.debug(f"DEBUG: update_task - Categorias e status da tarefa {task_id} atualizados.")

            if old_subcategory_id != task_obj.task_subcategory_id:
                current_app.logger.debug(f"DEBUG: update_task - Subcategoria da tarefa {task_id} alterada. Reavaliando checklist.")
                if task_obj.checklist:
                    current_app.logger.debug(f"DEBUG: update_task - Excluindo checklist existente para tarefa {task_id}.")
                    ChangeLogEntry.log_deletion(
                        current_user.id,
                        'TaskChecklist',
                        task_obj.checklist.id,
                        task_obj.checklist.to_dict(),
                        f'Checklist da tarefa "{task_obj.title}" (ID: {task_obj.id}) removido devido à mudança de subcategoria.'
                    )
                    db.session.delete(task_obj.checklist)
                
                if task_subcategory_obj and task_subcategory_obj.checklist_template:
                    current_app.logger.debug(f"DEBUG: update_task - Criando novo checklist para tarefa {task_id}.")
                    new_task_checklist = TaskChecklist(
                        task_id=task_obj.id,
                        task_subcategory_id=task_subcategory_obj.id
                    )
                    db.session.add(new_task_checklist)
                    db.session.flush()

                    for item_template in task_subcategory_obj.checklist_template.items:
                        task_checklist_item = TaskChecklistItem(
                            task_checklist_id=new_task_checklist.id,
                            checklist_item_template_id=item_template.id,
                            custom_label=item_template.label,
                            custom_field_type=item_template.field_type,
                            is_completed=False,
                        )
                        db.session.add(task_checklist_item)
                    current_app.logger.debug(f"DEBUG: update_task - Itens do novo checklist adicionados.")
                    
                    ChangeLogEntry.log_creation(
                        current_user.id,
                        'TaskChecklist',
                        new_task_checklist.id,
                        new_task_checklist.to_dict(),
                        f'Novo checklist gerado para a tarefa "{task_obj.title}" (Subcategoria: {task_subcategory_obj.name}) após mudança de subcategoria.'
                    )
                    current_app.logger.debug(f"DEBUG: update_task - Log de criação de novo checklist adicionado.")
            
            new_assignee_ids = sorted([user.id for user in form.assignees.data]) 
            if old_assignee_ids != new_assignee_ids:
                current_app.logger.debug(f"DEBUG: update_task - Atribuídos da tarefa {task_id} alterados. Atualizando.")
                TaskAssignment.query.filter_by(task_id=task_obj.id).delete()
                if new_assignee_ids:
                    for user_id in new_assignee_ids:
                        user_obj = User.query.get(user_id)
                        if user_obj:
                            new_assignment = TaskAssignment(task=task_obj, user=user_obj)
                            db.session.add(new_assignment)
                current_app.logger.debug(f"DEBUG: update_task - Atribuições atualizadas na sessão.")
                
                ChangeLogEntry.log_update(
                    user_id=current_user.id,
                    record_type='Task',
                    record_id=task_obj.id,
                    old_data={'assignees_ids': old_assignee_ids},
                    new_data={'assignees_ids': new_assignee_ids},
                    description=f"Responsáveis pela tarefa '{task_obj.title}' alterados."
                )
                current_app.logger.debug(f"DEBUG: update_task - Log de alteração de atribuídos adicionado.")

            db.session.commit() # Commit principal dos dados da tarefa
            current_app.logger.debug(f"DEBUG: update_task - PRIMEIRO db.session.commit() BEM-SUCEDIDO para tarefa ID: {task_id}. Dados principais gravados.")

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task_obj.id,
                old_data=old_task_data_for_changelog,
                new_data=task_obj.to_dict(),
                description=f"Tarefa '{task_obj.title}' atualizada no evento '{task_obj.event.title}'."
            )
            current_app.logger.debug(f"DEBUG: update_task - Log de atualização da tarefa adicionado. Tentando o SEGUNDO commit...")
            db.session.commit() # Commit do ChangeLogEntry
            current_app.logger.debug(f"DEBUG: update_task - SEGUNDO db.session.commit() BEM-SUCEDIDO. Task {task_id} DEVE ESTAR persistida no banco.")

            flash('Sua tarefa foi atualizada!', 'success')
            current_app.logger.debug(f"DEBUG: update_task - Mensagem flash de sucesso definida. Redirecionando para task_detail/{task_id}")
            return redirect(url_for('main.task_detail', task_id=task_obj.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"DEBUG: update_task - ERRO GERAL capturado durante a atualização da tarefa {task_id}: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao atualizar a tarefa: {str(e)}. Por favor, tente novamente.', 'danger')
            # Recarrega as choices da subcategoria em caso de erro de validação para o formulário
            if form.task_category.data:
                category_id_for_choices = form.task_category.data.id
                form.task_subcategory.choices = [(ts.id, ts.name) for ts in TaskSubcategory.query.filter(TaskSubcategory.task_category_id == category_id_for_choices).order_by(TaskSubcategory.name).all()]
                form.task_subcategory.choices.insert(0, ('', 'Selecione uma Subcategoria'))
            return render_template('create_edit_task.html', title='Atualizar Tarefa', form=form, legend='Atualizar Tarefa', task=task_obj, event=event_obj)
    else:
        # Se o formulário não validou, logs dos erros de validação
        if request.method == 'POST': # Apenas para POSTs que falharam na validação
            current_app.logger.warning(f"DEBUG: update_task - Formulário NÃO VALIDADO para tarefa {task_id}. Erros: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo '{field}': {error}", 'danger')
        else: # É um GET request para exibir o formulário
            current_app.logger.debug(f"DEBUG: update_task - Requisição GET para atualizar tarefa {task_id}.")

    return render_template('create_edit_task.html', title='Atualizar Tarefa', form=form, legend='Atualizar Tarefa', task=task_obj, event=event_obj)

@main.route("/task/<int:task_id>/delete", methods=['POST'])
@login_required
@permission_required('can_delete_task') # Usando o decorator consolidado
def delete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)
    event_obj = task_obj.event

    try:
        old_data = task_obj.to_dict()
        
        # Excluir áudio se houver
        if task_obj.audio_path:
            audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path)
            if os.path.exists(audio_filepath):
                os.remove(audio_filepath)
        
        # Excluir anexos físicos e do DB
        for attachment in task_obj.attachments:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER_ATTACHMENTS'], attachment.unique_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"Anexo '{attachment.unique_filename}' removido para tarefa {task_id}.")
        db.session.delete(task_obj) # Isso deve apagar TaskChecklist e TaskChecklistItem em cascata
        db.session.commit() # Commit das exclusões da tarefa e seus relacionados

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_id,
            old_data=old_data,
            description=f"Tarefa '{old_data.get('title', 'Título Desconhecido')}' excluída do evento '{task_obj.event.title}'."
        )
        db.session.commit() # Commit do ChangeLog

        flash('Sua tarefa foi excluída!', 'success')
        return redirect(url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir tarefa {task_id}: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao excluir a tarefa: {str(e)}. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.event', event_id=task_obj.event.id))


# =========================================================================
# NOVA ROTA: CONCLUIR TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/complete", methods=['POST'])
@login_required
@permission_required('can_complete_task') # Usando o decorator consolidado
def complete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)
    comment = request.form.get('completion_comment')

    if task_obj.is_completed:
        flash('Esta tarefa já está concluída.', 'info')
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    try:
        old_data_for_changelog = task_obj.to_dict()
        task_obj.is_completed = True
        task_obj.completed_at = datetime.utcnow()
        task_obj.completed_by_id = current_user.id
        completed_status = Status.query.filter_by(name='Concluído', type='task').first()
        if completed_status:
            task_obj.task_status_rel = completed_status 
        else:
            flash("Status 'Concluído' para tarefas não encontrado, por favor, crie-o no admin.", 'warning')
        
        # Lógica para marcar itens do checklist como completos ao concluir a tarefa principal
        if task_obj.checklist:
            for item in task_obj.checklist.items: 
                item.is_completed = True

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
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao concluir tarefa {task_id}: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao concluir a tarefa: {str(e)}. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
# =========================================================================
# NOVA ROTA: DESFAZER CONCLUSÃO DA TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/uncomplete", methods=['POST'])
@login_required
@permission_required('can_uncomplete_task') # Usando o decorator consolidado
def uncomplete_task(task_id):
    task_obj = Task.query.get_or_404(task_id)

    if not task_obj.is_completed:
        flash('Esta tarefa não está concluída.', 'info')
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    try:
        old_data_for_changelog = task_obj.to_dict()
        task_obj.is_completed = False
        task_obj.completed_at = None
        task_obj.completed_by_id = None
        pending_status = Status.query.filter_by(name='Pendente', type='task').first()
        if pending_status:
            task_obj.task_status_rel = pending_status 
        else:
            flash("Status 'Pendente' para tarefas não encontrado, por favor, crie-o no admin.", 'warning')
        # Lógica para desmarcar itens do checklist como incompletos ao desfazer a tarefa principal
        if task_obj.checklist:
            for item in task_obj.checklist.items:
                item.is_completed = False

        history_entry = TaskHistory(
            task_id=task_obj.id,
            action_type='uncompletion',
            description=f'Tarefa "{task_obj.title}" marcada como não concluída.',
            old_value=json.dumps({'is_completed': True, 'completed_at': old_data_for_changelog.get('completed_at'), 'completed_by_id': old_data_for_changelog.get('completed_by_id'), 'task_status': pending_status.name if pending_status else 'N/A'}),
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
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao desmarcar tarefa {task_id}: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao marcar a tarefa como não concluída: {str(e)}. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.task_detail', task_id=task_obj.id) if request.referrer and 'task/' in request.referrer else url_for('main.event', event_id=task_obj.event.id))


# =========================================================================
# NOVA ROTA: VISUALIZAR HISTÓRICO DA TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/history")
@login_required
@permission_required('can_view_task_history') # Usando o decorator consolidado
def task_history_view(task_id):
    task_obj = Task.query.get_or_404(task_id)

    history_records = task_obj.history.options(joinedload(TaskHistory.author)).order_by(TaskHistory.timestamp.desc()).all()
    return render_template('task_history.html', title=f'Histórico da Tarefa: {task_obj.title}', task=task_obj, history_records=history_records)


# =========================================================================
# Rotas de Grupos
# =========================================================================
@main.route("/group/new", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def list_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template('list_groups.html', groups=groups, title='Gerenciar Grupos')


@main.route("/group/<int:group_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    if group.users_in_group.first():
        flash('Não é possível excluir este grupo, pois ele contém usuários. Desvincule-os primeiro.', 'danger')
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
@admin_required # Usando o decorator consolidado
def manage_group_members(group_id):
    group = Group.query.get_or_404(group_id)
    form = AssignUsersToGroupForm()
    if form.validate_on_submit():
        current_member_ids = {ug.user_id for ug in group.users_in_group}
        new_member_ids = set(form.users.data)
        for user_id_to_remove in current_member_ids - new_member_ids:
            user_group = UserGroup.query.filter_by(group_id=group.id, user_id=user_id_to_remove).first()
            if user_group:
                user_obj = User.query.get(user_id_to_remove)
                db.session.delete(user_group)
                ChangeLogEntry.log_deletion(
                    user_id=current_user.id,
                    record_type='UserGroup', 
                    record_id=user_group.id,
                    old_data={'user_id': user_id_to_remove, 'username': user_obj.username if user_obj else 'Desconhecido'},
                    description=f"Usuário '{user_obj.username if user_obj else 'Desconhecido'}' removido do grupo '{group.name}'."
                )
        for user_id_to_add in new_member_ids - current_member_ids:
            user_obj = User.query.get(user_id_to_add)
            if user_obj:
                user_group = UserGroup(group=group, user=user_obj)
                db.session.add(user_group)
                ChangeLogEntry.log_creation(
                        user_id=current_user.id,
                        record_type='UserGroup', 
                        record_id=user_group.id, 
                        new_data={'user_id': user_id_to_add, 'username': user_obj.username, 'group_id': group.id, 'group_name': group.name},
                        description=f"Usuário '{user_obj.username}' adicionado ao grupo '{group.name}'."
                    )
        db.session.commit()
        flash('Membros do grupo atualizados com sucesso!', 'success')
        return redirect(url_for('main.manage_group_members', group_id=group.id))
    elif request.method == 'GET':
        form.users.data = [ug.user_id for ug in group.users_in_group]
    return render_template('manage_group_members.html', title=f'Membros do Grupo: {group.name}', group=group, form=form)


# =========================================================================
# Rotas de Permissões de Eventos (SIMPLIFICADAS E PROTEGIDAS)
# =========================================================================
@main.route("/event/<int:event_id>/permissions", methods=['GET', 'POST'])
@login_required
@permission_required('can_manage_permissions') # Usando o decorator consolidado
def manage_event_permissions(event_id):
    event = Event.query.get_or_404(event_id)
    permission_form = EventPermissionForm()
    permission_form.event.data = event 
    if permission_form.validate_on_submit():
        user_id = permission_form.user.data.id 
        
        existing_permission = EventPermission.query.filter_by(event_id=event.id, user_id=user_id).first()
        if existing_permission:
            flash('Este usuário já possui permissão para este evento.', 'info')
            return redirect(url_for('main.manage_event_permissions', event_id=event.id))
        new_permission = EventPermission(event_id=event.id, user_id=user_id)
        try:
            db.session.add(new_permission)
            db.session.commit()
            ChangeLogEntry.log_creation(current_user.id, 'EventPermission', new_permission.id, new_data=new_permission.to_dict(), description=f"Permissão de acesso ao evento '{event.title}' concedida ao usuário ID {user_id}.")
            db.session.commit()
            flash('Permissão de usuário adicionada com sucesso!', 'success')
            return redirect(url_for('main.manage_event_permissions', event_id=event.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar permissão para evento {event_id} e user {user_id}: {e}", exc_info=True)
            flash(f'Erro ao adicionar permissão: {str(e)}', 'danger')
            return redirect(url_for('main.manage_event_permissions', event_id=event.id))
    elif request.method == 'POST':
        flash('Erro ao adicionar permissão. Verifique os campos.', 'danger')
    permissions = EventPermission.query.filter_by(event_id=event.id).options(joinedload(EventPermission.user)).all()
    return render_template('manage_event_permissions.html', 
                            title='Gerenciar Permissões', 
                            event=event, 
                            permission_form=permission_form,
                            permissions=permissions)


@main.route("/event_permission/<int:permission_id>/delete", methods=['POST'])
@login_required
@permission_required('can_manage_permissions') # Usando o decorator consolidado
def delete_event_permission(permission_id):
    permission = EventPermission.query.get_or_404(permission_id)
    event_id = permission.event_id
    
    old_data = permission.to_dict()
    try:
        db.session.delete(permission)
        db.session.commit()
        ChangeLogEntry.log_deletion(current_user.id, 'EventPermission', permission_id, old_data=old_data, description=f"Permissão de acesso ao evento ID {event_id} removida do usuário ID {old_data.get('user_id')}.")
        db.session.commit()
        flash('Permissão removida com sucesso!', 'success')
        return redirect(url_for('main.manage_event_permissions', event_id=event_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar permissão {permission_id}: {e}", exc_info=True)
        flash(f'Erro ao deletar permissão: {str(e)}', 'danger')
        return redirect(url_for('main.manage_event_permissions', event_id=event_id))


# =========================================================================
# Rotas de ChangeLog (Auditoria)
# =========================================================================
@main.route("/changelog")
@login_required
@admin_required # Usando o decorator consolidado
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
@admin_required # Usando o decorator consolidado
def admin_panel():
    return render_template('admin_panel.html', title='Painel Administrativo')


# Rotas de Gerenciamento de Usuários
@main.route('/admin/users')
@login_required
@admin_required # Usando o decorator consolidado
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template('list_users.html', title='Gerenciar Usuários', users=users)


@main.route('/admin/user/new', methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
def new_user():
    form = UserForm(is_new_user=True)
    if form.validate_on_submit():
        try:
            user_role = form.role_obj.data
            if not user_role:
                flash(f'Erro: O papel não foi encontrado ou selecionado.', 'danger')
                return render_template('create_edit_user.html', title='Novo Usuário', form=form, legend='Criar Novo Usuário')
            # CORREÇÃO: ensure password_hash is passed to User constructor
            user = User(username=form.username.data, email=form.email.data, password_hash=generate_password_hash(form.password.data), role_obj=user_role) 
            db.session.add(user)
            db.session.commit()
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
            current_app.logger.error(f"Erro ao criar usuário: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao criar usuário: {str(e)}. Por favor, tente novamente.', 'danger')
    return render_template('create_edit_user.html', title='Novo Usuário', form=form, legend='Criar Novo Usuário')


@main.route('/admin/user/<int:user_id>/update', methods=['GET', 'POST'])
@login_required
@admin_required # Usando o decorator consolidado
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user, original_username=user.username, original_email=user.email, is_new_user=False, role_obj=user.role_obj)
    if form.validate_on_submit():
        try:
            old_data = user.to_dict()
            user.username = form.username.data
            user.email = form.email.data

            new_role_obj = form.role_obj.data
            if not new_role_obj:
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
            current_app.logger.error(f"Erro ao atualizar usuário: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao atualizar usuário: {str(e)}. Por favor, tente novamente.', 'danger')
    return render_template('create_edit_user.html', title='Atualizar Usuário', form=form, legend='Atualizar Usuário', user=user)

@main.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required # Usando o decorator consolidado
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Você não pode deletar sua própria conta através do painel de administração.', 'danger')
        return redirect(url_for('main.list_users'))
    if Event.query.filter_by(author=user).first() or TaskAssignment.query.filter_by(user=user).first() or Comment.query.filter_by(author=user).first():
        flash(f"Não é possível deletar o usuário '{user.username}' porque ele está associado a eventos, tarefas ou comentários. Desvincule-o primeiro.", 'danger')
        return redirect(url_for('main.list_users'))

    try:
        old_data = user.to_dict()

        db.session.delete(user)
        db.session.commit() # Commit da exclusão do usuário

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='User',
            record_id=user_id,
            old_data=old_data,
            description=f"Usuário '{old_data.get('username', 'Nome Desconhecido')}' (ID: {user_id}) deletado."
        )
        db.session.commit() # Commit do ChangeLog
        flash(f"Usuário '{user.username}' deletado com sucesso!", 'success')
        return redirect(url_for('main.list_users'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar usuário: {e}", exc_info=True)
        flash(f'Ocorreu um erro ao deletar usuário: {str(e)}. Por favor, tente novamente.', 'danger')
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
@permission_required('can_upload_task_audio') # Usando o decorator consolidado
def upload_task_audio(task_id):
    task_obj = Task.query.get_or_404(task_id)

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
            
            old_data_for_changelog = task_obj.to_dict() # Captura o estado antes da modificação
            task_obj.audio_path = unique_filename
            task_obj.audio_duration_seconds = audio_duration
            db.session.commit() # Commit da atualização do path do audio

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
            db.session.commit() # Commit do histórico

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task_obj.id,
                old_data=old_data_for_changelog,
                new_data=task_obj.to_dict(), # Captura o novo estado
                description=f"Áudio adicionado/atualizado na tarefa '{task_obj.title}'. Duração: {audio_duration}s."
            )
            db.session.commit() # Commit do ChangeLog

            return jsonify({
                'message': 'Áudio salvo com sucesso!',
                'audio_filename': unique_filename,
                'audio_url_base': url_for('main.serve_audio_file', filename=unique_filename) # Ajustado para Blueprint
            }), 200
        except Exception as e:
            db.session.rollback()
            if os.path.exists(upload_path):
                os.remove(upload_path)
            current_app.logger.error(f"Erro ao salvar audio da tarefa {task_id}: {e}", exc_info=True)
            return jsonify({'message': f'Erro ao salvar audio: {str(e)}'}), 500
    return jsonify({'message': 'Requisição inválida.'}), 400


@main.route("/api/task/<int:task_id>/delete_audio", methods=['DELETE'])
@login_required
@permission_required('can_delete_task_audio') # Usando o decorator consolidado
def delete_task_audio(task_id):
    task_obj = Task.query.get_or_404(task_id)

    if not task_obj.audio_path:
        return jsonify({'message': 'Nenhum audio para remover nesta tarefa.'}), 404
    audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task_obj.audio_path)

    try:
        old_data_for_changelog = task_obj.to_dict() # Captura o estado antes da modificação

        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)

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
        db.session.commit() # Commit do histórico
        
        task_obj.audio_path = None
        task_obj.audio_duration_seconds = None
        db.session.commit() # Commit da atualização do path do audio

        new_data_for_changelog = task_obj.to_dict() # Captura o novo estado
        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_obj.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f"Áudio excluído da tarefa '{task_obj.title}'."
        )
        db.session.commit() # Commit do ChangeLog

        return jsonify({'message': 'Áudio removido com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar audio da tarefa {task_id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao deletar audio: {str(e)}'}), 500


# =========================================================================
# NOVAS ROTAS PARA ANEXOS DE TAREFAS
# =========================================================================
# Rota para servir arquivos de anexo (para download)
@main.route("/uploads/attachments/<path:filename>")
@login_required
def serve_attachment_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER_ATTACHMENTS'], filename)


# Rota para upload de anexo - AGORA SUPORTA VINCULAR A TASKCHECKLISTITEM
@main.route("/attachment/upload/<int:task_id>", defaults={'task_checklist_item_id': None}, methods=['POST'])
@main.route("/attachment/upload/<int:task_id>/<int:task_checklist_item_id>", methods=['POST'])
@login_required
@permission_required('can_upload_attachments') # Usando o decorator consolidado
def upload_attachment(task_id, task_checklist_item_id):
    task_obj = Task.query.get_or_404(task_id)
    
    # Se um task_checklist_item_id foi fornecido, busque-o
    task_checklist_item = None
    if task_checklist_item_id:
        task_checklist_item = TaskChecklistItem.query.get_or_404(task_checklist_item_id)
        # Verificar se o item de checklist pertence à tarefa correta
        if task_checklist_item.task_checklist.task_id != task_id:
            flash('Item de checklist não pertence a esta tarefa.', 'danger')
            return redirect(url_for('main.task_detail', task_id=task_id))

    form = AttachmentForm() # Usar o form para validação do arquivo
    if not form.file.data:
        flash('Nenhum arquivo de anexo fornecido.', 'danger')
        return redirect(url_for('main.task_detail', task_id=task_id))

    # Lógica de upload de arquivo (do seu código original)
    file = form.file.data
    filename = secure_filename(file.filename)
    
    MAX_FILE_SIZE_MB = 20
    file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    unique_filename = str(uuid.uuid4()) + ('.' + file_extension if file_extension else '')
    upload_folder_path = current_app.config['UPLOAD_FOLDER_ATTACHMENTS']
    os.makedirs(upload_folder_path, exist_ok=True)
    upload_path = os.path.join(upload_folder_path, unique_filename)
    
    try:
        file.save(upload_path)
        actual_filesize = os.path.getsize(upload_path)
        if actual_filesize > MAX_FILE_SIZE_MB * 1024 * 1024:
            os.remove(upload_path)
            db.session.rollback() # Desfaz o attachment que foi adicionado (se algum processo foi iniciado)
            flash(f'O arquivo excede o tamanho máximo permitido de {MAX_FILE_SIZE_MB}MB.', 'danger')
            return redirect(url_for('main.task_detail', task_id=task_id))
        
        # Criação do Attachment
        attachment = Attachment(
            task_id=task_obj.id,
            filename=filename,
            unique_filename=unique_filename,
            storage_path=upload_path,
            mimetype=file.mimetype,
            filesize=actual_filesize,
            uploaded_by_user_id=current_user.id,
            task_checklist_item_id=task_checklist_item_id # Víncula ao item de checklist
        )

        # Lógica de aprovação de arte (aplica-se se vinculado a um item de checklist do tipo IMAGE e subcategoria exige)
        if task_checklist_item and \
           (task_checklist_item.custom_field_type == CustomFieldTypeEnum.IMAGE or \
            (task_checklist_item.checklist_item_template and task_checklist_item.checklist_item_template.field_type == CustomFieldTypeEnum.IMAGE)) and \
           task_obj.task_subcategory and task_obj.task_subcategory.requires_art_approval_on_images:
            attachment.art_approval_status = 'pending'
        else:
            attachment.art_approval_status = 'not_required' # Padrão se não for imagem ou não exigir aprovação

        db.session.add(attachment)
        db.session.flush() # Garante que attachment.id seja gerado

        # Se o anexo está vinculado a um TaskChecklistItem, atualiza o value_attachment_ids (uma string JSON de IDs)
        if task_checklist_item:
            # Garante que value_attachment_ids seja uma lista de ints
            attachment_ids_list = json.loads(task_checklist_item.value_attachment_ids) if task_checklist_item.value_attachment_ids else []
            # Validação de min/max images
            template = task_checklist_item.checklist_item_template
            current_attachments_count = len(attachment_ids_list) 
            if template:
                if template.max_images is not None and current_attachments_count >= template.max_images:
                    os.remove(upload_path) # Remove o arquivo recém-subido
                    db.session.rollback() # Desfaz o attachment que foi adicionado
                    flash(f'Limite máximo de {template.max_images} imagens para este item excedido.', 'danger')
                    return redirect(url_for('main.task_detail', task_id=task_id))

            attachment_ids_list.append(attachment.id)
            task_checklist_item.value_attachment_ids = json.dumps(attachment_ids_list)
            db.session.add(task_checklist_item) # Garante que a alteração seja rastreada


        db.session.commit() # Commit principal do attachment e atualização do checklist item

        ChangeLogEntry.log_creation(
            user_id=current_user.id,
            record_type='Attachment',
            record_id=attachment.id,
            new_data=attachment.to_dict(),
            description=f"Anexo '{filename}' adicionado à tarefa '{task_obj.title}' "
                        f"{f'(item {task_checklist_item.custom_label or (task_checklist_item.template_item.label if task_checklist_item.template_item else 'N/A')})' if task_checklist_item else ''} "
                        f"por {current_user.username}. Status de aprovação: {attachment.art_approval_status}."
        )
        db.session.commit() # Commit do ChangeLog
        
        flash('Anexo enviado com sucesso!', 'success')
        return redirect(url_for('main.task_detail', task_id=task_id))

    except Exception as e:
        db.session.rollback()
        if os.path.exists(upload_path):
            os.remove(upload_path)
        current_app.logger.error(f"Erro ao salvar anexo para tarefa {task_obj.id}: {e}", exc_info=True)
        flash(f'Erro ao salvar anexo: {str(e)}', 'danger')
        return redirect(url_for('main.task_detail', task_id=task_id))


# Rota para deletar um anexo
@main.route("/attachment/<int:attachment_id>/delete", methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    task_obj = attachment.task
    
    can_delete = False
    if current_user.is_admin:
        can_delete = True
    elif attachment.uploaded_by_user_id == current_user.id:
        can_delete = True
    elif current_user.role_obj and current_user.role_obj.can_manage_attachments:
        can_delete = True
    elif task_obj and task_obj.event.author_id == current_user.id: # Adicionado check para task_obj
        can_delete = True
    
    if not can_delete:
        return jsonify({'message': 'Você não tem permissão para excluir este anexo.'}), 403

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
    try:
        old_data = attachment.to_dict()
        
        # Se o anexo está vinculado a um TaskChecklistItem, remova-o da lista attachment_ids
        if attachment.task_checklist_item:
            # Garante que value_attachment_ids seja uma lista de ints
            attachment_ids_list = json.loads(attachment.task_checklist_item.value_attachment_ids) if attachment.task_checklist_item.value_attachment_ids else []
            if attachment.id in attachment_ids_list:
                attachment_ids_list.remove(attachment.id)
                attachment.task_checklist_item.value_attachment_ids = json.dumps(attachment_ids_list)
                db.session.add(attachment.task_checklist_item) # Garante que a alteração seja rastreada

        db.session.delete(attachment)
        db.session.commit() # Commit da exclusão do anexo e atualização do checklist item

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Attachment',
            record_id=attachment.id,
            old_data=old_data,
            description=f"Anexo '{attachment.filename}' excluído da tarefa '{task_obj.title if task_obj else 'N/A'}' por {current_user.username}." # Adicionado check para task_obj
        )
        db.session.commit() # Commit do ChangeLog

        return jsonify({'message': 'Anexo excluído com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir anexo do banco de dados {attachment.id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao excluir anexo do banco de dados: {str(e)}'}), 500


# =========================================================================
# NOVAS ROTAS DE API PARA GERENCIAMENTO DE CHECKLISTS E ITENS DE CHECKLIST
# =========================================================================

@main.route("/api/task_checklist_item/<int:item_id>/update", methods=['POST'])
@login_required
@permission_required('can_edit_task') # Exemplo de permissão
def update_task_checklist_item(item_id):
    item = TaskChecklistItem.query.options(joinedload(TaskChecklistItem.task_checklist).joinedload(TaskChecklist.task)).get_or_404(item_id)
    task = item.task_checklist.task

    # Verificar permissão do usuário na tarefa principal (ex: se é responsável, autor do evento, ou admin)
    can_edit_checklist_item = (
        current_user.is_admin or
        task.event.author_id == current_user.id or
        current_user.id in [u.id for u in task.assignees] or
        (current_user.role_obj and current_user.role_obj.can_edit_task)
    )
    if not can_edit_checklist_item:
        return jsonify({'message': 'Você não tem permissão para editar este item de checklist.'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Dados JSON ausentes.'}), 400

    old_data = item.to_dict() # Captura o estado antigo para o log

    # Atualizar campos com base no JSON recebido
    if 'value_text' in data:
        item.value_text = data['value_text']
    if 'value_date' in data:
        try:
            item.value_date = datetime.strptime(data['value_date'], '%Y-%m-%d').date() if data['value_date'] else None
        except ValueError:
            return jsonify({'message': 'Formato de data inválido. Use YYYY-MM-DD.'}), 400
    if 'value_time' in data:
        try:
            item.value_time = datetime.strptime(data['value_time'], '%H:%M').time() if data['value_time'] else None
        except ValueError:
            return jsonify({'message': 'Formato de hora inválido. Use HH:MM.'}), 400
    if 'value_number' in data:
        try:
            item.value_number = int(data['value_number']) if data['value_number'] else None
        except ValueError:
            return jsonify({'message': 'Formato de número inválido.'}), 400
    if 'value_boolean' in data: # Adicionado para boolean
        item.value_boolean = bool(data['value_boolean'])
    if 'is_completed' in data:
        item.is_completed = bool(data['is_completed'])
    
    # value_attachment_ids é atualizado via upload_attachment/delete_attachment

    try:
        db.session.add(item) # Garante que a alteração seja rastreada
        db.session.commit()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='TaskChecklistItem',
            record_id=item.id,
            old_data=old_data,
            new_data=item.to_dict(),
            description=f"Item de checklist '{item.custom_label or (item.template_item.label if item.template_item else 'N/A')}' da tarefa '{task.title}' atualizado."
        )
        db.session.commit()

        return jsonify({'message': 'Item de checklist atualizado com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar TaskChecklistItem {item_id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao atualizar item de checklist: {str(e)}'}), 500


@main.route("/api/task_checklist/<int:checklist_id>/add_item", methods=['POST'])
@login_required
@permission_required('can_edit_task') # Exemplo de permissão
def add_custom_task_checklist_item(checklist_id):
    task_checklist = TaskChecklist.query.options(joinedload(TaskChecklist.task)).get_or_404(checklist_id)
    task = task_checklist.task

    can_add_item = (
        current_user.is_admin or
        task.event.author_id == current_user.id or
        current_user.id in [u.id for u in task.assignees] or
        (current_user.role_obj and current_user.role_obj.can_edit_task)
    )
    if not can_add_item:
        return jsonify({'message': 'Você não tem permissão para adicionar itens a este checklist.'}), 403

    data = request.get_json()
    if not data or 'label' not in data or 'field_type' not in data:
        return jsonify({'message': 'Dados ausentes: label ou field_type são obrigatórios.'}), 400
    
    label = data['label'].strip()
    field_type_str = data['field_type']
    
    try:
        field_type = CustomFieldTypeEnum[field_type_str] # Converte string para o Enum CustomFieldTypeEnum
    except KeyError:
        return jsonify({'message': f'Tipo de campo inválido: {field_type_str}'}), 400

    new_item = TaskChecklistItem(
        task_checklist_id=task_checklist.id,
        custom_label=label,
        custom_field_type=field_type,
        is_completed=False,
    )
    try:
        db.session.add(new_item)
        db.session.commit()

        ChangeLogEntry.log_creation(
            user_id=current_user.id,
            record_type='TaskChecklistItem',
            record_id=new_item.id,
            new_data=new_item.to_dict(),
            description=f"Item de checklist personalizado '{label}' adicionado à tarefa '{task.title}'."
        )
        db.session.commit()

        return jsonify({
            'message': 'Item adicionado com sucesso!',
            'id': new_item.id,
            'label': new_item.custom_label,
            'field_type': new_item.custom_field_type.name,
            'is_completed': new_item.is_completed
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao adicionar item de checklist personalizado à tarefa {task.id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao adicionar item de checklist: {str(e)}'}), 500


@main.route("/api/task_checklist_item/<int:item_id>/delete", methods=['POST']) # Usar POST para deletes via AJAX forms
@login_required
@permission_required('can_edit_task') # Usando o decorator consolidado
def delete_custom_task_checklist_item(item_id):
    item = TaskChecklistItem.query.options(joinedload(TaskChecklistItem.task_checklist).joinedload(TaskChecklist.task)).get_or_404(item_id)
    task = item.task_checklist.task

    can_delete_item = (
        current_user.is_admin or
        task.event.author_id == current_user.id or
        (current_user.role_obj and current_user.role_obj.can_edit_task)
    )
    if not can_delete_item:
        return jsonify({'message': 'Você não tem permissão para deletar este item de checklist.'}), 403
    
    # Impedir exclusão de itens baseados em template (se desejar)
    if item.checklist_item_template_id:
        return jsonify({'message': 'Itens de checklist baseados em template não podem ser excluídos diretamente.'}), 403

    old_data = item.to_dict()
    try:
        # Se houver anexos associados, desvincular ou deletar (decisão de negócio)
        if item.attachments_list: # Corrigido para attachments_list
            for att in item.attachments_list:
                att.task_checklist_item_id = None # Desvincula
                db.session.add(att)

        db.session.delete(item)
        db.session.commit()

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='TaskChecklistItem',
            record_id=item.id,
            old_data=old_data,
            description=f"Item de checklist personalizado '{item.custom_label}' deletado da tarefa '{task.title}'."
        )
        db.session.commit()

        return jsonify({'message': 'Item de checklist deletado com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar item de checklist personalizado {item_id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao deletar item de checklist: {str(e)}'}), 500


# =========================================================================
# ROTA API PARA RETORNAR EVENTOS E TAREFAS PARA O CALENDÁRIO
# =========================================================================
@main.route("/api/calendar_events", methods=['GET'])
@login_required
def calendar_events_feed():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    start = datetime.fromisoformat(start_str) if start_str else None
    end = datetime.fromisoformat(end_str) if end_str else None

    events_for_calendar = []
    events_query = Event.query.options(
        joinedload(Event.author),
        joinedload(Event.event_status),
        joinedload(Event.category),
        joinedload(Event.event_permissions),
        joinedload(Event.tasks).joinedload(Task.assignees_associations).joinedload(TaskAssignment.user)
    )
    events_query = events_query.filter(Event.is_cancelled == False)
    if not current_user.is_admin:
        event_conditions = [
            Event.author_id == current_user.id,
            Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id)),
            Event.event_permissions.any(EventPermission.user_id == current_user.id)
        ]
        active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
        if active_status_obj:
            events_query = events_query.filter(and_(or_(*event_conditions), Event.is_published == True, Event.is_cancelled == False, Event.event_status == active_status_obj))
        else:
            events_query = events_query.filter(false())
    
    if start and end:
        events_query = events_query.filter(
            or_(
                and_(Event.due_date >= start, Event.due_date <= end),
                and_(Event.end_date >= start, Event.end_date <= end),
                and_(Event.due_date < start, Event.end_date > end),
                and_(Event.due_date >= start, Event.due_date <= end, Event.end_date == None)
            )
        )
    all_visible_events = events_query.all()
    for event_obj in all_visible_events:
        event_color = "#3788d8"
        if event_obj.is_cancelled:
            event_color = "#6c757d"
        elif event_obj.event_status and event_obj.event_status.name == 'Realizado':
            event_color = "#28a745"
        elif event_obj.event_status and event_obj.event_status.name == 'Arquivado':
            event_color = "#6c757d"
        elif event_obj.due_date and event_obj.due_date < datetime.utcnow() and not (event_obj.event_status and event_obj.event_status.name == 'Realizado'):
            event_color = "#dc3545"
        events_for_calendar.append({
            'id': f"event-{event_obj.id}",
            'title': event_obj.title,
            'start': event_obj.due_date.isoformat(),
            'end': (event_obj.end_date + timedelta(days=1)).isoformat() if event_obj.end_date else (event_obj.due_date + timedelta(days=1)).isoformat(),
            'url': url_for('main.event', event_id=event_obj.id),
            'color': event_color,
            'extendedProps': {
                'description': event_obj.description,
                'type': 'Evento',
                'location': event_obj.location,
                'status': event_obj.event_status.name if event_obj.event_status else 'N/A'
            },
            'allDay': not (event_obj.due_date.time() != datetime.min.time() or (event_obj.end_date and event_obj.end_date.time() != datetime.min.time()))
        })
    tasks_query = Task.query.options(
        joinedload(Task.assignees_associations).joinedload(TaskAssignment.user),
        joinedload(Task.event),
        joinedload(Task.task_status_rel)
    )
    if not current_user.is_admin:
        event_conditions = [
            Event.author_id == current_user.id,
            Event.tasks.any(Task.assignees_associations.any(TaskAssignment.user_id == current_user.id)),
            Event.event_permissions.any(EventPermission.user_id == current_user.id)
        ]
        active_status_obj = Status.query.filter_by(name='Ativo', type='event').first()
        if active_status_obj:
            tasks_query = tasks_query.join(Event).filter(and_(or_(*event_conditions), Event.is_published == True, Event.is_cancelled == False, Event.event_status == active_status_obj))
        else:
            tasks_query = tasks_query.filter(false())
    else:
        tasks_query = tasks_query.join(Event).filter(Event.is_cancelled == False)
    if start and end:
        tasks_query = tasks_query.filter(
            and_(Task.due_date >= start, Task.due_date <= end)
        )
    all_visible_tasks = tasks_query.all()
    for task_obj in all_visible_tasks:
        task_color = "#ffc107"
        if task_obj.is_completed:
            task_color = "#28a745"
        elif task_obj.due_date and task_obj.due_date < datetime.utcnow() and not task_obj.is_completed:
            task_color = "#dc3545"
        
        events_for_calendar.append({
            'id': f"task-{task_obj.id}",
            'title': task_obj.title,
            'start': task_obj.due_date.isoformat(),
            'end': (task_obj.due_date + timedelta(minutes=60)).isoformat(),
            'url': url_for('main.task_detail', task_id=task_obj.id),
            'color': task_color,
            'extendedProps': {
                'description': task_obj.description,
                'type': 'Tarefa',
                'event_title': task_obj.event.title if task_obj.event else 'N/A',
                'status': task_obj.task_status_rel.name if task_obj.task_status_rel else 'N/A'
            },
            'allDay': not (task_obj.due_date.time() != datetime.min.time())
        })
    
    return jsonify(events_for_calendar)


# =========================================================================
# NOVAS ROTAS DE NOTIFICAÇÕES
# =========================================================================
@main.route("/notifications") 
@login_required
def notifications(): 
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    # Marcar todas como lidas ao visualizar a página de notificações
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
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    flash('Notificação marcada como lida.', 'success')
    return redirect(url_for('main.notifications'))


@main.route("/api/notifications/unread_count")
@login_required
def unread_notifications_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})

# Rota para salvar a subscription de push notification
@main.route('/api/save-subscription', methods=['POST'])
@login_required
def save_subscription():
    data = request.get_json()
    if not data or not data.get('subscription'):
        return jsonify({'success': False, 'message': 'Dados de assinatura inválidos'}), 400

    endpoint = data['subscription']['endpoint']
    # Verifique se a subscription já existe para o usuário atual
    existing_subscription = PushSubscription.query.filter_by(user_id=current_user.id, endpoint=endpoint).first()
    if existing_subscription:
        return jsonify({'success': True, 'message': 'Assinatura já existe'}), 200 # CORREÇÃO: Linha 3281, string completa

    try:
        new_subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=data['subscription']['keys']['p256dh'],
            auth=data['subscription']['keys']['auth']
        )
        db.session.add(new_subscription)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Assinatura salva com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar assinatura de push para o usuário {current_user.id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Erro ao salvar assinatura: {str(e)}'}), 500


# =========================================================================
# NOVO: API para busca de usuários para @menções
# =========================================================================
@main.route("/api/users/search", methods=['GET'])
@login_required
def search_users_api():
    query = request.args.get('q', '').strip()
    users_data = []
    if query:
        # Busca por usuários cujo username ou email contenham a string da query
        # Limitado a 10 resultados para performance
        users = User.query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(10).all()

        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email
            })
    
    return jsonify(users_data)


# =========================================================================================
# ROTA PARA SERVIR O SERVICE WORKER 
# =========================================================================================
@main.route('/service-worker.js')
def serve_service_worker():
    """Serve o arquivo service-worker.js da pasta static."""
    # current_app.send_static_file procura na pasta 'static' definida para o blueprint
    # Você deve ter o arquivo 'service-worker.js' dentro da sua pasta 'static'
    return current_app.send_static_file('service-worker.js')