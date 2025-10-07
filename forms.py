# C:\gerenciador-eventos\forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateField, SelectField, SelectMultipleField, HiddenField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
# --- ATUALIZADO: Importar Attachment e EventPermission ---
from models import User, Category, Status, TaskCategory, Role, Group, Attachment, EventPermission
from extensions import db
from flask_login import current_user
from datetime import date, datetime
from wtforms.widgets import ListWidget, CheckboxInput # Manter essas importações se MultipleCheckboxField for usado em outros lugares

# NOVO CAMPO PERSONALIZADO: MultipleCheckboxField
# Mantenha esta classe se você a usa em outros formulários.
# Se TaskForm é o único lugar onde você precisava de seleção múltipla,
# e agora usará SelectMultipleField padrão, você pode remover esta classe.
class MultipleCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

# Função auxiliar para pegar usuários ativos
def get_users():
    # print("DEBUG_GET_USERS: Executando get_users()...") # Descomentar para depuração
    # Certifique-se que seu modelo User tem o campo is_active_db
    users = User.query.filter_by(is_active_db=True).order_by(User.username).all()
    # print(f"DEBUG_GET_USERS: get_users() retornou {len(users)} usuários.") # Descomentar para depuração
    return users

# Função auxiliar para pegar categorias de tarefas
def get_task_categories():
    return TaskCategory.query.order_by(TaskCategory.name).all()

# Função auxiliar para pegar status de tarefas (filtrando por type='task')
def get_task_statuses():
    return Status.query.filter_by(type='task').order_by(Status.name).all()

# Função auxiliar para pegar roles
def get_roles():
    return Role.query.order_by(Role.name).all()


class RegistrationForm(FlaskForm):
    username = StringField('Nome de Usuário',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Esse nome de usuário já existe. Por favor, escolha um diferente.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Esse e-mail já existe. Por favor, escolha um diferente.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Nome de Usuário',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    picture = FileField('Atualizar Foto de Perfil', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Atualizar')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Esse nome de usuário já existe. Por favor, escolha um diferente.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Esse e-mail já existe. Por favor, escolha um diferente.')

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Redefinir Senha')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Não existe conta com este e-mail. Você pode se registrar primeiro.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Nova Senha',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Redefinir Senha')

class EventForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])

    # === ALTERAÇÃO FEITA AQUI ===
    due_date = DateTimeField('Data de Vencimento', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={'type': 'datetime-local'})
    end_date = DateTimeField('Data de Término (Opcional)', format='%Y-%m-%dT%H:%M', validators=[Optional()], render_kw={'type': 'datetime-local'})
    # ============================

    location = StringField('Localização', validators=[Optional(), Length(max=100)])

    category = SelectField('Categoria', coerce=int)
    status = SelectField('Status', coerce=int)

    submit = SubmitField('Salvar Evento')

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        self.status.choices = [(s.id, s.name) for s in Status.query.filter_by(type='event').order_by(Status.name).all()]

