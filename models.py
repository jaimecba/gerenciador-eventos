# C:\gerenciador-eventos\models.py

from extensions import db, login_manager
from datetime import datetime, timedelta, date, time
from werkzeug.security import generate_password_hash, check_password_hash
import json
import itsdangerous
# from itsdangerous import URLSafeTimedSerializer # Não usado diretamente aqui, pode ser removido
from flask import current_app # current_app é usado em `itsdangerous` e outros contextos, mantém aqui por padrão
# from flask import url_for # Removido import global para evitar circular dependência; importado localmente em Attachment.to_dict
import uuid
from flask_login import UserMixin
from sqlalchemy.orm import joinedload, relationship
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, Enum, Numeric
import enum

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
    user = User.query.get(int(user_id))
    if user:
        print(f"DEBUG_LOAD_USER: Usuário ID {user_id} carregado. Username: {user.username}, Role ID: {user.role_id}, Role Name (via role_obj): {user.role_obj.name if user.role_obj else 'N/A'}")
    else:
        print(f"DEBUG_LOAD_USER: Usuário ID {user_id} NÃO encontrado.")
    return user

# --- Enum para Tipos de Campo do Checklist ---
class CustomFieldTypeEnum(enum.Enum):
    TEXT = "Texto Curto"
    TEXTAREA = "Texto Longo"
    DATE = "Data"
    TIME = "Hora"
    DATETIME = "Data e Hora"
    NUMBER = "Número"
    BOOLEAN = "Sim/Não"
    IMAGE = "Imagem/Arquivo Visual"
    FILE = "Anexo Genérico"
    URL = "Link (URL)"
    REFERENCE_BIBLICA = "Referência Bíblica"
    SELECT = "Seleção Única" # Para opções predefinidas

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
    can_approve_art = db.Column(db.Boolean, default=False, nullable=False) # NOVO: Permissão para aprovar artes

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
    
    # Relacionamento com TaskSubcategory usando back_populates
    approved_subcategories = db.relationship('TaskSubcategory', back_populates='approver_role', lazy=True)

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
            'can_approve_art': self.can_approve_art,
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
    changelog_entries = db.relationship('ChangeLogEntry', back_populates='user_associated_with_log', lazy=True, cascade='all, delete-orphan')
    assigned_tasks = db.relationship('TaskAssignment', back_populates='user', lazy=True, cascade='all, delete-orphan')
    user_groups = db.relationship('UserGroup', back_populates='user', lazy=True, cascade='all, delete-orphan')
    event_permissions = db.relationship('EventPermission', back_populates='user', lazy=True, cascade='all, delete-orphan')
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan')

    tasks_completed_by_me = db.relationship('Task', foreign_keys='Task.completed_by_id', back_populates='completed_by_user_obj')
    tasks_created_by_me = db.relationship('Task', foreign_keys='Task.creator_id', back_populates='creator_user_obj')

    task_history_records = db.relationship('TaskHistory', back_populates='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='author', lazy=True, cascade='all, delete-orphan') # Relacionamento para comentários feitos pelo usuário

    uploaded_attachments = db.relationship(
        'Attachment',
        back_populates='uploader',
        lazy=True,
        foreign_keys='Attachment.uploaded_by_user_id',
        cascade='all, delete-orphan'
    )
    approved_attachments = db.relationship(
        'Attachment',
        back_populates='art_approved_by',
        lazy=True,
        foreign_keys='Attachment.art_approved_by_id' # Explicitar foreign_keys
    )

    # --- NOVO: Relacionamento para as inscrições de notificações push ---
    push_subscriptions = db.relationship('PushSubscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    # --- FIM NOVO ---

    # Relacionamento de volta para TaskChecklistItem.completed_by
    completed_task_checklist_items = db.relationship('TaskChecklistItem', back_populates='completed_by_user_rel', lazy=True)


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

    @property
    def can_approve_art(self):
        if self.is_admin:
            return True
        result = self.role_obj and self.role_obj.can_approve_art or False
        return result
    # --- FIM DA ADIÇÃO DE PROPRIEDADES ---

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
    def has_event_permission_for_task(self, event_id):
        event = db.session.get(Event, event_id)
        if not event:
            return False

        if event.author_id == self.id or self.is_admin:
            return True

        user_event_permission = EventPermission.query.options(joinedload(EventPermission.user)).filter(
            EventPermission.user_id == self.id,
            EventPermission.event_id == event_id
        ).first()

        if user_event_permission:
            return True
        return False

    def to_dict(self):
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
            'can_publish_event': self.can_publish_event,
            'can_cancel_event': self.can_cancel_event,
            'can_duplicate_event': self.can_duplicate_event,
            'can_view_event_registrations': self.can_view_event_registrations,
            'can_view_event_reports': self.can_view_event_reports,
            'can_approve_art': self.can_approve_art,
            'can_create_task': self.can_create_task,
            'can_edit_task': self.can_edit_task,
            'can_delete_task': self.can_delete_task,
            'can_complete_task': self.can_complete_task,
            'can_uncomplete_task': self.can_uncomplete_task,
            'can_upload_task_audio': self.can_upload_task_audio,
            'can_delete_task_audio': self.can_delete_task_audio,
            'can_view_task_history': self.can_view_task_history,
            'can_manage_task_comments': self.can_manage_task_comments,
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
    __tablename__ = 'password_reset_token'
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
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    __table_args__ = (UniqueConstraint('name', 'type', name='_name_type_uc'),)

    # RELACIONAMENTOS ATUALIZADOS PARA back_populates
    events_with_this_status = db.relationship('Event', back_populates='event_status', lazy=True)
    tasks_with_this_status = db.relationship('Task', back_populates='task_status_rel', lazy=True)

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

    is_published = db.Column(db.Boolean, default=False, nullable=False)
    is_cancelled = db.Column(db.Boolean, default=False, nullable=False)

    # Relacionamentos
    category = db.relationship('Category', backref='events', lazy=True)
    event_status = db.relationship('Status', foreign_keys=[status_id], back_populates='events_with_this_status', lazy=True)
    tasks = db.relationship('Task', backref='event', lazy='selectin', cascade="all, delete-orphan")
    event_permissions = db.relationship('EventPermission', back_populates='event', lazy=True, cascade='all, delete-orphan')
    
    attachments = db.relationship('Attachment', back_populates='event', lazy=True, cascade='all, delete-orphan') 

    def __init__(self, title, description, due_date, author_id, category_id, status_id, end_date=None, location=None, is_published=False, is_cancelled=False):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.author_id = author_id
        self.category_id = category_id
        self.status_id = status_id
        self.end_date = end_date
        self.location = location
        self.is_published = is_published
        self.is_cancelled = is_cancelled
        self.created_at = datetime.utcnow()

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
            'status_name': self.event_status.name if self.event_status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_published': self.is_published,
            'is_cancelled': self.is_cancelled
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

# MODIFICADO: TaskCategory para ter relacionamento com TaskSubcategory
class TaskCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = db.relationship('Task', back_populates='task_category', lazy=True, cascade='all, delete-orphan')
    subcategories = db.relationship('TaskSubcategory', back_populates='parent_category', lazy=True, cascade='all, delete-orphan')

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

# --- NOVOS MODELOS ---

# Model para Subcategorias de Tarefas
class TaskSubcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    task_category_id = db.Column(db.Integer, db.ForeignKey('task_category.id'), nullable=False)

    parent_category = db.relationship('TaskCategory', back_populates='subcategories')

    requires_art_approval_on_images = db.Column(db.Boolean, default=False, nullable=False)
    checklist_template_id = db.Column(db.Integer, db.ForeignKey('checklist_template.id'), nullable=True)
    checklist_template = db.relationship('ChecklistTemplate', back_populates='task_subcategories_using_this_template')
    tasks = db.relationship('Task', back_populates='task_subcategory', lazy=True)

    # NOVO CAMPO para o ID do papel do aprovador
    approver_role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)
    # Relacionamento para o papel aprovador (usando back_populates)
    approver_role = db.relationship('Role', foreign_keys=[approver_role_id], back_populates='approved_subcategories')

    def __repr__(self):
        return f"<TaskSubcategory '{self.name}' de '{self.parent_category.name if self.parent_category else 'N/A'}'>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'task_category_id': self.task_category_id,
            'parent_category_name': self.parent_category.name if self.parent_category else None,
            'requires_art_approval_on_images': self.requires_art_approval_on_images,
            'checklist_template_id': self.checklist_template_id,
            'checklist_template_name': self.checklist_template.name if self.checklist_template else None,
            'approver_role_id': self.approver_role_id, # Adicionado ao dicionário
            'approver_role_name': self.approver_role.name if self.approver_role else None # Adicionado ao dicionário
        }

