from flask import render_template, url_for, flash, redirect, request, Blueprint, jsonify, current_app, abort
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from extensions import db

# MODIFIED: Importado TaskCategoryForm
from forms import RegistrationForm, LoginForm, EventForm, CategoryForm, StatusForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm, SearchForm, TaskForm, UserForm, TaskCategoryForm
# MODIFIED: Importado TaskCategory
from models import User, Event, Task, TaskAssignment, ChangeLogEntry, EventStatus, TaskStatus, Category, PasswordResetToken, TaskHistory, TaskCategory
from sqlalchemy import func, or_, distinct, false
from datetime import datetime, date, timedelta
import json
from sqlalchemy.orm import joinedload
import uuid
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory
from utils.changelog_utils import diff_dicts

from decorators import admin_required, project_manager_required, role_required

main = Blueprint('main', __name__)

# --- FUNÇÃO AUXILIAR PARA ENVIAR E-MAIL DE REDEFINIÇÃO DE SENHA (AGORA UTILIZA O NOVO MODELO) ---
def send_reset_email(user):
    # 1. Invalida quaisquer tokens de redefinição de senha não utilizados e não expirados para este usuário.
    active_tokens = PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).all()
    for token_obj in active_tokens:
        db.session.delete(token_obj)
    db.session.commit()

    # 2. Gera um novo UUID único para este token de redefinição
    token_uuid_str = str(uuid.uuid4())
    expires_in_seconds = 3600

    # 3. Cria uma nova entrada na tabela PasswordResetToken no banco de dados
    reset_token_db_entry = PasswordResetToken(
        user_id=user.id,
        token_uuid=token_uuid_str,
        expiration_date=datetime.utcnow() + timedelta(seconds=expires_in_seconds),
        is_used=False
    )
    db.session.add(reset_token_db_entry)
    db.session.commit()

    # 4. Assina o UUID usando URLSafeTimedSerializer do Flask
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset-salt')
    signed_token = s.dumps(token_uuid_str)

    # 5. Prepara e envia o e-mail
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

# Defina quantos itens você quer por página (para o ChangeLog)
LOGS_PER_PAGE = 10

# --- FUNÇÃO AUXILIAR PARA FILTRAGEM E PAGINAÇÃO DE EVENTOS ---
def get_filtered_events(user, search_query, page, per_page, event_status_name=None):
    """
    Função auxiliar para construir a query de eventos com base no status, pesquisa e permissões do usuário.
    Retorna um objeto de paginação de eventos.
    """
    # Base query com eager loading para otimização
    base_query = Event.query.options(
        joinedload(Event.status),     # Carrega o status do evento
        joinedload(Event.category),   # Carrega a categoria do evento
        joinedload(Event.author)      # Carrega o autor do evento
    )

    # Lógica de filtragem por permissão: Admin vê tudo, outros usuários veem eventos que criaram OU que foram atribuídos.
    if not current_user.is_admin:
        # Se não for admin, filtre por eventos criados pelo usuário OU onde o usuário está atribuído a alguma tarefa
        base_query = base_query.filter(
            or_(
                Event.author == current_user,  # Eventos criados pelo usuário logado
                Event.id.in_(  # Eventos onde o usuário está atribuído a alguma tarefa
                    db.session.query(distinct(Event.id))
                    .join(Event.tasks)
                    .join(Task.assignees_associations)
                    .filter(TaskAssignment.user_id == current_user.id)
                )
            )
        )

    # Aplica filtro por termo de pesquisa
    search_query_text = request.args.get('search', '')
    if search_query_text:
        base_query = base_query.filter(
            or_(
                Event.title.ilike(f'%{search_query_text}%'),
                Event.description.ilike(f'%{search_query_text}%')
            )
        )
    
    # Aplica filtro por status, se fornecido
    if event_status_name:
        event_status = EventStatus.query.filter_by(name=event_status_name).first()
        if event_status:
            base_query = base_query.filter(Event.status == event_status)
        else:
            # Se o status_name não existir, retorna uma query que não trará resultados
            current_app.logger.warning(f"Status de Evento '{event_status_name}' solicitado, mas não encontrado no banco de dados.")
            return Event.query.filter(false()).paginate(page=page, per_page=per_page, error_out=False)

    # Ordena eventos por data de vencimento (due_date) em ordem ascendente
    base_query = base_query.order_by(Event.due_date.asc())

    # Retorna o objeto de paginação
    return base_query.paginate(page=page, per_page=per_page, error_out=False)


@main.route("/")
@main.route("/home")
@login_required
def home():
    # A rota home agora lista TODOS os eventos visíveis para o usuário (sem filtro de status específico)
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    events = get_filtered_events(current_user, search_query, page, per_page)
    
    # Modificação: Adiciona current_filter para destacar o filtro ativo no template
    return render_template('home.html', events=events, title='Todos os Eventos', search_query=search_query, current_filter='all')

@main.route("/events/active")
@login_required
def active_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    # Usa a função auxiliar para filtrar por status "Ativo"
    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Ativo')
    
    # Modificação: Adiciona current_filter para destacar o filtro ativo no template
    return render_template('home.html', events=events, title='Eventos Ativos', search_query=search_query, current_filter='active')

@main.route("/events/completed")
@login_required
def completed_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    # Usa a função auxiliar para filtrar por status "Realizado"
    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Realizado')
    
    # Modificação: Adiciona current_filter para destacar o filtro ativo no template
    return render_template('home.html', events=events, title='Eventos Realizados', search_query=search_query, current_filter='completed')

@main.route("/events/archived")
@login_required
def archived_events():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5

    # Usa a função auxiliar para filtrar por status "Arquivado"
    events = get_filtered_events(current_user, search_query, page, per_page, event_status_name='Arquivado')
    
    # Modificação: Adiciona current_filter para destacar o filtro ativo no template
    return render_template('home.html', events=events, title='Eventos Arquivados', search_query=search_query, current_filter='archived')


