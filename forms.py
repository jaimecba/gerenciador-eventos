from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateTimeLocalField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms_sqlalchemy.fields import QuerySelectMultipleField # Importado no seu código
# =========================================================================
# ALTERAÇÃO: Importado TaskCategory
# =========================================================================
from models import User, Category, EventStatus, TaskStatus, Group, Event, TaskCategory
from flask_login import current_user
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField # Já estava aqui


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
    end_date = DateTimeLocalField('Data de Término', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    location = StringField('Local', validators=[Optional(), Length(max=100)])

    category = QuerySelectField(
        'Categoria',
        query_factory=lambda: Category.query.order_by(Category.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='-- Selecione uma Categoria (Opcional) --'
    )

    status = QuerySelectField(
        'Status do Evento',
        query_factory=lambda: EventStatus.query.order_by(EventStatus.name).all(),
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

# =========================================================================
# NOVO FORMULÁRIO: TaskCategoryForm - para gerenciar categorias de tarefas
# =========================================================================
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
# =========================================================================
# FIM NOVO FORMULÁRIO: TaskCategoryForm
# =========================================================================

class StatusForm(FlaskForm):
    name = StringField('Nome do Status', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Status')

    def __init__(self, original_name=None, *args, **kwargs):
        super(StatusForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            event_status = EventStatus.query.filter_by(name=name.data).first()
            task_status = TaskStatus.query.filter_by(name=name.data).first()
            if event_status or task_status:
                raise ValidationError('Este nome de status já existe. Por favor, escolha outro.')

class TaskForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    notes = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    due_date = DateTimeLocalField('Data de Vencimento', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])

    cloud_storage_link = StringField('Link de Armazenamento em Nuvem', validators=[Optional(), Length(max=500)])
    link_notes = TextAreaField('Observações do Link', validators=[Optional()])

    # =========================================================================
    # ALTERAÇÃO: O campo 'category' foi renomeado para 'task_category'
    # e agora usa o modelo TaskCategory.
    # =========================================================================
    # REMOVIDO: category = QuerySelectField(...)
    task_category = QuerySelectField(
        'Categoria da Tarefa', # Alterado o rótulo
        query_factory=lambda: TaskCategory.query.order_by(TaskCategory.name).all(), # Agora usa TaskCategory
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='-- Selecione uma Categoria de Tarefa (Opcional) --' # Alterado o texto em branco
    )

    status = QuerySelectField(
        'Status da Tarefa',
        query_factory=lambda: TaskStatus.query.order_by(TaskStatus.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        validators=[DataRequired()]
    )

    assignees = QuerySelectMultipleField(
        'Atribuir a',
        query_factory=lambda: User.query.order_by(User.username).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.username,
        allow_blank=True,
        blank_text='-- Selecione Usuários (Opcional) --'
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
    role = SelectField('Papel', choices=[('user', 'Usuário'), ('project_manager', 'Gerente de Projeto'), ('admin', 'Administrador')], validators=[DataRequired()])
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
        query_factory=lambda: User.query.order_by(User.username).all(),
        get_label='username',
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput()
    )
    submit = SubmitField('Atualizar Membros do Grupo')


class EventPermissionForm(FlaskForm):
    event = QuerySelectField(
        'Selecionar Evento',
        query_factory=lambda: Event.query.order_by(Event.title).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.title,
        validators=[DataRequired()]
    )
    user = QuerySelectField(
        'Selecionar Usuário Específico (Opcional)',
        query_factory=lambda: User.query.order_by(User.username).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.username,
        allow_blank=True,
        blank_text='--- N/A ---'
    )
    group = QuerySelectField(
        'Selecionar Grupo (Opcional)',
        query_factory=lambda: Group.query.order_by(Group.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=True,
        blank_text='--- N/A ---'
    )
    can_view = BooleanField('Pode Visualizar', default=True)
    can_edit = BooleanField('Pode Editar', default=False)
    submit = SubmitField('Definir Permissões')

    def validate(self, extra_validators=None):
        initial_validation = super().validate(extra_validators)
        if not initial_validation:
            return False

        user_selected = self.user.data is not None
        group_selected = self.group.data is not None

        if not (user_selected or group_selected):
            self.user.errors.append('Selecione um usuário OU um grupo para definir a permissão.')
            self.group.errors.append('Selecione um usuário OU um grupo para definir a permissão.')
            return False

        if user_selected and group_selected:
            self.user.errors.append('Permissões podem ser atribuídas a um usuário OU a um grupo, não ambos.')
            self.group.errors.append('Permissões podem ser atribuídas a um usuário OU a um grupo, não ambos.')
            return False

        return True