# Model para o Template do Checklist (Definição dos checklists padrão)
class ChecklistTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    task_subcategories_using_this_template = db.relationship('TaskSubcategory', back_populates='checklist_template', lazy=True, cascade='all, delete-orphan')
    items = db.relationship('ChecklistItemTemplate', back_populates='template', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ChecklistTemplate '{self.name}'>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items': [item.to_dict() for item in self.items]
        }

# Model para Itens do Template do Checklist (Os itens que compõem um ChecklistTemplate)
class ChecklistItemTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_template_id = db.Column(db.Integer, db.ForeignKey('checklist_template.id'), nullable=False)
    
    template = db.relationship('ChecklistTemplate', back_populates='items')
    label = db.Column(db.String(255), nullable=False)
    
    # Coluna do Enum: Usa o CustomFieldTypeEnum
    field_type = db.Column(db.Enum(CustomFieldTypeEnum, name='custom_field_type_enum', create_type=False), nullable=False)
    
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    
    min_images = db.Column(db.Integer, nullable=True)
    max_images = db.Column(db.Integer, nullable=True)
    options = db.Column(db.Text, nullable=True)
    placeholder = db.Column(db.String(255), nullable=True)

    task_checklist_items = db.relationship('TaskChecklistItem', back_populates='template_item', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ChecklistItemTemplate '{self.label}' ({self.field_type.value})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'checklist_template_id': self.checklist_template_id,
            'label': self.label,
            'field_type': self.field_type.name, # Retorna o nome do enum (TEXT, IMAGE, etc.)
            'field_type_value': self.field_type.value, # Retorna o valor do enum (Texto Curto, Imagem/Arquivo Visual, etc.)
            'is_required': self.is_required,
            'order': self.order,
            'min_images': self.min_images,
            'max_images': self.max_images,
            'options': self.options,
            'placeholder': self.placeholder
        }