class CategoryForm(FlaskForm):
    name = StringField('Nome da Categoria', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria')

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.original_name = kwargs.get('original_name') # Para validação de atualização

    def validate_name(self, name):
        if name.data != self.original_name: # Apenas valida se o nome mudou
            category = Category.query.filter_by(name=name.data).first()
            if category:
                raise ValidationError('Este nome de categoria já existe. Por favor, escolha um diferente.')

class StatusForm(FlaskForm):
    name = StringField('Nome do Status', validators=[DataRequired(), Length(max=80)])
    type = SelectField('Tipo', choices=[('event', 'Evento'), ('task', 'Tarefa')], validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Salvar Status')

    def __init__(self, *args, **kwargs):
        super(StatusForm, self).__init__(*args, **kwargs)
        self.original_name = kwargs.get('original_name')
        self.original_type = kwargs.get('original_type')

    def validate_name(self, name):
        # Apenas valida se o nome OU o tipo mudaram para evitar conflitos com ele mesmo
        if name.data != self.original_name or self.type.data != self.original_type:
            status_entry = Status.query.filter_by(name=name.data, type=self.type.data).first()
            if status_entry:
                raise ValidationError(f'Já existe um status com o nome "{name.data}" para o tipo "{self.type.data}".')

class TaskCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria de Tarefa', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria de Tarefa')

    def __init__(self, *args, **kwargs):
        super(TaskCategoryForm, self).__init__(*args, **kwargs)
        self.original_name = kwargs.get('original_name')

    def validate_name(self, name):
        if name.data != self.original_name:
            task_category = TaskCategory.query.filter_by(name=name.data).first()
            if task_category:
                raise ValidationError('Este nome de categoria de tarefa já existe. Por favor, escolha um diferente.')

class TaskForm(FlaskForm):
    title = StringField('Título da Tarefa', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])
    notes = TextAreaField('Notas Internas (visíveis apenas para quem pode gerenciar a tarefa)', validators=[Optional()])
    due_date = DateTimeField('Data de Vencimento', format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={'type': 'datetime-local'})

    cloud_storage_link = StringField('Link para Armazenamento na Nuvem', validators=[Optional()])
    link_notes = TextAreaField('Notas sobre o Link', validators=[Optional()])

    # === CORREÇÃO AQUI: Troca para SelectMultipleField padrão ===
    assignees = SelectMultipleField('Atribuir a Usuários', coerce=int)
    # ==========================================================

    task_category = SelectField('Categoria da Tarefa', coerce=int, validators=[Optional()])
    status = SelectField('Status da Tarefa', coerce=int, validators=[DataRequired()])

    event = HiddenField() # Para passar o objeto do evento para a validação

    submit = SubmitField('Salvar Tarefa')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # Popula as escolhas dinamicamente
        self.assignees.choices = [(user.id, user.username) for user in get_users()]
        # Adiciona a opção padrão (vazia) para o SelectField de categoria de tarefa
        task_category_choices = [(tc.id, tc.name) for tc in get_task_categories()]
        self.task_category.choices = [(0, "-- Selecione uma Categoria de Tarefa (Opcional) --")] + task_category_choices

        self.status.choices = [(s.id, s.name) for s in get_task_statuses()]

    # A validação `validate_assignees` pode ser removida ou mantida dependendo se você
    # precisa de validação extra além do `DataRequired()` se o campo for obrigatório.
    # Por exemplo, se o campo não é obrigatório e nenhum usuário for selecionado,
    # não há problema, então esta função é redundante se `DataRequired` não estiver lá.
    def validate_assignees(self, field):
        if not field.data:
            # Caso o campo não seja obrigatório e não haja seleção, não faz nada.
            # Se for obrigatório, adicione DataRequired() no campo 'assignees' acima.
            pass

