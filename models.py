# C:\\\\\\\\\\\gerenciador-eventos\\\\\\\\\\\models.py

from extensions import db, login_manager
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
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
    
    # NOVO: Permissão para criar eventos
    can_create_event = db.Column(db.Boolean, default=False, nullable=False)

    # --- NOVAS COLUNAS: Capacidades de permissão de TAREFA granular (ADICIONADAS AQUI) ---
    can_create_task = db.Column(db.Boolean, default=False, nullable=False)
    can_edit_task = db.Column(db.Boolean, default=False, nullable=False)
    can_delete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_complete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_uncomplete_task = db.Column(db.Boolean, default=False, nullable=False)
    can_upload_task_audio = db.Column(db.Boolean, default=False, nullable=False)
    can_delete_task_audio = db.Column(db.Boolean, default=False, nullable=False)
    can_view_task_history = db.Column(db.Boolean, default=False, nullable=False)
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
            'can_create_event': self.can_create_event, # Adicionado
            # Incluir as novas permissões de tarefa no dicionário
            'can_create_task': self.can_create_task,
            'can_edit_task': self.can_edit_task,
            'can_delete_task': self.can_delete_task,
            'can_complete_task': self.can_complete_task,
            'can_uncomplete_task': self.can_uncomplete_task,
            'can_upload_task_audio': self.can_upload_task_audio,
            'can_delete_task_audio': self.can_delete_task_audio,
            'can_view_task_history': self.can_view_task_history
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

    # CORRIGIDO: Removida a referência `foreign_keys=[TaskHistory.user_id]`
    # O SQLAlchemy pode inferir a FK se a relação for clara e back_populates for usado.
    task_history_records = db.relationship('TaskHistory', back_populates='author', lazy=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_active(self):
        return self.is_active_db

    @property
    def role(self):
        # Este 'role' retorna o nome da role para compatibilidade, não o objeto Role completo.
        # Para acessar permissões da role, use 'self.role_obj.<permissao>'
        role_name = self.role_obj.name if self.role_obj else 'unknown'
        # --- DEPURACAO ADICIONADA ---
        print(f"DEBUG_USER_ROLE: Para user '{self.username}', propriedade 'role' retornando: '{role_name}' (role_obj presente: {self.role_obj is not None})")
        # --- FIM DA DEPURACAO ---
        return role_name

    @property
    def is_admin(self):
        # Esta é uma verificação simples para 'Admin' baseada no nome da role.
        # Para verificações mais granulares, use self.role_obj.<permissao>
        is_admin_status = (self.role == 'Admin')
        # --- DEPURACAO ADICIONADA ---
        print(f"DEBUG_IS_ADMIN: Para user '{self.username}', is_admin avaliado como: {is_admin_status} (baseado em role=='{self.role}')")
        # --- FIM DA DEPURACAO ---
        return is_admin_status

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
        # Usamos joinedload para carregar a Role junto e evitar N+1 queries
        user_event_permission = EventPermission.query.options(joinedload(EventPermission.role)).filter(
            EventPermission.user_id == self.id,
            EventPermission.event_id == event_id
        ).first()

        if user_event_permission and user_event_permission.role:
            # 4. Verificar se a role associada a essa EventPermission concede edição de evento
            # (que atualmente engloba a capacidade de manipular tarefas, mas isso será refinado nas rotas)
            if user_event_permission.role.can_edit_event: # Alterado de can_view_event AND can_edit_event para apenas can_edit_event
                return True
        
        # 5. Verificar permissões de grupo
        # Isso envolve:
        # a) Pegar todos os grupos aos quais este usuário pertence.
        # b) Para cada grupo, buscar EventPermission para esse event_id e group_id.
        # c) Se encontrar e a role do grupo permitir can_edit_event, retornar True.
        for user_group_assoc in self.user_groups:
            group_permission = EventPermission.query.options(joinedload(EventPermission.role)).filter(
                EventPermission.group_id == user_group_assoc.group_id,
                EventPermission.event_id == event_id
            ).first()
            if group_permission and group_permission.role and \
               group_permission.role.can_edit_event: # Alterado de can_view_event AND can_edit_event para apenas can_edit_event
                return True

        return False # Nenhuma permissão suficiente encontrada
    # --- FIM NOVO MÉTODO ---


    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active_db,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Role: '{self.role}')"

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

    # Relacionamentos
    category = db.relationship('Category', backref='events', lazy=True)
    status = db.relationship('Status', foreign_keys=[status_id], backref='events', lazy=True)
    
    tasks = db.relationship('Task', backref='event', lazy='selectin', cascade="all, delete-orphan")
    
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

    # >> REMOVIDO: A relação 'task_assignments' e seu backref 'task_obj' causavam conflito.
    # >> Assumimos que 'assignees_associations' é a relação principal para atribuições.
    # task_assignments = db.relationship('TaskAssignment', backref='task_obj', lazy=True, cascade='all, delete-orphan')
    
    # Esta é a relação principal para atribuições de tarefas (Task -> TaskAssignment)
    assignees_associations = db.relationship(
        'TaskAssignment', 
        back_populates='task', 
        lazy=True, 
        cascade='all, delete-orphan',
        # AGORA COM OVERLAPS EXATO SUGERIDO PELO WARNING PARA Task.assignees_associations
        overlaps="task_assignments,task_obj" 
    )

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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        category_name = self.task_category.name if self.task_category else 'N/A'
        return f"Task('{self.title}', '{self.due_date}', Category: '{category_name}')"

class TaskAssignment(db.Model):
    __tablename__ = 'task_assignment'
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', name='fk_task_assignment_task_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_task_assignment_user_id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Esta é a relação TaskAssignment -> Task
    task = db.relationship(
        'Task', 
        back_populates='assignees_associations',
        # AGORA COM OVERLAPS EXATO SUGERIDO PELO WARNING PARA TaskAssignment.task
        overlaps="task_assignments,task_obj" 
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_permission_user_id', ondelete='CASCADE'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', name='fk_event_permission_group_id', ondelete='CASCADE'), nullable=True)
    
    role_id = db.Column(db.Integer, db.ForeignKey('role.id', name='fk_event_permission_role_id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = db.relationship('Event', back_populates='event_permissions')
    user = db.relationship('User', back_populates='event_permissions') 
    group = db.relationship('Group', back_populates='event_permissions')
    role = db.relationship('Role') # Mantenha este relacionamento para carregar as propriedades da Role

    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND group_id IS NULL) OR (user_id IS NULL AND group_id IS NOT NULL)',
            name='_user_or_group_check'
        ),
        # --- CORREÇÃO AQUI: Usando db.Index para unique constraints parciais ---
        Index('_event_user_unique_idx', 'event_id', 'user_id', unique=True,
                 postgresql_where=db.Column('user_id').isnot(None)),
        Index('_event_group_unique_idx', 'event_id', 'group_id', unique=True,
                 postgresql_where=db.Column('group_id').isnot(None)),
        # --- FIM DA CORREÇÃO ---
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        target = f"User ID: {self.user_id}" if self.user_id else f"Group ID: {self.group_id}"
        return f"EventPermission(Event ID: {self.event_id}, {target}, Role: {self.role.name if self.role else 'N/A'})"