# MODIFICADO: Task para adicionar relacionamento com TaskSubcategory e TaskChecklist
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
    priority = db.Column(db.String(20), nullable=False, default='medium')
    
    # Única relação para attachments diretos da tarefa
    attachments = db.relationship('Attachment', back_populates='task', lazy=True, cascade='all, delete-orphan') # <-- MANTER ESTA
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_task_event_id'), nullable=False)
    task_status_id = db.Column(db.Integer, db.ForeignKey('status.id', name='fk_task_status_id'), nullable=False)
    task_category_id = db.Column(db.Integer, db.ForeignKey('task_category.id', name='fk_task_task_category_id'), nullable=True)
    task_subcategory_id = db.Column(db.Integer, db.ForeignKey('task_subcategory.id'), nullable=True)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_completed_by_id'), nullable=True)

    creator_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_creator_id'), nullable=False)

    # Relacionamentos
    task_status_rel = db.relationship('Status', foreign_keys=[task_status_id], back_populates='tasks_with_this_status', lazy=True)
    task_category = db.relationship('TaskCategory', back_populates='tasks', lazy=True)
    task_subcategory = db.relationship('TaskSubcategory', back_populates='tasks', lazy=True)
    
    checklist = db.relationship('TaskChecklist', back_populates='task', lazy=True, uselist=False, cascade="all, delete-orphan") # Relacionamento com TaskChecklist

    assignees_associations = db.relationship(
        'TaskAssignment',
        back_populates='task',
        lazy=True,
        cascade='all, delete-orphan'
    )
    
    completed_by_user_obj = db.relationship(
      'User', 
      foreign_keys=[completed_by_id],
      back_populates='tasks_completed_by_me'
    )

    creator_user_obj = db.relationship(
        'User', 
        foreign_keys=[creator_id], 
        back_populates='tasks_created_by_me'
    )

    history = db.relationship('TaskHistory', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='task', lazy=True, cascade='all, delete-orphan', order_by="Comment.timestamp.asc()")

    # REMOVIDO: a relação 'direct_attachments' era redundante e causava conflito.
    # A relação 'attachments' no início da classe Task já cumpre este papel.
    # direct_attachments = db.relationship(
    #     'Attachment',
    #     foreign_keys='Attachment.task_id',
    #     back_populates='task', # Vincula à propriedade 'task' em Attachment
    #     lazy=True,
    #     cascade='all, delete-orphan'
    # )


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
            'task_status_name': self.task_status_rel.name if self.task_status_rel else None,
            'task_category_id': self.task_category_id,
            'task_category_name': self.task_category.name if self.task_category else None,
            'task_subcategory_id': self.task_subcategory_id,
            'task_subcategory_name': self.task_subcategory.name if self.task_subcategory else None,
            'assigned_user_ids': assigned_user_ids,
            'assigned_usernames': assigned_usernames,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by_id': self.completed_by_id,
            'completed_by_username': self.completed_by_user_obj.username if self.completed_by_user_obj else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'attachments_count': len(self.attachments) if self.attachments is not None else 0,
            'checklist': self.checklist.to_dict() if self.checklist else None,
            'creator_id': self.creator_id,
            'creator_username': self.creator_user_obj.username if self.creator_user_obj else None, # <-- Vírgula adicionada aqui
            'priority': self.priority 
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

