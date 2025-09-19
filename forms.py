# C:\\\\\\\\\\\gerenciador-eventos\\\\\\\\\\\forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateTimeLocalField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp, URL
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from flask_login import current_user
from models import User, Category, Status, Group, Event, TaskCategory, Role
from datetime import datetime

# =========================================================================
# Funções auxiliares para QuerySelectField
# =========================================================================
def get_event_statuses():
    return Status.query.filter_by(type='event').order_by(Status.name).all()

def get_task_statuses():
    return Status.query.filter_by(type='task').order_by(Status.name).all()

def get_event_categories():
    return Category.query.order_by(Category.name).all()

def get_task_categories():
    return TaskCategory.query.order_by(TaskCategory.name).all()

def get_roles():
    # Retorna todas as roles, incluindo suas capacidades de evento.
    # Pode ser filtrado se você quiser exibir apenas roles específicas para permissões de evento.
    return Role.query.order_by(Role.name).all()

def get_users():
    # Incluindo 'is_active_db=True' para garantir que apenas usuários ativos sejam listados
    return User.query.filter_by(is_active_db=True).order_by(User.username).all()

def get_groups():
    return Group.query.order_by(Group.name).all()

def get_events():
    return Event.query.order_by(Event.title).all()
# =========================================================================
# FIM das Funções auxiliares
# =========================================================================

class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[
        DataRequired(),
        Length(min=2, max=20),
        Regexp('^[a-z]+$', message='O nome de usuário deve conter apenas letras minúsculas.')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está em uso. Por favor, escolha outro.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Atualizar Foto de Perfil', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Atualizar')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Este email já está em uso. Por favor, escolha outro.')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Redefinição de Senha')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Não há conta com este email. Você pode se registrar primeiro.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Redefinir Senha')

class SearchForm(FlaskForm):
    search_query = StringField('Buscar', validators=[Optional()])
    submit = SubmitField('Buscar')

class EventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    due_date = DateTimeLocalField('Data de Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeLocalField('Data de Término (Opcional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    location = StringField('Local', validators=[Optional(), Length(max=100)])

    category = QuerySelectField(
        'Categoria',
        query_factory=get_event_categories,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='-- Selecione uma Categoria (Opcional) --'
    )

    status = QuerySelectField(
        'Status do Evento',
        query_factory=get_event_statuses,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        validators=[DataRequired()]
    )
    submit = SubmitField('Salvar Evento')


class CategoryForm(FlaskForm):
    name = StringField('Nome da Categoria', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria')

    def __init__(self, original_name=None, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            category = Category.query.filter_by(name=name.data).first()
            if category:
                raise ValidationError('Este nome de categoria já existe. Por favor, escolha outro.')


class TaskCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria da Tarefa', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria da Tarefa')

    def __init__(self, original_name=None, *args, **kwargs):
        super(TaskCategoryForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            task_category = TaskCategory.query.filter_by(name=name.data).first()
            if task_category:
                raise ValidationError('Este nome de categoria de tarefa já existe. Por favor, escolha outro.')


class StatusForm(FlaskForm):
    name = StringField('Nome do Status', validators=[DataRequired(), Length(min=2, max=50)])
    type = SelectField('Tipo de Status', choices=[('event', 'Evento'), ('task', 'Tarefa')], validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Status')

    def __init__(self, original_name=None, original_type=None, *args, **kwargs):
        super(StatusForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        self.original_type = original_type

    def validate_name(self, name):
        if self.original_name is None or (name.data != self.original_name or self.type.data != self.original_type):
            status = Status.query.filter_by(name=name.data, type=self.type.data).first()
            if status:
                raise ValidationError(f"Um status com o nome '{name.data}' e tipo '{self.type.data}' já existe. Por favor, escolha outro nome ou tipo.")


class TaskForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    notes = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    due_date = DateTimeLocalField('Data de Vencimento', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])

    cloud_storage_link = StringField('Link de Armazenamento em Nuvem', validators=[Optional(), Length(max=500), URL()])
    link_notes = TextAreaField('Observações do Link', validators=[Optional()])

    task_category = QuerySelectField(
        'Categoria da Tarefa',
        query_factory=get_task_categories,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='-- Selecione uma Categoria de Tarefa (Opcional) --'
    )

    status = QuerySelectField(
        'Status da Tarefa',
        query_factory=get_task_statuses,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        validators=[DataRequired()]
    )

    # Este campo está correto para seleção múltipla de usuários
    assignees = QuerySelectMultipleField(
        'Atribuir a',
        query_factory=get_users,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.username,
        # widget=ListWidget(prefix_label=False),  # Você pode descomentar e usar se preferir checkboxes
        # option_widget=CheckboxInput()           # ou manter o dropdown múltiplo padrão
    )
    
    event = QuerySelectField(
        'Evento Relacionado',
        query_factory=get_events,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.title,
        validators=[DataRequired()],
        render_kw={'disabled': True}
    )

    submit = SubmitField('Salvar Tarefa')

class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[
        DataRequired(),
        Length(min=2, max=20),
        Regexp('^[a-z]+$', message='O nome de usuário deve conter apenas letras minúsculas.')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha')
    confirm_password = PasswordField('Confirmar Senha')
    
    role_obj = QuerySelectField(
        'Papel',
        query_factory=get_roles,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        blank_text='-- Selecione um Papel --',
        validators=[DataRequired()]
    )
    submit = SubmitField('Salvar Alterações')

    def __init__(self, original_username=None, original_email=None, is_new_user=False, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        self.is_new_user = is_new_user

        if self.is_new_user:
            self.password.validators = [DataRequired(), Length(min=6)]
            self.confirm_password.validators = [DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')]
            self.submit.label.text = 'Criar Usuário'
        else:
            self.password.validators = [Optional(), Length(min=6)]
            self.confirm_password.validators = [Optional(), EqualTo('password', message='As senhas devem ser iguais.')]
            self.submit.label.text = 'Atualizar Usuário'

    def validate_username(self, username):
        if self.is_new_user or (username.data != self.original_username):
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        if self.is_new_user or (email.data != self.original_email):
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Este email já está em uso. Por favor, escolha outro.')

class GroupForm(FlaskForm):
    name = StringField('Nome do Grupo', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Grupo')

    def __init__(self, original_name=None, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            group = Group.query.filter_by(name=name.data).first()
            if group:
                raise ValidationError('Este nome de grupo já existe. Por favor, escolha outro.')

class AssignUsersToGroupForm(FlaskForm):
    users = QuerySelectMultipleField(
        'Membros do Grupo',
        query_factory=get_users,
        get_label='username',
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput()
    )
    submit = SubmitField('Atualizar Membros do Grupo')


class EventPermissionForm(FlaskForm):
    event = QuerySelectField(
        'Selecionar Evento',
        query_factory=get_events,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.title,
        validators=[DataRequired()]
    )
    user = QuerySelectField(
        'Selecionar Usuário Específico (Opcional)',
        query_factory=get_users,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.username,
        allow_blank=True,
        blank_text='--- N/A ---'
    )
    group = QuerySelectField(
        'Selecionar Grupo (Opcional)',
        query_factory=get_groups,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='--- N/A ---'
    )
    # --- NOVO CAMPO: Selecionar a Role para a permissão ---
    role = QuerySelectField(
        'Selecionar Papel (Permissão)',
        query_factory=get_roles,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        validators=[DataRequired()]
    )
    # --- CAMPOS REMOVIDOS: can_view e can_edit ---
    # can_view = BooleanField('Pode Visualizar', default=True)
    # can_edit = BooleanField('Pode Editar', default=False)
    submit = SubmitField('Definir Permissões')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        user_selected = self.user.data is not None
        group_selected = self.group.data is not None
        role_selected = self.role.data is not None # Verifica se uma role foi selecionada

        if not (user_selected or group_selected):
            self.user.errors.append('Selecione um usuário OU um grupo para definir a permissão.')
            self.group.errors.append('Selecione um usuário OU um grupo para definir a permissão.')
            return False

        if user_selected and group_selected:
            self.user.errors.append('Permissões podem ser atribuídas a um usuário OU a um grupo, não ambos.')
            self.group.errors.append('Permissões podem ser atribuídas a um usuário OU a um grupo, não ambos.')
            return False
        
        if not role_selected:
            self.role.errors.append('Selecione um papel para a permissão.')
            return False

        return True

# Formulário simples para o modelo Role para uso no Admin
class AdminRoleForm(FlaskForm):
    name = StringField('Nome do Papel', validators=[DataRequired(), Length(min=2, max=80)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    # --- Permissões de Evento (existentes) ---
    can_view_event = BooleanField('Pode Visualizar Eventos', default=False)
    can_edit_event = BooleanField('Pode Editar Eventos', default=False)
    can_manage_permissions = BooleanField('Pode Gerenciar Permissões de Evento', default=False)
    can_create_event = BooleanField('Pode Criar Eventos', default=False) # <--- NOVO CAMPO AQUI
    # --- NOVAS Permissões específicas de Tarefa ---
    can_create_task = BooleanField('Pode Criar Tarefas', default=False)
    can_edit_task = BooleanField('Pode Editar Tarefas', default=False)
    can_delete_task = BooleanField('Pode Excluir Tarefas', default=False)
    can_complete_task = BooleanField('Pode Concluir Tarefas', default=False)
    can_uncomplete_task = BooleanField('Pode Reabrir Tarefas Concluídas', default=False)
    can_upload_task_audio = BooleanField('Pode Fazer Upload de Áudio em Tarefas', default=False)
    can_delete_task_audio = BooleanField('Pode Excluir Áudio de Tarefas', default=False)
    can_view_task_history = BooleanField('Pode Visualizar Histórico de Tarefas', default=False)
    # --- FIM NOVAS Permissões de Tarefa ---
    submit = SubmitField('Salvar Papel') # Adicionado botão de submit, caso não houvesse

# NOVO: Formulário simples para o modelo Group para uso no Admin
class AdminGroupForm(FlaskForm):
    name = StringField('Nome do Grupo', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Grupo') # Adicionado botão de submit

# NOVO: Formulário simples para o modelo Category para uso no Admin
class AdminCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria') # Adicionado botão de submit

# NOVO: Formulário simples para o modelo TaskCategory para uso no Admin
class AdminTaskCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria da Tarefa', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria da Tarefa') # Adicionado botão de submit

# NOVO: Formulário simples para o modelo Status para uso no Admin
class AdminStatusForm(FlaskForm):
    name = StringField('Nome do Status', validators=[DataRequired(), Length(min=2, max=50)])
    type = SelectField('Tipo de Status', choices=[('event', 'Evento'), ('task', 'Tarefa')], validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Status') # Adicionado botão de submit

# NOVO: Formulário simples para o modelo Event para uso no Admin
class AdminEventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    due_date = DateTimeLocalField('Data de Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeLocalField('Data de Término (Opcional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    location = StringField('Local', validators=[Optional(), Length(max=100)])

    # Seleção do autor do evento (User)
    author = QuerySelectField(
        'Autor',
        query_factory=get_users,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.username,
        validators=[DataRequired()]
    )

    # Seleção da categoria do evento
    category = QuerySelectField(
        'Categoria',
        query_factory=get_event_categories,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='-- Selecione uma Categoria (Opcional) --'
    )

    # Seleção do status do evento
    status = QuerySelectField(
        'Status do Evento',
        query_factory=get_event_statuses,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        validators=[DataRequired()]
    )
    submit = SubmitField('Salvar Evento') # Adicionado botão de submit