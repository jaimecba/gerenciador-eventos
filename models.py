from extensions import db, login_manager
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import uuid
from flask_login import UserMixin

# --- ADICIONADO PARA DEPURAR A VERSÃO DO ITSDANGEROUS ---
print(f"DEBUG: Itsdangerous version being used: {itsdangerous.__version__}")
# --- FIM DA DEPURACAO ---

# Carrega um usuário dado seu ID para o Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """
    Função obrigatória para o Flask-Login carregar um usuário
    dado seu ID.
    """
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200)) # Armazena o hash da senha
    role = db.Column(db.String(20), default='user', nullable=False) # 'user', 'project_manager', 'admin'
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg') # Adicionado: Arquivo de imagem do perfil

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    events_created = db.relationship('Event', backref='author', lazy=True, foreign_keys='Event.author_id')
    changelog_entries = db.relationship('ChangeLogEntry', backref='user', lazy=True)
    
    # Relação com TaskAssignment (tabela intermediária para atribuição de tarefas)
    # A TaskAssignment tem um back_populates para 'user', e aqui é o outro lado.
    assigned_tasks = db.relationship('TaskAssignment', back_populates='user', lazy=True, cascade='all, delete-orphan')

    # Relação muitos-para-muitos com Group através do modelo UserGroup
    user_groups = db.relationship('UserGroup', back_populates='user', lazy=True, cascade='all, delete-orphan')
    
    # Relação um-para-muitos com EventPermission, onde o usuário é o foco da permissão
    # O back_populates aponta para EventPermission.user
    event_permissions = db.relationship('EventPermission', back_populates='user', lazy=True, cascade='all, delete-orphan')

    # Relacionamento com PasswordResetToken (NOVO)
    # Um usuário pode ter vários tokens de redefinição de senha (embora invalidaremos os antigos)
    # 'password_reset_tokens' será um atributo na classe User
    # 'user' será um atributo na classe PasswordResetToken (criado pelo backref)
    password_reset_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan')

    # NOVO BACKREF: Para tarefas que este usuário concluiu (definido em Task.completed_by)
    # Este 'backref' cria implicitamente Task.completed_by_user
    completed_tasks = db.relationship('Task', backref='completed_by_user', lazy=True, foreign_keys='Task.completed_by_id')

    # =========================================================================
    # AJUSTADO: Usando back_populates para TaskHistory
    # =========================================================================
    task_history_records = db.relationship('TaskHistory', back_populates='author', lazy=True, foreign_keys='TaskHistory.user_id')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        # A propriedade is_admin agora usa a coluna 'role'
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

# NOVO MODELO: PasswordResetToken para gerenciar tokens de redefinição de senha
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token' # Nome da tabela no banco de dados

    id = db.Column(db.Integer, primary_key=True)
    # O token único que será gerado (UUID) e assinado para o link
    token_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_password_reset_token_user_id'), nullable=False) # Chave estrangeira para o usuário
    expiration_date = db.Column(db.DateTime, nullable=False) # Data/hora de expiração do token
    is_used = db.Column(db.Boolean, default=False, nullable=False) # Flag para indicar se o token já foi usado
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False) # Data de criação do token

    def is_expired(self):
        # Verifica se o token já expirou comparando com a data atual UTC
        return datetime.utcnow() > self.expiration_date


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
    status_id = db.Column(db.Integer, db.ForeignKey('event_status.id', name='fk_event_status_id'), nullable=True)

    # Relacionamentos
    category = db.relationship('Category', backref='events', lazy=True)
    status = db.relationship('EventStatus', backref='events', lazy=True) # Este é o objeto EventStatus
    tasks = db.relationship('Task', backref='event', lazy='selectin', cascade="all, delete-orphan")

    # Relação um-para-muitos com EventPermission (um evento pode ter várias permissões)
    event_permissions = db.relationship('EventPermission', back_populates='event', lazy=True, cascade='all, delete-orphan')

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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"Event('{self.title}', Due: '{self.due_date}', End: '{self.end_date}', Loc: '{self.location}')"

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

# =========================================================================
# NOVO MODELO: TaskCategory - para gerenciar categorias de tarefas
# (Este modelo já estava correto na sua versão)
# =========================================================================
class TaskCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = db.relationship('Task', back_populates='task_category', lazy=True) # Relacionamento com Tarefas

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
# =========================================================================
# FIM NOVO MODELO: TaskCategory
# =========================================================================


class EventStatus(db.Model):
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
        return f"EventStatus('{self.name}')"

class TaskStatus(db.Model):
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
        return f"TaskStatus('{self.name}')"

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
    task_status_id = db.Column(db.Integer, db.ForeignKey('task_status.id', name='fk_task_status_id'), nullable=False)
    
    # =========================================================================
    # ALTERAÇÕES NO MODELO TASK (já estavam corretas na sua versão):
    # 1. REMOVIDO: category_id (que apontava para Category de Eventos)
    # 2. ADICIONADO: task_category_id (que apontará para a nova TaskCategory)
    # =========================================================================
    task_category_id = db.Column(db.Integer, db.ForeignKey('task_category.id', name='fk_task_task_category_id'), nullable=True)
    
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_completed_by_id'), nullable=True)

    # Relacionamentos
    task_status = db.relationship('TaskStatus', backref='tasks', lazy=True)
    # O relacionamento 'category' antigo foi removido, agora usamos 'task_category'
    task_category = db.relationship('TaskCategory', back_populates='tasks', lazy=True) # Novo relacionamento com TaskCategory

    assignees_associations = db.relationship('TaskAssignment', back_populates='task', lazy=True, cascade='all, delete-orphan')
    completed_by = db.relationship('User', foreign_keys=[completed_by_id], overlaps="completed_by_user,completed_tasks")
    history = db.relationship('TaskHistory', backref='task', lazy='dynamic', cascade='all, delete-orphan')


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
            # =========================================================================
            # ALTERAÇÕES NO TO_DICT DO MODELO TASK (já estavam corretas na sua versão):
            # 1. REMOVIDO: 'category_id'
            # 2. ADICIONADO: 'task_category_id' e 'task_category_name'
            # =========================================================================
            'task_category_id': self.task_category_id,
            'task_category_name': self.task_category.name if self.task_category else None, # Nome da categoria da tarefa
            
            'assigned_user_ids': assigned_user_ids,
            'assigned_usernames': assigned_usernames,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by_id': self.completed_by_id,
            'completed_by_username': self.completed_by_user.username if self.completed_by_user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        # Corrigido para mostrar a categoria da tarefa
        category_name = self.task_category.name if self.task_category else 'N/A'
        return f"Task('{self.title}', '{self.due_date}', Category: '{category_name}')"

class TaskAssignment(db.Model):
    __tablename__ = 'task_assignment'
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_task_assignment_task_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_assignment_user_id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship('Task', back_populates='assignees_associations')
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
    action_type = db.Column(db.String(50), nullable=False) # Ex: 'criacao', 'edicao', 'conclusao', 'transferencia', 'comentario'
    description = db.Column(db.Text, nullable=True) # Descrição breve da ação
    
    old_value = db.Column(db.Text, nullable=True) 
    new_value = db.Column(db.Text, nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_history_user_id'), nullable=False) # Quem realizou a ação
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    comment = db.Column(db.Text, nullable=True) # Comentários adicionais da ação (ex: motivo da transferência, observações da conclusão)

    # Relacionamentos
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
    record_id = db.Column(db.Integer, nullable=True) # Pode ser nulo se a ação não se referir a um registro específico
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
    def log_creation(cls, user_id, record_type, record_id, new_data, description):
        entry = cls(
            user_id=user_id,
            action='create',
            record_type=record_type,
            record_id=record_id,
            new_data=new_data,
            description=description
        )
        db.session.add(entry)

    @classmethod
    def log_update(cls, user_id, record_type, record_id, old_data, new_data, description):
        entry = cls(
            user_id=user_id,
            action='update',
            record_type=record_type,
            record_id=record_id,
            old_data=old_data,
            new_data=new_data,
            description=description
        )
        db.session.add(entry)

    @classmethod
    def log_deletion(cls, user_id, record_type, record_id, old_data, description):
        entry = cls(
            user_id=user_id,
            action='delete',
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
    event_permissions = db.relationship('EventPermission', back_populates='group', lazy=True, cascade='all, delete-orphan')

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_permission_user_id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', name='fk_event_permission_group_id'), nullable=True)

    can_view = db.Column(db.Boolean, default=True, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = db.relationship('Event', back_populates='event_permissions')
    user = db.relationship('User', back_populates='event_permissions') 
    group = db.relationship('Group', back_populates='event_permissions')

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', 'group_id', name='_event_user_group_uc'),
        db.CheckConstraint(
            '(user_id IS NOT NULL AND group_id IS NULL) OR (user_id IS NULL AND group_id IS NOT NULL)',
            name='_user_or_group_check'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'can_view': self.can_view,
            'can_edit': self.can_edit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        target = f"User ID: {self.user_id}" if self.user_id else f"Group ID: {self.group_id}"
        return f"EventPermission(Event ID: {self.event_id}, {target}, View: {self.can_view}, Edit: {self.can_edit})"
