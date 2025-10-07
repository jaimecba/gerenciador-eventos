# C:\gerenciador-eventos\models.py

from extensions import db, login_manager
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for # ADICIONADO: url_for para Attachment.to_dict()
import uuid
from flask_login import UserMixin
from sqlalchemy.orm import joinedload # <--- ADICIONADO: Import para otimização de carregamento de relacionamentos
from sqlalchemy import CheckConstraint, Index # Importar para usar em __table_args__

# --- ADICIONADO PARA DEPURAR A VERSÃO DO ITSDANGEROUS ---
print(f"DEBUG: Itsdangerous version being used: {itsdangerous.__version__}")
# --- FIM DA DEPURACAO ---

# Carrega um usuário dado seu ID para o Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """
    Função obrigatória para o Flask-Login carregar um usuário
    dado seu ID, carregando o objeto Role junto para otimização.
    """
    user = User.query.options(joinedload(User.role_obj)).get(int(user_id))
    # --- DEPURACAO ADICIONADA ---
    if user:
        print(f"DEBUG_LOAD_USER: Usuário ID {user_id} carregado. Username: {user.username}, Role ID: {user.role_id}, Role Name (via role_obj): {user.role_obj.name if user.role_obj else 'N/A'}")
    else:
        print(f"DEBUG_LOAD_USER: Usuário ID {user_id} NÃO encontrado.")
    # --- FIM DA DEPURACAO ---
    return user

# NOVO MODELO: Role (para gerenciar papéis de usuário)
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # Ex: 'Admin', 'Project Manager', 'User'
    description = db.Column(db.String(200), nullable=True)

    # --- NOVAS COLUNAS: Capacidades de permissão de evento (existentes) ---
    can_view_event = db.Column(db.Boolean, default=False, nullable=False)
    can_edit_event = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_permissions = db.Column(db.Boolean, default=False, nullable=False)
    can_create_event = db.Column(db.Boolean, default=False, nullable=False) # Permissão para criar eventos

    # --- NOVAS COLUNAS: Capacidades de permissão de EVENTO (sugeridas) ---
    can_publish_event = db.Column(db.Boolean, default=False, nullable=False) # NOVO
    can_cancel_event = db.Column(db.Boolean, default=False, nullable=False)  # NOVO
    can_duplicate_event = db.Column(db.Boolean, default=False, nullable=False) # NOVO
    can_view_event_registrations = db.Column(db.Boolean, default=False, nullable=False) # NOVO
    can_view_event_reports = db.Column(db.Boolean, default=False, nullable=False) # NOVO

    # --- NOVAS COLUNAS: Capacidades de permissão de TAREFA granular (ADICIONADAS AQUI) ---
    can_create_task = db.Column(db.Boolean, default=False, nullable=False)
    can_edit_task = db.Column(db.Boolean, default=False, nullable=False)
    can_delete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_complete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_uncomplete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_upload_task_audio = db.Column(db.Boolean, default=False, nullable=False)
    can_delete_task_audio = db.Column(db.Boolean, default=False, nullable=False)
    can_view_task_history = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_task_comments = db.Column(db.Boolean, default=False, nullable=False) # Permissão para adicionar/gerenciar comentários em tarefas

    # --- Permissões para anexos em tarefas ---
    can_upload_attachments = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_attachments = db.Column(db.Boolean, default=False, nullable=False) # Inclui deletar
    # --- FIM NOVAS COLUNAS ---

    # Relacionamento back-populates para os usuários que possuem este papel
    users = db.relationship('User', back_populates='role_obj', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'can_view_event': self.can_view_event,
            'can_edit_event': self.can_edit_event,
            'can_manage_permissions': self.can_manage_permissions,
            'can_create_event': self.can_create_event,
            # NOVOS: Incluir as novas permissões de evento
            'can_publish_event': self.can_publish_event,
            'can_cancel_event': self.can_cancel_event,
            'can_duplicate_event': self.can_duplicate_event,
            'can_view_event_registrations': self.can_view_event_registrations,
            'can_view_event_reports': self.can_view_event_reports,
            # Incluir as novas permissões de tarefa no dicionário
            'can_create_task': self.can_create_task,
            'can_edit_task': self.can_edit_task,
            'can_delete_task': self.can_delete_task,
            'can_complete_task': self.can_complete_task,
            'can_uncomplete_task': self.can_uncomplete_task,
            'can_upload_task_audio': self.can_upload_task_audio,
            'can_delete_task_audio': self.can_delete_task_audio,
            'can_view_task_history': self.can_view_task_history,
            'can_manage_task_comments': self.can_manage_task_comments,
            # Incluir novas permissões de anexo
            'can_upload_attachments': self.can_upload_attachments,
            'can_manage_attachments': self.can_manage_attachments
        }

    def __repr__(self):
        return f"Role('{self.name}')"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200)) # Armazena o hash da senha

    role_id = db.Column(db.Integer, db.ForeignKey('role.id', name='fk_user_role_id'), nullable=False)

    role_obj = db.relationship('Role', back_populates='users', lazy=True)

    image_file = db.Column(db.String(20), nullable=False, default='default.jpg') # Adicionado: Arquivo de imagem do perfil

    is_active_db = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    events_created = db.relationship('Event', backref='author', lazy=True, foreign_keys='Event.author_id')
    changelog_entries = db.relationship('ChangeLogEntry', backref='user', lazy=True)

    assigned_tasks = db.relationship('TaskAssignment', back_populates='user', lazy=True, cascade='all, delete-orphan')

    user_groups = db.relationship('UserGroup', back_populates='user', lazy=True, cascade='all, delete-orphan')
    event_permissions = db.relationship('EventPermission', back_populates='user', lazy=True, cascade='all, delete-orphan')

    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan')

    completed_tasks = db.relationship('Task', backref='completed_by_user', lazy=True, foreign_keys='Task.completed_by_id')

    task_history_records = db.relationship('TaskHistory', back_populates='author', lazy=True)
    comments = db.relationship('Comment', back_populates='author', lazy=True, cascade='all, delete-orphan') # Relacionamento para comentários feitos pelo usuário
    uploaded_attachments = db.relationship('Attachment', back_populates='uploader', lazy=True) # Relacionamento para anexos feitos pelo usuário
    # --- NOVO: Relacionamento para as inscrições de notificações push ---
    push_subscriptions = db.relationship('PushSubscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    # --- FIM NOVO ---

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_db

    @property
    def role(self):
        role_name = self.role_obj.name if self.role_obj else 'unknown'
        return role_name

    @property
    def is_admin(self):
        is_admin_status = (self.role_obj and self.role_obj.name == 'Admin')
        return is_admin_status

    # --- Permissões de Evento ---
    @property
    def can_view_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_view_event or False
        return result

    @property
    def can_edit_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_edit_event or False
        return result

    @property
    def can_manage_permissions(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_manage_permissions or False
        return result

    @property
    def can_create_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_create_event or False
        return result

    # --- NOVAS PROPRIEDADES DE PERMISSÃO DE EVENTO ---
    @property
    def can_publish_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_publish_event or False
        return result

    @property
    def can_cancel_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_cancel_event or False
        return result

    @property
    def can_duplicate_event(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_duplicate_event or False
        return result

    @property
    def can_view_event_registrations(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_view_event_registrations or False
        return result

    @property
    def can_view_event_reports(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_view_event_reports or False
        return result
    # --- FIM NOVAS PROPRIEDADES DE PERMISSÃO DE EVENTO ---


    # --- Permissões de Tarefa ---
    @property
    def can_create_task(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_create_task or False
        return result

    @property
    def can_edit_task(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_edit_task or False
        return result

    @property
    def can_delete_task(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_delete_task or False
        return result

    @property
    def can_complete_task(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_complete_task or False
        return result

    @property
    def can_uncomplete_task(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_uncomplete_task or False
        return result

    @property
    def can_upload_task_audio(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_upload_task_audio or False
        return result

    @property
    def can_delete_task_audio(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_delete_task_audio or False
        return result

    @property
    def can_view_task_history(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_view_task_history or False
        return result

    @property
    def can_manage_task_comments(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_manage_task_comments or False
        return result

    # --- Propriedades para permissões de anexo ---
    @property
    def can_upload_attachments(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_upload_attachments or False
        return result

    @property
    def can_manage_attachments(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_manage_attachments or False
        return result
    # --- FIM DA ADIÇÃO DE PROPRIEDADES ---

    # --- NOVO MÉTODO: Verifica se o usuário tem permissão mínima para um evento para fins de atribuição de tarefa ---
    # Manter este método como está por enquanto, pois ele verifica permissão geral de edição de evento.
    # As verificações granulares de tarefa serão feitas diretamente nas rotas, acessando as novas permissões da role.
    def has_event_permission_for_task(self, event_id):
        # 1. Obter o evento. Usar db.session.get para carregar do cache se disponível.
        event = db.session.get(Event, event_id) # Usar get, pois query.get_or_404 não é adequado aqui
        if not event:
            return False # Evento não existe ou foi excluído

        # 2. Verificar se o usuário é o autor do evento ou um administrador
        if event.author_id == self.id or self.is_admin:
            return True # Autor e Admin sempre tem permissão total

        # 3. Buscar permissões específicas do usuário para este evento
        user_event_permission = EventPermission.query.options(joinedload(EventPermission.user)).filter(
            EventPermission.user_id == self.id,
            EventPermission.event_id == event_id
        ).first()

        # Aqui, como EventPermission é user-only, a existência da permissão já é suficiente.
        # Não precisamos mais verificar uma role dentro de EventPermission
        if user_event_permission:
            return True

        # 5. Permissões de grupo não são mais consideradas para EventPermission.has_event_permission_for_task.
        # Este método foi simplificado para refletir a nova estrutura.

        return False # Nenhuma permissão suficiente encontrada
    # --- FIM NOVO MÉTODO ---


    def to_dict(self):
        # CORREÇÃO AQUI: Incluir todas as permissões no to_dict do User
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active_db,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_admin': self.is_admin,
            'can_view_event': self.can_view_event,
            'can_edit_event': self.can_edit_event,
            'can_manage_permissions': self.can_manage_permissions,
            'can_create_event': self.can_create_event,
            # NOVOS: Incluir as novas permissões de evento no to_dict
            'can_publish_event': self.can_publish_event,
            'can_cancel_event': self.can_cancel_event,
            'can_duplicate_event': self.can_duplicate_event,
            'can_view_event_registrations': self.can_view_event_registrations,
            'can_view_event_reports': self.can_view_event_reports,
            'can_create_task': self.can_create_task,
            'can_edit_task': self.can_edit_task,
            'can_delete_task': self.can_delete_task,
            'can_complete_task': self.can_complete_task,
            'can_uncomplete_task': self.can_uncomplete_task,
            'can_upload_task_audio': self.can_upload_task_audio,
            'can_delete_task_audio': self.can_delete_task_audio,
            'can_view_task_history': self.can_view_task_history,
            'can_manage_task_comments': self.can_manage_task_comments,
            # Incluir permissões de anexo no to_dict
            'can_upload_attachments': self.can_upload_attachments,
            'can_manage_attachments': self.can_manage_attachments
        }

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Role: '{self.role}')"

    # --- NOVOS MÉTODOS ADICIONADOS PARA COMPARAÇÃO CORRETA DE OBJETOS USER ---
    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
    # --- FIM DOS NOVOS MÉTODOS ---

# NOVO MODELO: PasswordResetToken para gerenciar tokens de redefinição de senha
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token' # Nome da tabela no banco de dados

    id = db.Column(db.Integer, primary_key=True)
    token_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_password_reset_token_user_id'), nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def is_expired(self):
        return datetime.utcnow() > self.expiration_date


# =========================================================================
# NOVO MODELO CONSOLIDADO: Status (substitui EventStatus e TaskStatus)
# =========================================================================
class Status(db.Model):
    __tablename__ = 'status'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False) # Não é único globalmente
    type = db.Column(db.String(20), nullable=False) # 'event' ou 'task'
    description = db.Column(db.String(255), nullable=True)

    # Garante que a combinação de nome e tipo seja única
    __table_args__ = (db.UniqueConstraint('name', 'type', name='_name_type_uc'),)

    event_associations = db.relationship('Event', foreign_keys='Event.status_id', backref='status_obj', lazy=True, viewonly=True)
    task_associations = db.relationship('Task', foreign_keys='Task.task_status_id', backref='task_status_obj', lazy=True, viewonly=True)


    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description
        }

    def __repr__(self):
        return f"<Status {self.name} ({self.type})>"
# =========================================================================
# FIM DO NOVO MODELO: Status
# =========================================================================


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_author_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', name='fk_event_category_id'), nullable=True)

    status_id = db.Column(db.Integer, db.ForeignKey('status.id', name='fk_event_status_id'), nullable=True)

    # --- NOVOS CAMPOS PARA O MODELO EVENT ---
    is_published = db.Column(db.Boolean, default=False, nullable=False) # NOVO: Para controle de publicação
    is_cancelled = db.Column(db.Boolean, default=False, nullable=False) # NOVO: Para marcar eventos como cancelados
    # --- FIM NOVOS CAMPOS ---

    # Relacionamentos
    category = db.relationship('Category', backref='events', lazy=True)
    status = db.relationship('Status', foreign_keys=[status_id], backref='events', lazy=True)

    tasks = db.relationship('Task', backref='event', lazy='selectin', cascade="all, delete-orphan")
    event_permissions = db.relationship('EventPermission', back_populates='event', lazy=True, cascade='all, delete-orphan')
# ATUALIZAR __init__ para incluir os novos campos, se você estiver usando um __init__ explícito
    # Se você não tiver um __init__ explícito e confiar no SQLAlchemy, pode ignorar este bloco.
    def __init__(self, title, description, due_date, author_id, category_id, status_id, end_date=None, location=None, is_published=False, is_cancelled=False):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.author_id = author_id
        self.category_id = category_id
        self.status_id = status_id
        self.end_date = end_date
        self.location = location
        self.is_published = is_published # INCLUÍDO NO __init__
        self.is_cancelled = is_cancelled # INCLUÍDO NO __init__
        self.created_at = datetime.utcnow() # Garante que created_at seja definido na criação

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'author_id': self.author_id,
            'category_id': self.category_id,
            'status_id': self.status_id,
            'status_name': self.status.name if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_published': self.is_published, # INCLUÍDO NO to_dict
            'is_cancelled': self.is_cancelled  # INCLUÍDO NO to_dict
        }

    def __repr__(self):
        return f"Event('{self.title}', Due: '{self.due_date}', End: '{self.end_date}', Loc: '{self.location}', Published: {self.is_published}, Cancelled: {self.is_cancelled})"
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"Category('{self.name}')"

class TaskCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = db.relationship('Task', back_populates='task_category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"TaskCategory('{self.name}')"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    original_due_date = db.Column(db.DateTime, nullable=True)

    cloud_storage_link = db.Column(db.String(500), nullable=True)
    link_notes = db.Column(db.Text, nullable=True)
    audio_path = db.Column(db.String(500), nullable=True)
    audio_duration_seconds = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_task_event_id'), nullable=False)
    task_status_id = db.Column(db.Integer, db.ForeignKey('status.id', name='fk_task_status_id'), nullable=False)
    task_category_id = db.Column(db.Integer, db.ForeignKey('task_category.id', name='fk_task_task_category_id'), nullable=True)

    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_completed_by_id'), nullable=True)

    # Relacionamentos
    task_status = db.relationship('Status', foreign_keys=[task_status_id], backref='tasks', lazy=True)
    task_category = db.relationship('TaskCategory', back_populates='tasks', lazy=True)

    # Esta é a relação principal para atribuições de tarefas (Task -> TaskAssignment)
    assignees_associations = db.relationship(
        'TaskAssignment',
        back_populates='task',
        lazy=True,
        cascade='all, delete-orphan'
    )

    completed_by = db.relationship('User', foreign_keys=[completed_by_id], overlaps="completed_by_user,completed_tasks")
    history = db.relationship('TaskHistory', backref='task', lazy='dynamic', cascade='all, delete-orphan')

    comments = db.relationship('Comment', back_populates='task', lazy=True, cascade='all, delete-orphan', order_by="Comment.timestamp.asc()") # Relacionamento para comentários da tarefa
    attachments = db.relationship('Attachment', back_populates='task', lazy=True, cascade='all, delete-orphan', order_by="Attachment.upload_timestamp.asc()") # Relacionamento para anexos da tarefa

    @property
    def assignees(self):
        return [assignment.user for assignment in self.assignees_associations]

    def to_dict(self):
        assigned_user_ids = [assign.user_id for assign in self.assignees_associations]
        assigned_usernames = [assign.user.username for assign in self.assignees_associations if assign.user]

        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'notes': self.notes,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'original_due_date': self.original_due_date.isoformat() if self.original_due_date else None,
            'cloud_storage_link': self.cloud_storage_link,
            'link_notes': self.link_notes,
            'audio_path': self.audio_path,
            'audio_duration_seconds': self.audio_duration_seconds,
            'event_id': self.event_id,
            'task_status_id': self.task_status_id,
            'task_status_name': self.task_status.name if self.task_status else None,

            'task_category_id': self.task_category_id,
            'task_category_name': self.task_category.name if self.task_category else None,

            'assigned_user_ids': assigned_user_ids,
            'assigned_usernames': assigned_usernames,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by_id': self.completed_by_id,
            'completed_by_username': self.completed_by_user.username if self.completed_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'attachments_count': len(self.attachments)
        }

    def __repr__(self):
        category_name = self.task_category.name if self.task_category else 'N/A'
        return f"Task('{self.title}', '{self.due_date}', Category: '{category_name}')"

class TaskAssignment(db.Model):
    __tablename__ = 'task_assignment'
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_task_assignment_task_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_assignment_user_id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship(
        'Task',
        back_populates='assignees_associations'
    )
    user = db.relationship('User', back_populates='assigned_tasks')

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'assigned_at': self.assigned_at.isoformat()
        }

    def __repr__(self):
        return f"TaskAssignment(Task ID: {self.task_id}, User ID: {self.user_id})"

class TaskHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_task_history_task_id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)

    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_history_user_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    comment = db.Column(db.Text, nullable=True)

    author = db.relationship('User', back_populates='task_history_records', foreign_keys=[user_id])

    def __repr__(self):
        return f'<TaskHistory {self.action_type} for Task {self.task_id} by User {self.user_id}>'

    def set_old_value(self, data):
        self.old_value = json.dumps(data)

    def get_old_value(self):
        return json.loads(self.old_value) if self.old_value else None

    def set_new_value(self, data):
        self.new_value = json.dumps(data)

    def get_new_value(self):
        return json.loads(self.new_value) if self.new_value else None

class ChangeLogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_changelog_user_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    old_data = db.Column(db.JSON, nullable=True)
    new_data = db.Column(db.JSON, nullable=True)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'Desconhecido',
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'old_data': self.old_data,
            'new_data': self.new_data,
            'description': self.description
        }

    @classmethod
    def log_creation(cls, user_id, record_type, record_id, new_data, description, action='create'):
        entry = cls(
            user_id=user_id,
            action=action,
            record_type=record_type,
            record_id=record_id,
            new_data=new_data,
            description=description
        )
        db.session.add(entry)

    @classmethod
    def log_update(cls, user_id, record_type, record_id, old_data, new_data, description, action='update'):
        entry = cls(
            user_id=user_id,
            action=action,
            record_type=record_type,
            record_id=record_id,
            old_data=old_data,
            new_data=new_data,
            description=description
        )
        db.session.add(entry)

    @classmethod
    def log_deletion(cls, user_id, record_type, record_id, old_data, description, action='delete'):
        entry = cls(
            user_id=user_id,
            action=action,
            record_type=record_type,
            record_id=record_id,
            old_data=old_data,
            description=description
        )
        db.session.add(entry)

    def __repr__(self):
        return f"ChangeLogEntry('{self.action}', '{self.record_type}', '{self.timestamp}')"

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users_in_group = db.relationship('UserGroup', back_populates='group', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"Group('{self.name}')"

class UserGroup(db.Model):
    __tablename__ = 'user_group'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_user_group_user_id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', name='fk_user_group_group_id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='user_groups')
    group = db.relationship('Group', back_populates='users_in_group')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'group_id': self.group_id,
            'assigned_at': self.assigned_at.isoformat()
        }

    def __repr__(self):
        return f"UserGroup(User ID: {self.user_id}, Group ID: {self.group_id})"


class EventPermission(db.Model):
    __tablename__ = 'event_permission'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_event_permission_event_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_permission_user_id', ondelete='CASCADE'), nullable=False) # AGORA nullable=False

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = db.relationship('Event', back_populates='event_permissions')
    user = db.relationship('User', back_populates='event_permissions')

    __table_args__ = (
        # A nova UniqueConstraint garante que um usuário só pode ter uma permissão por evento
        db.UniqueConstraint('event_id', 'user_id', name='_event_user_unique_uc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else 'N/A', # Adicionado para melhor visualização
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"EventPermission(Event ID: {self.event_id}, User ID: {self.user.id if self.user else 'N/A'}, User: {self.user.username if self.user else 'N/A'})"


# =========================================================================
# NOVO MODELO: Comment (para comentários em tarefas)
# =========================================================================
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_comment_task_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_comment_user_id'), nullable=False)


    task = db.relationship('Task', back_populates='comments')
    author = db.relationship('User', back_populates='comments') # CORRIGIDO: user -> author para combinar com User.comments

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'task_id': self.task_id,
            'user_id': self.user_id,
            'username': self.author.username if self.author else 'Desconhecido'
        }

    def __repr__(self):
        return f"Comment(ID: {self.id}, Task ID: {self.task_id}, Author: {self.author.username if self.author else 'N/A'}, Timestamp: {self.timestamp})"
# =========================================================================
# FIM NOVO MODELO: Comment
# =========================================================================

# =========================================================================
# NOVO MODELO: Attachment (para anexos em tarefas)
# =========================================================================
class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_attachment_task_id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False) # Nome original do arquivo
    unique_filename = db.Column(db.String(255), unique=True, nullable=False) # Nome do arquivo salvo no disco (ex: usando UUID)
    storage_path = db.Column(db.String(500), nullable=False) # Caminho completo ou URL do arquivo (local ou nuvem)
    mimetype = db.Column(db.String(100), nullable=True) # Tipo MIME do arquivo
    filesize = db.Column(db.Integer, nullable=True) # Tamanho em bytes
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_attachment_uploaded_by_user_id'), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False) # CORRIGIDO AQUI: nome da coluna para consistência

    # Relacionamentos
    task = db.relationship('Task', back_populates='attachments')
    uploader = db.relationship('User', back_populates='uploaded_attachments')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'filename': self.filename,
            'unique_filename': self.unique_filename,
            'storage_path': self.storage_path,
            'mimetype': self.mimetype,
            'filesize': self.filesize,
            'uploaded_by_user_id': self.uploaded_by_user_id,
            'uploaded_by_username': self.uploader.username if self.uploader else 'Desconhecido',
            'upload_timestamp': self.upload_timestamp.isoformat(),
            'download_url': url_for('main.download_attachment', attachment_id=self.id, _external=False) # ADICIONADO: URL para download
        }

    def __repr__(self):
        return f"Attachment(ID: {self.id}, Task ID: {self.task_id}, Filename: '{self.filename}')"
# =========================================================================
# FIM NOVO MODELO: Attachment
# =========================================================================

# =========================================================================
# NOVO MODELO: Notification (para notificações in-app e metadados de email)
# =========================================================================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(500), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Adicionar campos para relacionar a notificação a um objeto específico
    related_object_type = db.Column(db.String(50), nullable=True) # Ex: 'Task', 'Event', 'Comment'
    related_object_id = db.Column(db.Integer, nullable=True)

    # Relacionamento com o usuário que recebe a notificação
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))
    def __repr__(self):
        return f"Notification('{self.user.username}', '{self.message[:30]}...', Read: {self.is_read})"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'link_url': self.link_url,
            'is_read': self.is_read,
            'timestamp': self.timestamp.isoformat(),
            'related_object_type': self.related_object_type,
            'related_object_id': self.related_object_id
        }
# =========================================================================
# FIM NOVO MODELO: Notification
# =========================================================================

# =========================================================================
# NOVO MODELO: PushSubscription (PARA NOTIFICAÇÕES PUSH)
# =========================================================================
class PushSubscription(db.Model):
    __tablename__ = 'push_subscription' # Nome da tabela no banco de dados

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(512), unique=True, nullable=False) # URL única do serviço push
    p256dh = db.Column(db.String(255), nullable=False) # Chave pública para criptografia do payload
    auth = db.Column(db.String(255), nullable=False) # Chave de autenticação
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow) # Data de criação da subscription

    # O relacionamento 'user' é estabelecido pelo backref no modelo User

    def __repr__(self):
        return f'<PushSubscription {self.endpoint} for User {self.user_id}>'

    def to_dict(self):
        """
        Converte o objeto PushSubscription em um dicionário compatível
        com a biblioteca pywebpush para envio de notificações.
        """
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth
            }
        }
# =========================================================================
# FIM NOVO MODELO: PushSubscription
# =========================================================================