# MODIFICADO: ChangeLogEntry para usar db.Text e métodos estáticos
class ChangeLogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_changelog_user_id'), nullable=True)
    user_associated_with_log = db.relationship('User', back_populates='changelog_entries', foreign_keys=[user_id])
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    old_data = db.Column(db.Text, nullable=True)
    new_data = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_associated_with_log.username if self.user_associated_with_log else 'Desconhecido',
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'old_data': self.old_data_dict,
            'new_data': self.new_data_dict,
            'description': self.description
        }

    @staticmethod
    def log_creation(user_id, record_type, record_id, new_data, description=None):
        entry = ChangeLogEntry(
            user_id=user_id,
            record_type=record_type,
            record_id=record_id,
            action='create',
            new_data=json.dumps(new_data) if new_data else None,
            description=description
        )
        db.session.add(entry)

    @staticmethod
    def log_update(user_id, record_type, record_id, old_data, new_data, description=None):
        entry = ChangeLogEntry(
            user_id=user_id,
            record_type=record_type,
            record_id=record_id,
            action='update',
            old_data=json.dumps(old_data) if old_data else None,
            new_data=json.dumps(new_data) if new_data else None,
            description=description
        )
        db.session.add(entry)

    @staticmethod
    def log_deletion(user_id, record_type, record_id, old_data, description=None):
        entry = ChangeLogEntry(
            user_id=user_id,
            record_type=record_type,
            record_id=record_id,
            action='delete',
            old_data=json.dumps(old_data) if old_data else None,
            description=description
        )
        db.session.add(entry)

    @property
    def old_data_dict(self):
        return json.loads(self.old_data) if self.old_data else {}

    @property
    def new_data_dict(self):
        return json.loads(self.new_data) if self.new_data else {}

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_permission_user_id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = db.relationship('Event', back_populates='event_permissions')
    user = db.relationship('User', back_populates='event_permissions')
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='_event_user_unique_uc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'user_username': self.user.username if self.user else 'N/A',
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
    author = db.relationship('User', back_populates='comments')

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

# NOVO MODELO: TaskChecklist (associado a uma Task específica)
class TaskChecklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, unique=True)
    task = db.relationship('Task', back_populates='checklist')

    task_subcategory_id = db.Column(db.Integer, db.ForeignKey('task_subcategory.id'), nullable=False)
    task_subcategory = db.relationship('TaskSubcategory', backref='task_checklists', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = db.relationship('TaskChecklistItem', back_populates='task_checklist', lazy=True, cascade='all, delete-orphan', order_by='TaskChecklistItem.order')

    def __repr__(self):
        return f"<TaskChecklist for Task '{self.task.title if self.task else 'N/A'}' subcategory '{self.task_subcategory.name if self.task_subcategory else 'N/A'}'>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_title': self.task.title if self.task else None,
            'task_subcategory_id': self.task_subcategory_id,
            'task_subcategory_name': self.task_subcategory.name if self.task_subcategory else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items_count': len(self.items),
            'items': [item.to_dict() for item in self.items]
        }