class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[Optional()])
    confirm_password = PasswordField('Confirmar Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    role_obj = SelectField('Papel do Usuário', coerce=lambda x: Role.query.get(int(x)), validators=[DataRequired()])
    submit = SubmitField('Salvar Usuário')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.is_new_user = kwargs.get('is_new_user', False)
        self.original_username = kwargs.get('original_username')
        self.original_email = kwargs.get('original_email')

        self.role_obj.choices = [(r.id, r.name) for r in get_roles()]

        if not self.is_new_user:
            self.password.validators = [Optional()]
            self.confirm_password.validators = [Optional(), EqualTo('password', message='As senhas devem ser iguais.')]
        else:
            self.password.validators = [DataRequired()]
            self.confirm_password.validators = [DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')]

    def validate_username(self, username):
        if self.original_username and username.data == self.original_username:
            return
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Esse nome de usuário já existe. Por favor, escolha um diferente.')

    def validate_email(self, email):
        if self.original_email and email.data == self.original_email:
            return
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Esse e-mail já existe. Por favor, escolha um diferente.')

class AdminRoleForm(FlaskForm):
    name = StringField('Nome do Papel', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])

    # Permissões de Evento
    can_view_event = BooleanField('Pode Visualizar Eventos')
    can_edit_event = BooleanField('Pode Editar Eventos')
    can_manage_permissions = BooleanField('Pode Gerenciar Permissões de Eventos')
    can_create_event = BooleanField('Pode Criar Eventos')

    # Permissões de Tarefa
    can_create_task = BooleanField('Pode Criar Tarefas')
    can_edit_task = BooleanField('Pode Editar Tarefas')
    can_delete_task = BooleanField('Pode Excluir Tarefas')
    can_complete_task = BooleanField('Pode Concluir Tarefas')
    can_uncomplete_task = BooleanField('Pode Reverter Conclusão de Tarefas')
    can_upload_task_audio = BooleanField('Pode Fazer Upload de Áudio em Tarefas')
    can_delete_task_audio = BooleanField('Pode Excluir Áudio de Tarefas')
    can_view_task_history = BooleanField('Pode Visualizar Histórico de Tarefas')
    can_manage_task_comments = BooleanField('Pode Gerenciar Comentários em Tarefas')

    # --- NOVO: Permissões de anexo (ADICIONADO AQUI) ---
    can_upload_attachments = BooleanField('Pode Fazer Upload de Anexos em Tarefas')
    can_manage_attachments = BooleanField('Pode Gerenciar (Excluir) Anexos em Tarefas')
    # --- FIM NOVO ---

    submit = SubmitField('Salvar Papel')

    # --- REMOVIDO: validate_name para AdminRoleForm, pois a validação de unicidade
    #              já é tratada no `on_model_change` da `RoleAdminView` em `app.py`.
    #              Isso resolve o `AttributeError: 'AdminRoleForm' object has no attribute 'obj'`.
    # def validate_name(self, name):
    #     if self.obj and self.obj.name == name.data:
    #         return
    #     role = Role.query.filter_by(name=name.data).first()
    #     if role:
    #         raise ValidationError('Este nome de papel já existe. Por favor, escolha um diferente.')


class GroupForm(FlaskForm):
    name = StringField('Nome do Grupo', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Grupo')

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.original_name = kwargs.get('original_name')

    def validate_name(self, name):
        if name.data != self.original_name:
            group = Group.query.filter_by(name=name.data).first()
            if group:
                raise ValidationError('Este nome de grupo já existe. Por favor, escolha um diferente.')

class AssignUsersToGroupForm(FlaskForm):
    users = MultipleCheckboxField('Usuários', coerce=int)
    submit = SubmitField('Atribuir Usuários')

    def __init__(self, *args, **kwargs):
        super(AssignUsersToGroupForm, self).__init__(*args, **kwargs)
        self.users.choices = [(u.id, u.username) for u in User.query.order_by(User.username).all()]

class EventPermissionForm(FlaskForm):
    user = SelectField('Usuário', coerce=int, validators=[DataRequired()])
    # REMOVIDO: group e role fields
    # group = SelectField('Grupo', coerce=int, validators=[Optional()])
    # role = SelectField('Papel de Permissão', coerce=int, validators=[DataRequired()])
    
    event = HiddenField() # Para passar o objeto do evento para a validação
    submit = SubmitField('Adicionar Permissão')

    def __init__(self, *args, **kwargs):
        super(EventPermissionForm, self).__init__(*args, **kwargs)
        
        # --- DEBUG TEMPORÁRIO ---
        all_users = User.query.order_by(User.username).all()
        print(f"DEBUG EventPermissionForm: Encontrados {len(all_users)} usuários.")
        # REMOVIDO: DEBUG para grupos e papéis
        # all_groups = Group.query.order_by(Group.name).all()
        # print(f"DEBUG EventPermissionForm: Encontrados {len(all_groups)} grupos.")
        # all_roles = Role.query.order_by(Role.name).all()
        # print(f"DEBUG EventPermissionForm: Encontrados {len(all_roles)} papéis.")
        # --- FIM DEBUG TEMPORÁRIO ---

        self.user.choices = [(0, "-- Selecione um Usuário --")] + [(u.id, u.username) for u in all_users]
        # REMOVIDO: group.choices e role.choices
        # self.group.choices = [(0, "-- Selecione um Grupo (Opcional) --")] + [(g.id, g.name) for g in all_groups]
        # self.role.choices = [(r.id, r.name) for r in all_roles]

    # --- CORRIGIDO E SIMPLIFICADO: A validação agora só lida com o usuário ---
    def validate(self, extra_validators=None):
        if not super(EventPermissionForm, self).validate(extra_validators=extra_validators):
            return False

        # Verifica se um usuário foi realmente selecionado (DataRequired no campo user já faz isso)
        if self.user.data == 0:
            self.user.errors.append('Por favor, selecione um usuário.')
            return False

        # Validação para evitar permissões duplicadas (usuário já tem permissão para este evento)
        event_id = self.event.data if self.event.data else None
        if event_id:
            existing_permission = db.session.query(EventPermission).filter_by(event_id=event_id, user_id=self.user.data).first()
            
            # self.obj é usado para edições; se não for None, significa que estamos editando uma permissão existente.
            # O objetivo é evitar adicionar uma permissão duplicada, mas permitir a edição da mesma.
            if existing_permission and (not hasattr(self, 'obj') or (hasattr(self, 'obj') and self.obj.id != existing_permission.id)):
                self.user.errors.append('Este usuário já tem uma permissão para este evento.')
                return False

        return True

class SearchForm(FlaskForm):
    query = StringField('Pesquisar', validators=[DataRequired()])
    submit = SubmitField('Buscar')

class CommentForm(FlaskForm):
    content = TextAreaField('Seu Comentário', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('Adicionar Comentário')

# =========================================================================
# NOVO: Formulário para upload de anexos (ADICIONADO AQUI)
# =========================================================================
class AttachmentForm(FlaskForm):
    file = FileField('Selecionar Anexo', validators=[
        DataRequired(message='Por favor, selecione um arquivo.'),
        FileAllowed(['jpg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar'],
                    message='Tipo de arquivo não permitido.')
    ])
    submit = SubmitField('Anexar Arquivo')
# =========================================================================
# FIM NOVO FORMULÁRIO: AttachmentForm
# =========================================================================