# --- FIM DAS ROTAS DE LISTAGEM DE EVENTOS MODIFICADAS ---

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
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

@main.route("/event/new", methods=['GET', 'POST'])
@login_required
def new_event(): 
    form = EventForm()
    
    if form.validate_on_submit():
        selected_category = form.category.data 
        selected_status = form.status.data 

        event = Event(title=form.title.data, description=form.description.data,
                      due_date=form.due_date.data, end_date=form.end_date.data, 
                      location=form.location.data, author=current_user,
                      category=selected_category, 
                      status=selected_status)     
        db.session.add(event)
        db.session.commit()
        
        ChangeLogEntry.log_creation(
            user_id=current_user.id,
            record_type='Event',
            record_id=event.id,
            new_data=event.to_dict(),
            description=f'Evento "{event.title}" criado.'
        )
        db.session.commit()

        flash('Seu evento foi criado!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_edit_event.html', title='Novo Evento', form=form, legend='Criar Evento')

@main.route("/event/<int:event_id>")
@login_required
def event(event_id):
    # Carrega o evento e suas tarefas, e para cada tarefa, seus atribuídos e os detalhes do usuário atribuído.
    event = Event.query.options(
        joinedload(Event.tasks) \
        .joinedload(Task.assignees_associations) \
        .joinedload(TaskAssignment.user)
    ).get_or_404(event_id)

    # Lógica de permissão de visualização
    if current_user.is_admin:
        can_view = True
    else:
        can_view = any(current_user in [assignment.user for assignment in task.assignees_associations if assignment.user]
                       for task in event.tasks)

    if not can_view:
        flash('Você não tem permissão para visualizar este evento.', 'danger')
        return redirect(url_for('main.home'))

    # Carrega todas as tarefas do evento e as separa em ativas e finalizadas
    # Ordena as ativas por due_date e as finalizadas por completed_at (mais recente primeiro)
    active_tasks = sorted([task for task in event.tasks if not task.is_completed], key=lambda t: t.due_date)
    completed_tasks = sorted([task for task in event.tasks if task.is_completed], key=lambda t: t.completed_at if t.completed_at else datetime.min, reverse=True)

    # Passa a data atual para o template para formatação condicional
    current_date = date.today()

    # Passa as listas de tarefas ativas e finalizadas para o template
    return render_template('event.html', title=event.title, event=event, active_tasks=active_tasks, completed_tasks=completed_tasks, current_date=current_date)


@main.route("/event/<int:event_id>/update", methods=['GET', 'POST'])
@login_required
def update_event(event_id): 
    event = Event.query.get_or_404(event_id)
    # Autorização: Apenas o autor do evento ou um administrador pode editá-lo.
    if not current_user.is_admin and event.author != current_user:
        flash('Você não tem permissão para editar este evento.', 'danger')
        return redirect(url_for('main.home'))

    form = EventForm(obj=event) 

    if form.validate_on_submit():
        old_data = event.to_dict() 

        selected_category = form.category.data 
        selected_status = form.status.data 

        event.title = form.title.data
        event.description = form.description.data
        event.due_date = form.due_date.data 
        event.end_date = form.end_date.data 
        event.location = form.location.data 
        event.category = selected_category 
        event.status = selected_status 
        db.session.commit()
        
        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Event',
            record_id=event.id,
            old_data=old_data,
            new_data=event.to_dict(),
            description=f'Evento "{event.title}" atualizado.'
        )
        db.session.commit()

        flash('Seu evento foi atualizado!', 'success')
        return redirect(url_for('main.event', event_id=event.id))
    elif request.method == 'GET':
        pass
    return render_template('create_edit_event.html', title='Atualizar Evento', form=form, legend='Atualizar Evento', event=event)