# NOVO MODELO: TaskChecklistItem (valores preenchidos para uma Task específica)
class TaskChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_checklist_id = db.Column(db.Integer, db.ForeignKey('task_checklist.id'), nullable=False)
    task_checklist = db.relationship('TaskChecklist', back_populates='items')
    
    checklist_item_template_id = db.Column(db.Integer, db.ForeignKey('checklist_item_template.id'), nullable=True)
    template_item = db.relationship('ChecklistItemTemplate', back_populates='task_checklist_items')

    label = db.Column(db.String(255), nullable=False) # Este label vem do template
    
    custom_label = db.Column(db.String(255), nullable=True) # Para substituir o label do template, se necessário
    custom_field_type = db.Column(db.Enum(CustomFieldTypeEnum, name='custom_field_type_enum', create_type=False), nullable=False) # Para substituir o field_type do template, se necessário
    
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)

    # Colunas para armazenar os valores de diferentes tipos
    value_text = db.Column(db.Text, nullable=True)
    value_date = db.Column(db.Date, nullable=True)
    value_time = db.Column(db.Time, nullable=True)
    value_datetime = db.Column(db.DateTime, nullable=True)
    value_number = db.Column(db.Numeric(10, 2), nullable=True) # Mantive Numeric(10,2) para precisão
    value_boolean = db.Column(db.Boolean, nullable=True)
    
    # Campo is_completed adicionado
    is_completed = db.Column(db.Boolean, default=False, nullable=False)

    # Relacionamento com Attachments para este item específico do checklist
    attachments = db.relationship('Attachment', back_populates='task_checklist_item', lazy=True, cascade='all, delete-orphan')
    
    # Informações de conclusão do item do checklist
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_by_user_rel = db.relationship(
      'User', 
      foreign_keys=[completed_by_id], 
      back_populates='completed_task_checklist_items'
    )

    def __repr__(self):
        # Usar custom_label se existir, senão usar label do template
        display_label = self.custom_label if self.custom_label else self.label
        return f"<TaskChecklistItem '{display_label}' for Task '{self.task_checklist.task.title if self.task_checklist and self.task_checklist.task else 'N/A'}'>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_checklist_id': self.task_checklist_id,
            'checklist_item_template_id': self.checklist_item_template_id,
            'label': self.custom_label if self.custom_label else self.label, # Prioriza custom_label para exibição
            'field_type': self.custom_field_type.name, # Simplificado, já que custom_field_type é obrigatório
            'field_type_value': self.custom_field_type.value, # Simplificado
            'is_required': self.is_required,
            'order': self.order,
            'value_text': self.value_text,
            'value_date': self.value_date.isoformat() if self.value_date else None,
            'value_time': self.value_time.isoformat() if self.value_time else None,
            'value_datetime': self.value_datetime.isoformat() if self.value_datetime else None,
            'value_number': str(self.value_number) if self.value_number else None, # Converte Numeric para string
            'value_boolean': self.value_boolean,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by_id': self.completed_by_id,
            'completed_by_username': self.completed_by_user_rel.username if self.completed_by_user_rel else None,
            'attachments': [att.to_dict() for att in self.attachments] if self.attachments else []
        }

class Attachment(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    unique_filename = db.Column(db.String(255), unique=True, nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    mimetype = db.Column(db.String(100), nullable=True)
    filesize = db.Column(db.BigInteger, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_attachment_task_id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_attachment_event_id'), nullable=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_attachment_uploaded_by_user_id'), nullable=False)

    art_approval_status = db.Column(db.String(50), default='not_applicable', nullable=False)
    art_approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_attachment_art_approved_by_id'), nullable=True)
    art_approval_timestamp = db.Column(db.DateTime, nullable=True)
    art_feedback = db.Column(db.Text, nullable=True)

    task_checklist_item_id = db.Column(db.Integer, db.ForeignKey('task_checklist_item.id'), nullable=True)

    # Relacionamentos com back_populates para evitar conflitos
    task = db.relationship('Task', foreign_keys=[task_id], back_populates='attachments') # <-- CORRIGIDO AQUI
    event = db.relationship('Event', back_populates='attachments')
    uploader = db.relationship('User', back_populates='uploaded_attachments', foreign_keys=[uploaded_by_user_id])
    art_approved_by = db.relationship('User', foreign_keys=[art_approved_by_id], back_populates='approved_attachments')
    task_checklist_item = db.relationship('TaskChecklistItem', back_populates='attachments')

    def to_dict(self):
        from flask import url_for 
        return {
            'id': self.id,
            'task_id': self.task_id,
            'event_id': self.event_id,
            'filename': self.filename,
            'unique_filename': self.unique_filename,
            # 'storage_path': self.storage_path, # Removido por segurança
            'mimetype': self.mimetype,
            'filesize': self.filesize,
            'uploaded_by_user_id': self.uploaded_by_user_id,
            'uploaded_by_username': self.uploader.username if self.uploader else 'Desconhecido',
            'uploaded_at': self.uploaded_at.isoformat(),
            'public_url': url_for('main.serve_attachment_file', filename=self.unique_filename, _external=True),
            'art_approval_status': self.art_approval_status,
            'art_approved_by_id': self.art_approved_by_id,
            'art_approved_by_username': self.art_approved_by.username if self.art_approved_by else None,
            'art_approval_timestamp': self.art_approval_timestamp.isoformat() if self.art_approval_timestamp else None,
            'art_feedback': self.art_feedback,
            'task_checklist_item_id': self.task_checklist_item_id
        }

    def __repr__(self):
        return f"Attachment(ID: {self.id}, Filename: '{self.filename}', Task ID: {self.task_id}, Event ID: {self.event_id}, Status: {self.art_approval_status})"
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
    related_object_type = db.Column(db.String(50), nullable=True)
    related_object_id = db.Column(db.Integer, nullable=True)
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
    __tablename__ = 'push_subscription'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(512), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

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