@main.route("/event/<int:event_id>/delete", methods=['POST']) 
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    # Autorização: Apenas o autor do evento ou um administrador pode excluí-lo
    if not current_user.is_admin and event.author != current_user:
        flash('Você não tem permissão para excluir este evento.', 'danger')
        return redirect(url_for('main.home'))
    
    try:
        old_data = event.to_dict() 

        db.session.delete(event)

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Event',
            record_id=event_id, 
            old_data=old_data,
            description=f'Evento "{old_data.get("title", "Título Desconhecido")}" excluído.'
        )
        db.session.commit() 

        flash('Seu evento foi excluído!', 'success')
        return redirect(url_for('main.home'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o evento: {e}. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.home'))

@main.route("/event/<int:event_id>/task/new", methods=['GET', 'POST']) 
@login_required
def new_task(event_id): 
    event = Event.query.get_or_404(event_id)
    # Autorização: Apenas o autor do evento ou um administrador pode adicionar tarefas a ele.
    if not current_user.is_admin and event.author != current_user:
        flash('Você não tem permissão para adicionar tarefas a este evento.', 'danger')
        return redirect(url_for('main.home'))

    form = TaskForm()

    if not User.query.first():
        flash('Não há usuários cadastrados no sistema para atribuir tarefas. Crie usuários primeiro.', 'info')
        
    if form.validate_on_submit():
        print(f"--- DEBUG: new_task - Formulário validado com sucesso! ---") 
        try:
            # MODIFIED: Usando form.task_category.data e atribuindo a task_category no modelo Task
            selected_task_category = form.task_category.data # MODIFIED
            selected_task_status = form.status.data

            task = Task(
                title=form.title.data,
                description=form.description.data,
                due_date=form.due_date.data, 
                event=event, 
                task_category=selected_task_category, # MODIFIED: de 'category' para 'task_category'
                task_status=selected_task_status,
                notes=form.notes.data,
                cloud_storage_link=form.cloud_storage_link.data,
                link_notes=form.link_notes.data
            ) 

            db.session.add(task)
            db.session.flush() 
            print(f"--- DEBUG: new_task - Tarefa adicionada à sessão e ID gerado: {task.id} ---") 

            selected_users = form.assignees.data 
            print(f"--- DEBUG: new_task - Usuários selecionados no formulário: {[u.username for u in selected_users]} ---") 

            if not selected_users:
                 print("--- DEBUG: new_task - Nenhum usuário selecionado para atribuição. ---") 

            for user_obj in selected_users: 
                assignment = TaskAssignment(task=task, user=user_obj) 
                db.session.add(assignment)
                print(f"--- DEBUG: new_task - Adicionando atribuição: Tarefa '{task.title}' para Usuário '{user_obj.username}' ---") 
            
            db.session.commit() 
            print("--- DEBUG: new_task - Transação comitada com sucesso! ---") 

            # >>> NOVO CÓDIGO AQUI para registrar a criação no histórico (TaskHistory)
            history_description = f'Tarefa "{task.title}" criada.'
            history_new_value = {
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'status': task.task_status.name if task.task_status else 'N/A',
                # MODIFIED: De 'category' para 'task_category'
                'task_category': task.task_category.name if task.task_category else 'N/A', # MODIFIED
                'event_title': task.event.title if task.event else 'N/A'
            }
            history_entry = TaskHistory(
                task_id=task.id,
                action_type='creation',
                description=history_description,
                old_value=None,
                new_value=json.dumps(history_new_value), # Armazena como string JSON
                user_id=current_user.id,
                comment=f"Criada por {current_user.username}"
            )
            db.session.add(history_entry)
            db.session.commit() # Comita a entrada do histórico
            # <<< FIM DO NOVO CÓDIGO

            # Log da criação da tarefa (já existente ChangeLogEntry)
            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='Task',
                record_id=task.id,
                new_data=task.to_dict(),
                description=f'Tarefa "{task.title}" criada no evento "{event.title}".'
            )
            db.session.commit() 

            flash('Sua tarefa foi criada!', 'success')
            return redirect(url_for('main.event', event_id=event.id))
        except Exception as e:
            db.session.rollback() 
            flash(f'Ocorreu um erro ao criar a tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar tarefa: {e}", exc_info=True) 
            print(f"--- DEBUG: new_task - ERRO: {e} ---") 
    else: 
        print(f"--- DEBUG: new_task - Validação do formulário FALHOU. Erros: {form.errors} ---")
            
    return render_template('create_edit_task.html', title='Nova Tarefa', form=form, legend='Criar Tarefa', event=event)

@main.route("/task/<int:task_id>/update", methods=['GET', 'POST']) 
@login_required
def update_task(task_id): 
    task = Task.query.get_or_404(task_id)
    
    # Autorização: Administrador pode editar qualquer tarefa; outros usuários apenas as atribuídas.
    if not current_user.is_admin and current_user not in task.assignees:
        flash('Você não tem permissão para editar esta tarefa, pois não está atribuído a ela.', 'danger')
        return redirect(url_for('main.event', event_id=task.event.id))

    form = TaskForm(obj=task) 

    if not User.query.first():
        flash('Não há usuários cadastrados no sistema para atribuir tarefas. Crie usuários primeiro.', 'info')

    if request.method == 'GET':
        existing_assignees = task.assignees
        form.assignees.data = existing_assignees
        form.cloud_storage_link.data = task.cloud_storage_link
        form.link_notes.data = task.link_notes
        # MODIFIED: Preencher o campo task_category do formulário com a categoria da tarefa existente
        form.task_category.data = task.task_category # MODIFIED
        print(f"--- DEBUG: update_task - GET: Usuários pré-populados: {[u.username for u in existing_assignees]} ---") 
    
    if form.validate_on_submit():
        print("--- DEBUG: update_task - Formulário validado com sucesso! ---") 
        try:
            # Captura dados antigos antes da modificação para TaskHistory e ChangeLogEntry
            old_task_data_for_changelog = task.to_dict()

            old_task_data_for_history = {
                'title': task.title,
                'description': task.description,
                'notes': task.notes,
                'due_date': task.due_date,
                'task_status_id': task.task_status_id,
                'task_category_id': task.task_category_id, # MODIFIED: de 'category_id' para 'task_category_id'
                'cloud_storage_link': task.cloud_storage_link,
                'link_notes': task.link_notes,
                'assignees_ids': sorted([u.id for u in task.assignees]) if task.assignees else []
            }
            old_status_name = task.task_status.name if task.task_status else 'N/A'
            # MODIFIED: De task.category.name para task.task_category.name
            old_category_name = task.task_category.name if task.task_category else 'N/A' # MODIFIED
            old_assignee_names = sorted([u.username for u in task.assignees]) if task.assignees else []

            # MODIFIED: Usando form.task_category.data
            selected_task_category = form.task_category.data # MODIFIED
            selected_task_status = form.status.data

            # Aplica dados do formulário ao objeto da tarefa
            task.title = form.title.data
            task.description = form.description.data
            task.notes = form.notes.data 
            task.due_date = form.due_date.data 
            task.task_category = selected_task_category # MODIFIED: de 'task.category' para 'task.task_category'
            task.task_status = selected_task_status
            task.cloud_storage_link = form.cloud_storage_link.data
            task.link_notes = form.link_notes.data
            
            # Lidar com atualização de responsáveis
            new_assignee_ids = sorted([u.id for u in form.assignees.data]) if form.assignees.data else []
            assignees_changed = old_task_data_for_history['assignees_ids'] != new_assignee_ids

            if assignees_changed:
                TaskAssignment.query.filter_by(task_id=task.id).delete()
                db.session.flush() # Comita exclusões para evitar conflitos com novas inserções
                print(f"--- DEBUG: update_task - Deletadas atribuições existentes para a tarefa {task.id}. ---")

                selected_users = form.assignees.data
                print(f"--- DEBUG: update_task - Usuários selecionados no formulário: {[u.username for u in selected_users]} ---") 

                if not selected_users:
                     print("--- DEBUG: update_task - Nenhum usuário selecionado para atribuição. ---") 

                for user_obj in selected_users: 
                    assignment = TaskAssignment(task=task, user=user_obj) 
                    db.session.add(assignment)
                    print(f"--- DEBUG: update_task - Adicionando nova atribuição: Tarefa '{task.title}' para Usuário '{user_obj.username}' ---") 
            
            db.session.commit() # Comita todas as alterações da tarefa (e novas atribuições se responsáveis mudaram)
            print("--- DEBUG: update_task - Transação comitada com sucesso! ---") 

            # Captura novos dados após a modificação para TaskHistory e ChangeLogEntry
            new_task_data_for_changelog = task.to_dict()

            new_task_data_for_history = {
                'title': task.title,
                'description': task.description,
                'notes': task.notes,
                'due_date': task.due_date,
                'task_status_id': task.task_status_id,
                'task_category_id': task.task_category_id, # MODIFIED: de 'category_id' para 'task_category_id'
                'cloud_storage_link': task.cloud_storage_link,
                'link_notes': task.link_notes,
                'assignees_ids': sorted([u.id for u in task.assignees]) if task.assignees else []
            }
            new_status_name = task.task_status.name if task.task_status else 'N/A'
            # MODIFIED: De task.category.name para task.task_category.name
            new_category_name = task.task_category.name if task.task_category else 'N/A' # MODIFIED
            new_assignee_names = sorted([u.username for u in task.assignees]) if task.assignees else []

            # >>> NOVO CÓDIGO AQUI para registrar a edição no histórico (TaskHistory)
            changes_logged_in_history = False
            
            if old_task_data_for_history['title'] != new_task_data_for_history['title']:
                history_entry = TaskHistory(
                    task_id=task.id,
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
                    task_id=task.id,
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
                    task_id=task.id,
                    action_type='updated',
                    description='Notas da tarefa alteradas',
                    old_value=json.dumps({'notes': old_task_data_for_history['notes']}),
                    new_value=json.dumps({'notes': new_task_data_for_history['notes']}),
                    user_id=current_user.id,
                    comment=f"Notas alteradas."
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            # Comparação de datas exige formatação para string
            old_due_date_str = old_task_data_for_history['due_date'].strftime('%Y-%m-%d') if old_task_data_for_history['due_date'] else None
            new_due_date_str = new_task_data_for_history['due_date'].strftime('%Y-%m-%d') if new_task_data_for_history['due_date'] else None

            if old_due_date_str != new_due_date_str:
                history_entry = TaskHistory(
                    task_id=task.id,
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
                    task_id=task.id,
                    action_type='updated',
                    description='Status da tarefa alterado',
                    old_value=json.dumps({'status': old_status_name}),
                    new_value=json.dumps({'status': new_status_name}),
                    user_id=current_user.id,
                    comment=f"Status alterado de '{old_status_name}' para '{new_status_name}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True

            # MODIFIED: Verificar e logar mudanças na task_category
            if old_task_data_for_history['task_category_id'] != new_task_data_for_history['task_category_id']: # MODIFIED
                history_entry = TaskHistory(
                    task_id=task.id,
                    action_type='updated',
                    description='Categoria da tarefa alterada', # Mantém "Categoria da tarefa"
                    old_value=json.dumps({'task_category': old_category_name}), # MODIFIED: Chave para 'task_category'
                    new_value=json.dumps({'task_category': new_category_name}), # MODIFIED: Chave para 'task_category'
                    user_id=current_user.id,
                    comment=f"Categoria da tarefa alterada de '{old_category_name}' para '{new_category_name}'" # MODIFIED: Texto
                )
                db.session.add(history_entry)
                changes_logged_in_history = True
            
            if old_task_data_for_history['cloud_storage_link'] != new_task_data_for_history['cloud_storage_link']:
                history_entry = TaskHistory(
                    task_id=task.id,
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
                    task_id=task.id,
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
                    task_id=task.id,
                    action_type='updated',
                    description='Responsáveis pela tarefa alterados',
                    old_value=json.dumps({'assignees': old_assignee_names}),
                    new_value=json.dumps({'assignees': new_assignee_names}),
                    user_id=current_user.id,
                    comment=f"Responsáveis alterados de '{', '.join(old_assignee_names) or 'Nenhum'}' para '{', '.join(new_assignee_names) or 'Nenhum'}'"
                )
                db.session.add(history_entry)
                changes_logged_in_history = True
            
            # Comita todas as mudanças do TaskHistory se houveram
            if changes_logged_in_history:
                db.session.commit()
            # <<< FIM NOVO CÓDIGO

            # Log da atualização da tarefa (já existente ChangeLogEntry)
            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task.id,
                old_data=old_task_data_for_changelog,
                new_data=new_task_data_for_changelog,
                description=f'Tarefa "{task.title}" atualizada no evento "{task.event.title}".'
            )
            db.session.commit() 

            flash('Sua tarefa foi atualizada!', 'success')
            return redirect(url_for('main.event', event_id=task.event.id))
        except Exception as e:
            db.session.rollback() 
            flash(f'Ocorreu um erro ao atualizar a tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar tarefa: {e}", exc_info=True) 
            print(f"--- DEBUG: update_task - ERRO: {e} ---") 
            
    else: 
        print(f"--- DEBUG: update_task - Validação do formulário FALHOU. Erros: {form.errors} ---")
            
    return render_template('create_edit_task.html', title='Atualizar Tarefa', form=form, legend='Atualizar Tarefa', task=task, event=task.event)

@main.route("/task/<int:task_id>/delete", methods=['POST']) 
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Autorização: Administrador pode excluir qualquer tarefa; outros usuários apenas se for o autor do evento.
    if not current_user.is_admin and task.event.author != current_user:
        flash('Você não tem permissão para excluir esta tarefa.', 'danger')
        return redirect(url_for('main.event', event_id=task.event.id))
    
    try:
        old_data = task.to_dict() 

        if task.audio_path:
            audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task.audio_path)
            if os.path.exists(audio_filepath):
                os.remove(audio_filepath)
                current_app.logger.info(f"Áudio '{task.audio_path}' removido para tarefa {task_id}.")

        db.session.delete(task)

        # NÃO PRECISA LOGAR NO TASKHISTORY AQUI, POIS A TAREFA SERÁ DELETADA E O CASCADE DELETE-ORPHAN REMOVERÁ OS HISTÓRICOS.
        # SE QUISER REGISTRAR A EXCLUSÃO DA TAREFA, DEVE SER NO ChangeLogEntry.
        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='Task',
            record_id=task_id, 
            old_data=old_data,
            description=f'Tarefa "{old_data.get("title", "Título Desconhecido")}" excluída do evento "{task.event.title}".'
        )
        db.session.commit() 

        flash('Sua tarefa foi excluída!', 'success')
        return redirect(url_for('main.event', event_id=task.event.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a tarefa: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao excluir tarefa: {e}", exc_info=True)
        return redirect(url_for('main.event', event_id=task.event.id))

# =========================================================================
# NOVA ROTA: CONCLUIR TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/complete", methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    comment = request.form.get('completion_comment') # Obtém o comentário do formulário

    # Autorização: Apenas o autor do evento, um administrador ou um usuário atribuído à tarefa pode concluir.
    is_assigned = current_user in task.assignees
    
    if not current_user.is_admin and task.event.author != current_user and not is_assigned:
        flash('Você não tem permissão para concluir esta tarefa.', 'danger')
        return redirect(url_for('main.event', event_id=task.event.id))

    if task.is_completed:
        flash('Esta tarefa já está concluída.', 'info')
        return redirect(url_for('main.event', event_id=task.event.id))

    try:
        old_data_for_changelog = task.to_dict() # Captura o estado antigo da tarefa para o changelog

        task.is_completed = True
        task.completed_at = datetime.utcnow()
        task.completed_by_id = current_user.id
        
        # >>> NOVO CÓDIGO AQUI para registrar a conclusão no TaskHistory
        history_entry = TaskHistory(
            task_id=task.id,
            action_type='conclusao', # Mantendo 'conclusao' como solicitado, embora 'completed' seja mais padrão.
            description=f'Tarefa "{task.title}" marcada como concluída.',
            old_value=json.dumps({'is_completed': False, 'completed_at': None, 'completed_by_id': None}), # Estado antigo
            new_value=json.dumps({'is_completed': True, 'completed_at': task.completed_at.isoformat(), 'completed_by_id': task.completed_by_id}), # Novo estado
            user_id=current_user.id,
            comment=comment
        )
        db.session.add(history_entry)
        # <<< FIM NOVO CÓDIGO

        db.session.commit() # Comita todas as alterações, incluindo a tarefa e a entrada no TaskHistory

        new_data_for_changelog = task.to_dict() # Captura o novo estado da tarefa para o changelog

        # Loga também no ChangeLogEntry (para auditoria geral do sistema)
        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f'Tarefa "{task.title}" concluída por {current_user.username}.' + (f' Comentário: "{comment}"' if comment else '')
        )
        db.session.commit()

        flash('Tarefa concluída com sucesso!', 'success')
        return redirect(url_for('main.event', event_id=task.event.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao concluir a tarefa: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao concluir tarefa {task_id}: {e}", exc_info=True)
        return redirect(url_for('main.event', event_id=task.event.id))

# =========================================================================
# FIM NOVA ROTA: CONCLUIR TAREFA
# =========================================================================

# =========================================================================
# NOVA ROTA: VISUALIZAR HISTÓRICO DA TAREFA
# =========================================================================
@main.route("/task/<int:task_id>/history")
@login_required
def task_history_view(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Autorização: Apenas o autor do evento, um administrador ou um usuário atribuído à tarefa pode ver o histórico.
    is_assigned = current_user in task.assignees
    
    if not current_user.is_admin and task.event.author != current_user and not is_assigned:
        flash('Você não tem permissão para visualizar o histórico desta tarefa.', 'danger')
        return redirect(url_for('main.event', event_id=task.event.id))

    # Usando o relacionamento 'history' com lazy='dynamic' e carregando o autor da entrada do histórico
    history_records = task.history.options(joinedload(TaskHistory.author)).order_by(TaskHistory.timestamp.desc()).all()

    return render_template('task_history.html', title=f'Histórico da Tarefa: {task.title}', task=task, history_records=history_records)
# =========================================================================
# FIM NOVA ROTA: VISUALIZAR HISTÓRICO DA TAREFA
# =========================================================================


@main.route("/statuses/<string:status_type>") 
@login_required
@admin_required 
def list_statuses(status_type):
    if status_type == 'event':
        statuses = EventStatus.query.order_by(EventStatus.name).all()
        title = "Status de Eventos"
    elif status_type == 'task':
        statuses = TaskStatus.query.order_by(TaskStatus.name).all()
        title = "Status de Tarefas"
    else:
        abort(404) 
    return render_template('list_statuses.html', statuses=statuses, title=title, status_type=status_type)

@main.route("/status/<string:status_type>/new", methods=['GET', 'POST']) 
@login_required
@admin_required 
def new_status(status_type): 
    form = StatusForm() 
    if form.validate_on_submit():
        try:
            if status_type == 'event':
                status = EventStatus(name=form.name.data, description=form.description.data)
            elif status_type == 'task':
                status = TaskStatus(name=form.name.data, description=form.description.data)
            else:
                abort(404) 
            
            db.session.add(status)
            db.session.commit()

            ChangeLogEntry.log_creation(
                user_id=current_user.id, record_type='EventStatus', record_id=status.id,
                new_data={'id': status.id, 'name': status.name, 'description': status.description},
                description=f'Status de Evento "{status.name}" criado.'
            )
            db.session.commit()
            
            flash(f'Status "{status.name}" criado!', 'success')
            return redirect(url_for('main.list_statuses', status_type=status_type))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar status: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar status: {e}", exc_info=True)
    return render_template('create_edit_status.html', title=f'Novo Status de {status_type.capitalize()}', form=form, legend=f'Criar Status de {status_type.capitalize()}')

@main.route("/status/<string:status_type>/<int:status_id>/update", methods=['GET', 'POST']) 
@login_required
@admin_required 
def update_status(status_type, status_id): 
    if status_type == 'event':
        status = EventStatus.query.get_or_404(status_id)
    elif status_type == 'task':
        status = TaskStatus.query.get_or_404(status_id)
    else:
        abort(404)

    form = StatusForm(obj=status) 
    if form.validate_on_submit():
        try:
            old_data = {'id': status.id, 'name': status.name, 'description': status.description}

            status.name = form.name.data
            status.description = form.description.data
            db.session.commit()

            new_data = {'id': status.id, 'name': status.name, 'description': status.description}

            if status_type == 'event':
                ChangeLogEntry.log_update(
                    user_id=current_user.id, record_type='EventStatus', record_id=status.id,
                    old_data=old_data, new_data=new_data,
                    description=f'Status de Evento "{status.name}" atualizado.'
                )
            elif status_type == 'task':
                ChangeLogEntry.log_update(
                    user_id=current_user.id, record_type='TaskStatus', record_id=status.id,
                    old_data=old_data, new_data=new_data,
                    description=f'Status de Tarefa "{status.name}" atualizado.'
                )
            db.session.commit()

            flash(f'Status "{status.name}" atualizado!', 'success')
            return redirect(url_for('main.list_statuses', status_type=status_type))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar status: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar status: {e}", exc_info=True)
    return render_template('create_edit_status.html', title=f'Atualizar Status de {status_type.capitalize()}', form=form, legend=f'Atualizar Status de {status_type.capitalize()}')

@main.route("/status/<string:status_type>/<int:status_id>/delete", methods=['POST']) 
@login_required
@admin_required 
def delete_status(status_type, status_id):
    if status_type == 'event':
        status = EventStatus.query.get_or_404(status_id)
        if status.events.count() > 0: 
            flash('Não é possível excluir este status pois há eventos associados a ele.', 'danger')
            return redirect(url_for('main.list_statuses', status_type=status_type))
    elif status_type == 'task':
        status = TaskStatus.query.get_or_404(status_id)
        if status.tasks.count() > 0: 
            flash('Não é possível excluir este status pois há tarefas associadas a ele.', 'danger')
            return redirect(url_for('main.list_statuses', status_type=status_type))
    else:
        abort(404)

    try:
        old_data = {'id': status.id, 'name': status.name, 'description': status.description}

        db.session.delete(status)

        if status_type == 'event':
            ChangeLogEntry.log_deletion(
                user_id=current_user.id, record_type='EventStatus', record_id=status_id,
                old_data=old_data,
                description=f'Status de Evento "{old_data.get("name", "Nome Desconhecido")}" excluído.'
            )
        elif status_type == 'task':
            ChangeLogEntry.log_deletion(
                user_id=current_user.id, record_type='TaskStatus', record_id=status_id,
                old_data=old_data,
                description=f'Status de Tarefa "{old_data.get("name", "Nome Desconhecido")}" excluído.'
            )
        db.session.commit() 

        flash(f'Status "{status.name}" excluído!', 'success')
        return redirect(url_for('main.list_statuses', status_type=status_type))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir status: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao excluir status: {e}", exc_info=True)
        return redirect(url_for('main.list_statuses', status_type=status_type))

@main.route("/categories")
@login_required
@admin_required 
def categories(): 
    categories = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=categories, title='Categorias') 

@main.route("/category/new", methods=['GET', 'POST'])
@login_required
@admin_required 
def new_category(): 
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            category = Category(name=form.name.data, description=form.description.data)
            db.session.add(category)
            db.session.commit()

            ChangeLogEntry.log_creation(
                user_id=current_user.id, record_type='Category', record_id=category.id,
                new_data={'id': category.id, 'name': category.name, 'description': category.description},
                description=f'Categoria "{category.name}" criada.'
            )
            db.session.commit()

            flash(f'Categoria "{category.name}" criada!', 'success')
            return redirect(url_for('main.categories')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar categoria: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar categoria: {e}", exc_info=True)
    return render_template('create_edit_category.html', title='Nova Categoria', form=form, legend='Criar Categoria')

@main.route("/category/<int:category_id>/update", methods=['GET', 'POST']) 
@login_required
@admin_required 
def update_category(category_id): 
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category) 
    if form.validate_on_submit():
        try:
            old_data = {'id': category.id, 'name': category.name, 'description': category.description}

            category.name = form.name.data
            category.description = form.description.data
            db.session.commit()

            new_data = {'id': category.id, 'name': category.name, 'description': category.description}

            ChangeLogEntry.log_update(
                user_id=current_user.id, record_type='Category', record_id=category.id,
                old_data=old_data, new_data=new_data,
                description=f'Categoria "{category.name}" atualizada.'
            )
            db.session.commit()

            flash(f'Categoria "{category.name}" atualizada!', 'success')
            return redirect(url_for('main.categories')) 
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar categoria: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar categoria: {e}", exc_info=True)
    return render_template('create_edit_category.html', title='Atualizar Categoria', form=form, legend='Atualizar Categoria')

@main.route("/category/<int:category_id>/delete", methods=['POST']) 
@login_required
@admin_required 
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    # A verificação 'category.tasks.count() > 0' aqui provavelmente não é mais relevante
    # porque `Task` agora se vincula a `TaskCategory`, não `Category`.
    # No entanto, a mantemos, pois ela continuará a verificar associações com eventos.
    if category.events.count() > 0 or category.tasks.count() > 0: # `category.tasks.count()` será 0 aqui
        flash('Não é possível excluir esta categoria, pois ela está associada a eventos ou tarefas.', 'danger')
        return redirect(url_for('main.categories')) 
    
    try:
        old_data = {'id': category.id, 'name': category.name, 'description': category.description}

        db.session.delete(category)

        ChangeLogEntry.log_deletion(
            user_id=current_user.id, record_type='Category', record_id=category_id,
            old_data=old_data,
            description=f'Categoria "{old_data.get("name", "Nome Desconhecido")}" excluída.'
        )
        db.session.commit() 

        flash(f'Categoria "{category.name}" excluída!', 'success')
        return redirect(url_for('main.categories')) 
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir categoria: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao excluir categoria: {e}", exc_info=True)
        return redirect(url_for('main.categories'))

# NEW: TaskCategory Management Routes
# =========================================================================
@main.route("/task_categories")
@login_required
@admin_required
def list_task_categories():
    task_categories = TaskCategory.query.order_by(TaskCategory.name).all()
    return render_template('task_categories.html', task_categories=task_categories, title='Categorias de Tarefa')

@main.route("/task_category/new", methods=['GET', 'POST'])
@login_required
@admin_required
def new_task_category():
    form = TaskCategoryForm()
    if form.validate_on_submit():
        try:
            task_category = TaskCategory(name=form.name.data, description=form.description.data)
            db.session.add(task_category)
            db.session.commit()

            ChangeLogEntry.log_creation(
                user_id=current_user.id, record_type='TaskCategory', record_id=task_category.id,
                new_data={'id': task_category.id, 'name': task_category.name, 'description': task_category.description},
                description=f'Categoria de Tarefa "{task_category.name}" criada.'
            )
            db.session.commit()

            flash(f'Categoria de Tarefa "{task_category.name}" criada!', 'success')
            return redirect(url_for('main.list_task_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar categoria de tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao criar categoria de tarefa: {e}", exc_info=True)
    return render_template('create_edit_task_category.html', title='Nova Categoria de Tarefa', form=form, legend='Criar Categoria de Tarefa')

@main.route("/task_category/<int:task_category_id>/update", methods=['GET', 'POST'])
@login_required
@admin_required
def update_task_category(task_category_id):
    task_category = TaskCategory.query.get_or_404(task_category_id)
    form = TaskCategoryForm(obj=task_category, original_name=task_category.name) # Pass original_name for validation
    if form.validate_on_submit():
        try:
            old_data = {'id': task_category.id, 'name': task_category.name, 'description': task_category.description}

            task_category.name = form.name.data
            task_category.description = form.description.data
            db.session.commit()

            new_data = {'id': task_category.id, 'name': task_category.name, 'description': task_category.description}

            ChangeLogEntry.log_update(
                user_id=current_user.id, record_type='TaskCategory', record_id=task_category.id,
                old_data=old_data, new_data=new_data,
                description=f'Categoria de Tarefa "{task_category.name}" atualizada.'
            )
            db.session.commit()

            flash(f'Categoria de Tarefa "{task_category.name}" atualizada!', 'success')
            return redirect(url_for('main.list_task_categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar categoria de tarefa: {e}. Por favor, tente novamente.', 'danger')
            current_app.logger.error(f"Erro ao atualizar categoria de tarefa: {e}", exc_info=True)
    return render_template('create_edit_task_category.html', title='Atualizar Categoria de Tarefa', form=form, legend='Atualizar Categoria de Tarefa')

@main.route("/task_category/<int:task_category_id>/delete", methods=['POST'])
@login_required
@admin_required
def delete_task_category(task_category_id):
    task_category = TaskCategory.query.get_or_404(task_category_id)
    if task_category.tasks.count() > 0: # Verifica se há tarefas associadas a esta categoria de tarefa
        flash('Não é possível excluir esta categoria de tarefa, pois ela está associada a tarefas.', 'danger')
        return redirect(url_for('main.list_task_categories'))

    try:
        old_data = {'id': task_category.id, 'name': task_category.name, 'description': task_category.description}

        db.session.delete(task_category)

        ChangeLogEntry.log_deletion(
            user_id=current_user.id, record_type='TaskCategory', record_id=task_category_id,
            old_data=old_data,
            description=f'Categoria de Tarefa "{old_data.get("name", "Nome Desconhecido")}" excluída.'
        )
        db.session.commit()

        flash(f'Categoria de Tarefa "{task_category.name}" excluída!', 'success')
        return redirect(url_for('main.list_task_categories'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir categoria de tarefa: {e}. Por favor, tente novamente.', 'danger')
        current_app.logger.error(f"Erro ao excluir categoria de tarefa: {e}", exc_info=True)
        return redirect(url_for('main.list_task_categories'))
# =========================================================================
# FIM NEW: TaskCategory Management Routes
# =========================================================================

# Rota para visualizar o ChangeLog
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

# Rotas de Gerenciamento de Usuários (Novas)
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
            user = User(username=form.username.data, email=form.email.data, role=form.role.data)
            user.set_password(form.password.data) 

            db.session.add(user)
            db.session.commit()
            print(f"--- DEBUG: new_user - Usuário '{user.username}' criado com sucesso! ---") 

            ChangeLogEntry.log_creation(
                user_id=current_user.id,
                record_type='User',
                record_id=user.id,
                new_data=user.to_dict(),
                description=f'Usuário "{user.username}" (ID: {user.id}) criado.'
            )
            db.session.commit() 

            flash(f'Usuário "{user.username}" criado com sucesso!', 'success')
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
    form = UserForm(obj=user, original_username=user.username, original_email=user.email, is_new_user=False) 

    if form.validate_on_submit():
        print("--- DEBUG: update_user - Formulário validado com sucesso! ---") 
        try:
            old_data = user.to_dict() 

            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data

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
                description=f'Usuário "{user.username}" (ID: {user.id}) editado. Nova role: {user.role}.'
            )
            db.session.commit()

            flash(f'Usuário "{user.username}" atualizado com sucesso!', 'success')
            return redirect(url_for('main.list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar usuário: {e}. Por favor, tente novamente.', 'danger')
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

    try:
        old_data = user.to_dict()
        
        db.session.delete(user)

        ChangeLogEntry.log_deletion(
            user_id=current_user.id,
            record_type='User',
            record_id=user_id,
            old_data=old_data,
            description=f'Usuário "{old_data.get("username", "Nome Desconhecido")}" (ID: {user_id}) deletado.'
        )
        db.session.commit() 

        flash(f'Usuário "{user.username}" deletado com sucesso!', 'success')
        return redirect(url_for('main.list_users'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar usuário: {e}. Por favor, tente novamente.', 'danger')
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
    task = Task.query.get_or_404(task_id)

    is_assigned = current_user in task.assignees
    
    if not current_user.is_admin and task.event.author != current_user and not is_assigned:
        return jsonify({'message': 'Você não tem permissão para adicionar áudio a esta tarefa.'}), 403

    if 'audio_file' not in request.files:
        return jsonify({'message': 'Nenhum arquivo de áudio fornecido.'}), 400

    audio_file = request.files['audio_file']
    audio_duration = request.form.get('duration_seconds', type=int)

    if audio_file.filename == '':
        return jsonify({'message': 'Nenhum arquivo selecionado.'}), 400

    if audio_file and audio_duration is not None:
        unique_filename = f"{uuid.uuid4()}.{secure_filename(audio_file.filename).rsplit('.', 1)[1].lower()}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], unique_filename)

        try:
            old_task_data_for_history = {
                'audio_path': task.audio_path,
                'audio_duration_seconds': task.audio_duration_seconds
            }
            # Remove o áudio antigo se existir
            if task.audio_path and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task.audio_path)):
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task.audio_path))

            audio_file.save(upload_path)

            old_data_for_changelog = task.to_dict()

            task.audio_path = unique_filename
            task.audio_duration_seconds = audio_duration
            db.session.commit()

            new_data_for_changelog = task.to_dict()

            # >>> NOVO CÓDIGO AQUI para registrar upload/update de áudio no TaskHistory
            history_entry = TaskHistory(
                task_id=task.id,
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
            db.session.commit() # Comita a entrada do histórico
            # <<< FIM NOVO CÓDIGO

            ChangeLogEntry.log_update(
                user_id=current_user.id,
                record_type='Task',
                record_id=task.id,
                old_data=old_data_for_changelog,
                new_data=new_data_for_changelog,
                description=f'Áudio adicionado/atualizado na tarefa "{task.title}". Duração: {audio_duration}s.'
            )
            db.session.commit()

            return jsonify({
                'message': 'Áudio salvo com sucesso!',
                'audio_filename': unique_filename,
                'audio_url_base': url_for('main.static_audio_files', filename=unique_filename)
            }), 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar áudio da tarefa {task_id}: {e}", exc_info=True)
            return jsonify({'message': f'Erro ao salvar áudio: {str(e)}'}), 500
    
    return jsonify({'message': 'Requisição inválida.'}), 400

@main.route("/api/task/<int:task_id>/delete_audio", methods=['DELETE'])
@login_required
def delete_task_audio(task_id):
    task = Task.query.get_or_404(task_id)

    is_assigned = current_user in task.assignees
    if not current_user.is_admin and task.event.author != current_user and not is_assigned:
        return jsonify({'message': 'Você não tem permissão para remover áudio desta tarefa.'}), 403

    if not task.audio_path:
        return jsonify({'message': 'Nenhum áudio para remover nesta tarefa.'}), 404

    audio_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_AUDIO'], task.audio_path)

    try:
        old_task_data_for_history = {
            'audio_path': task.audio_path,
            'audio_duration_seconds': task.audio_duration_seconds
        }

        if os.path.exists(audio_filepath):
            os.remove(audio_filepath)

        old_data_for_changelog = task.to_dict()

        task.audio_path = None
        task.audio_duration_seconds = None
        
        # >>> NOVO CÓDIGO AQUI para registrar remoção de áudio no TaskHistory
        history_entry = TaskHistory(
            task_id=task.id,
            action_type='audio_removed',
            description='Áudio da tarefa removido',
            old_value=json.dumps(old_task_data_for_history),
            new_value=json.dumps({'audio_path': None, 'audio_duration_seconds': None}),
            user_id=current_user.id,
            comment=f"Áudio removido da tarefa."
        )
        db.session.add(history_entry)
        # <<< FIM NOVO CÓDIGO
        
        db.session.commit() # Comita todas as alterações, incluindo a remoção e a entrada no TaskHistory

        new_data_for_changelog = task.to_dict()

        ChangeLogEntry.log_update(
            user_id=current_user.id,
            record_type='Task',
            record_id=task.id,
            old_data=old_data_for_changelog,
            new_data=new_data_for_changelog,
            description=f'Áudio removido da tarefa "{task.title}".'
        )
        db.session.commit()

        return jsonify({'message': 'Áudio removido com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover áudio da tarefa {task_id}: {e}", exc_info=True)
        return jsonify({'message': f'Erro ao remover áudio: {str(e)}'}), 500

@main.route('/audio_uploads/<path:filename>')
def static_audio_files(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER_AUDIO'], filename)

# --- FIM NOVAS ROTAS DE API PARA GERENCIAMENTO DE ÁUDIO EM TAREFAS ---

# --- NOVAS ROTAS PARA REDEFINIÇÃO DE SENHA ---

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
            flash('Não foi possível enviar o e-mail de redefinição de senha para este endereço. Verifique o e-mail e tente novamente.', 'warning')
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

            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(form.password.data)
            db.session.commit()

            ChangeLogEntry.log_update(
                user_id=user.id,
                record_type='User',
                record_id=user.id,
                old_data={},
                new_data={},
                description=f'Senha do usuário "{user.username}" redefinida com sucesso.'
            )
            db.session.commit()

            flash('Sua senha foi redefinida com sucesso! Você já pode fazer login.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao redefinir senha do usuário {user.id}: {e}", exc_info=True)
            flash('Ocorreu um erro ao redefinir sua senha. Por favor, tente novamente.', 'danger')
            return redirect(url_for('main.reset_request'))
            
    return render_template('reset_token.html', title='Redefinir Senha', form=form)

# Páginas de Erro (manter estas no final do arquivo)
@main.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@main.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_server_error(error):
    return render_template('errors/500.html'), 500