from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateField, SelectField, SelectMultipleField, HiddenField, DateTimeField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp, NumberRange
from models import User, Category, Status, TaskCategory, Role, Group, Attachment, EventPermission, \
    TaskSubcategory, ChecklistTemplate, ChecklistItemTemplate, CustomFieldTypeEnum, Task, Event, TaskChecklistItem, TaskAssignment
from extensions import db
from flask_login import current_user
from datetime import date, datetime
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
import json
from sqlalchemy.orm import joinedload

# ==============================================================================
# ==============================================================================
# ESTA É A NOVA FUNÇÃO DE DEPURACÃO - DEVE FICAR AQUI, APÓS OS IMPORTS
# E AGORA ESTÁ CORRETA, RETORNANDO UM OBJETO DE CONSULTA
# ==============================================================================

# Definição do assignees (se precisar de debug específico, use o lambda 'agressivo' temporariamente)
# Mantive a depuração original que estava no seu forms.txt, mas a reestruturei para ser um lambda
# que retorna a consulta de forma correta.
# Ela não será mais 'agressiva' no sentido de forçar um .all(), mas ainda imprime informações.
assignees = QuerySelectMultipleField(
    'Atribuído a',
    query_factory=lambda: (
        # Removi o .all() aqui para o query_factory retornar o objeto de consulta, como deve ser.
        # As impressões agora verificam a query ANTES dela ser executada pelo QuerySelectMultipleField.
        print("\n--- DEBUG_ASSIGNESS_QUERY (LAMBDA RESTRUTURADO) ---"),
        user_query := db.session.query(User),
        print(f"Objeto de consulta de usuários criado (LAMBDA): {user_query}"),
        # NOTA: Não é ideal fazer um .all() aqui dentro do lambda da query_factory,
        # pois o campo fará seu próprio .all(). Esta é apenas para debug extra,
        # para *ver* se a query retorna algo *antes* do campo.
        # Em produção, você removeria esta parte 'test_users'.
        test_users := user_query.all(), # AQUI EXECUTAMOS A QUERY PARA GARANTIR O PRINT E VER O RESULTADO
        (
            print(f"DEBUG: Preview de usuários encontrados (LAMBDA): {[u.username for u in test_users if hasattr(u, 'username')]}")
            if test_users else print("DEBUG: NENHUM usuário encontrado pela query (LAMBDA).")
        ),
        print("--- FIM DEBUG_ASSIGNESS_QUERY (LAMBDA RESTRUTURADO) ---\n"),
        db.session.query(User) # RETORNA O OBJETO DE QUERY ORIGINAL E CORRETO PARA O CAMPO
    )[-1], # Isso seleciona o último elemento da tupla, que é a query real
    get_label='username',
    widget=ListWidget(prefix_label=False),
    option_widget=CheckboxInput(),
    allow_blank=True,
    blank_text='Ninguém Atribuído'
)
# ==============================================================================


# --- Formulários de Usuário e Autenticação ---

class RegistrationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Esse nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Esse email já está registrado. Por favor, escolha outro.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Atualizar Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Atualizar')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Esse nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Esse email já está registrado. Por favor, escolha outro.')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Redefinir Senha')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('Não há conta com esse email. Você deve se registrar primeiro.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Redefinir Senha')

# --- Formulários de Eventos ---

class CategoryForm(FlaskForm):
    name = StringField('Nome da Categoria', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria')

class StatusForm(FlaskForm):
    name = StringField('Nome do Status', validators=[DataRequired(), Length(max=50)])
    type = SelectField('Tipo', choices=[('event', 'Evento'), ('task', 'Tarefa'), ('generic', 'Genérico')], validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Status')

class EventForm(FlaskForm):
    title = StringField('Título do Evento', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrição do Evento', validators=[Optional()])
    due_date = DateTimeField('Data e Hora de Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeField('Data e Hora de Término', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    location = StringField('Localização', validators=[Optional(), Length(max=100)])
    category = QuerySelectField(
        'Categoria',
        query_factory=lambda: db.session.query(Category), # CORRIGIDO: Removido .all()
        get_label=lambda x: x.name,
        allow_blank=True,
        blank_text='Selecione uma Categoria'
    )
    event_status = QuerySelectField(
        'Status do Evento',
        query_factory=lambda: db.session.query(Status).filter_by(type='event'), # CORRIGIDO: Removido .all()
        get_label=lambda x: x.name,
        allow_blank=True,
        blank_text='Selecione um Status'
    )
    submit = SubmitField('Salvar Evento')

    def validate_end_date(self, field):
        if self.due_date.data and field.data and field.data < self.due_date.data:
            raise ValidationError('A data de término não pode ser anterior à data de início.')

# --- Formulários de Administração ---

class AdminRoleForm(FlaskForm):
    name = StringField('Nome do Papel', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    can_view_event = BooleanField('Pode Visualizar Eventos')
    can_edit_event = BooleanField('Pode Editar Eventos')
    can_manage_permissions = BooleanField('Pode Gerenciar Permissões')
    can_create_event = BooleanField('Pode Criar Eventos')
    can_publish_event = BooleanField('Pode Publicar Eventos')
    can_cancel_event = BooleanField('Pode Cancelar Eventos')
    can_duplicate_event = BooleanField('Pode Duplicar Eventos')
    can_view_event_registrations = BooleanField('Pode Visualizar Inscrições de Eventos')
    can_view_event_reports = BooleanField('Pode Visualizar Relatórios de Eventos')
    can_approve_art = BooleanField('Pode Aprovar Arte')
    can_create_task = BooleanField('Pode Criar Tarefas')
    can_edit_task = BooleanField('Pode Editar Tarefas')
    can_delete_task = BooleanField('Pode Excluir Tarefas')
    can_complete_task = BooleanField('Pode Concluir Tarefas')
    can_uncomplete_task = BooleanField('Pode Desmarcar Tarefas como Concluídas')
    can_upload_task_audio = BooleanField('Pode Fazer Upload de Áudio da Tarefa')
    can_delete_task_audio = BooleanField('Pode Excluir Áudio da Tarefa')
    can_view_task_history = BooleanField('Pode Visualizar Histórico da Tarefa')
    can_manage_task_comments = BooleanField('Pode Gerenciar Comentários da Tarefa')
    can_upload_attachments = BooleanField('Pode Fazer Upload de Anexos')
    can_manage_attachments = BooleanField('Pode Gerenciar Anexos')
    submit = SubmitField('Salvar Papel')


class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha')
    role_obj = QuerySelectField(
        'Papel',
        query_factory=lambda: db.session.query(Role), # CORRIGIDO: Removido .all()
        get_label=lambda x: x.name,
        allow_blank=True,
        blank_text='Nenhum Papel Atribuído'
    )
    is_active_db = BooleanField('Ativo')
    submit = SubmitField('Salvar Usuário')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.is_new_user = getattr(self, 'is_new_user', False)
        self.original_username = getattr(self, 'original_username', None)
        self.original_email = getattr(self, 'original_email', None)

        if self.is_new_user:
            self.password.validators = [DataRequired()]
        else:
            self.password.validators = [Optional()]

    def validate_username(self, username):
        if self.is_new_user or (self.original_username and username.data != self.original_username):
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Esse nome de usuário já está em uso. Por favor, escolha outro.')

    def validate_email(self, email):
        if self.is_new_user or (self.original_email and email.data != self.original_email):
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Esse email já está registrado. Por favor, escolha outro.')


class GroupForm(FlaskForm):
    name = StringField('Nome do Grupo', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Salvar Grupo')

class AssignUsersToGroupForm(FlaskForm):
    # Este campo usa SelectMultipleField com choices, que espera uma lista. Está correto.
    users = SelectMultipleField('Usuários', coerce=int, validators=[DataRequired()], widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    submit = SubmitField('Atribuir Usuários')

    def __init__(self, *args, **kwargs):
        super(AssignUsersToGroupForm, self).__init__(*args, **kwargs)
        self.users.choices = [(user.id, user.username) for user in User.query.order_by(User.username).all()] # Aqui .all() é necessário.

class EventPermissionForm(FlaskForm):
    event = QuerySelectField(
        'Evento',
        query_factory=lambda: db.session.query(Event), # CORRIGIDO: Removido .all()
        get_label='title',
        validators=[DataRequired()]
    )
    user = QuerySelectField(
        'Usuário',
        query_factory=lambda: db.session.query(User), # CORRIGIDO: Removido .all()
        get_label='username',
        validators=[DataRequired()]
    )
    submit = SubmitField('Salvar Permissão')

# --- Formulários de Tarefas ---

class TaskCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria de Tarefa', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar Categoria de Tarefa')

class TaskSubcategoryForm(FlaskForm):
    name = StringField('Nome da Subcategoria', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    parent_category = QuerySelectField(
        'Categoria Pai',
        query_factory=lambda: db.session.query(TaskCategory), # CORRIGIDO: Removido .all()
        get_label='name',
        validators=[DataRequired()]
    )
    checklist_template = QuerySelectField(
        'Template de Checklist Associado',
        query_factory=lambda: db.session.query(ChecklistTemplate), # CORRIGIDO: Removido .all()
        get_label='name',
        allow_blank=True,
        blank_text='Nenhum Template'
    )
    requires_art_approval_on_images = BooleanField('Requer aprovação de arte em imagens')
    submit = SubmitField('Salvar Subcategoria')


class CustomFieldTypeEnumField(SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = [(member.name, member.value) for member in CustomFieldTypeEnum]


class ChecklistTemplateForm(FlaskForm):
    name = StringField('Nome do Template', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Salvar Template')

class ChecklistItemTemplateForm(FlaskForm):
    label = StringField('Etiqueta do Item', validators=[DataRequired(), Length(max=255)])
    field_type = CustomFieldTypeEnumField('Tipo de Campo', validators=[DataRequired()])
    is_required = BooleanField('É Obrigatório?')
    order = IntegerField('Ordem', validators=[DataRequired(), NumberRange(min=0)])
    min_images = IntegerField('Mínimo de Imagens', validators=[Optional(), NumberRange(min=0)])
    max_images = IntegerField('Máximo de Imagens', validators=[Optional(), NumberRange(min=0)])
    options = TextAreaField('Options (para Select/Radio, JSON formatado)', validators=[Optional()])
    placeholder = StringField('Placeholder', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Salvar Item do Template')

    def validate_options(self, field):
        if field.data:
            try:
                json.loads(field.data)
            except json.JSONDecodeError:
                raise ValidationError('As opções devem ser um JSON válido.')

    def validate_max_images(self, field):
        if self.min_images.data is not None and field.data is not None and field.data < self.min_images.data:
            raise ValidationError('O máximo de imagens não pode ser menor que o mínimo de imagens.')


class TaskForm(FlaskForm):
    title = StringField('Título da Tarefa', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Descrição', validators=[Optional()])
    notes = TextAreaField('Notas Internas', validators=[Optional()])

    due_date = DateTimeField(
        'Data de Vencimento',
        format='%d/%m/%Y %H:%M',
        validators=[DataRequired()]
    )

    cloud_storage_link = StringField('Link para Armazenamento na Nuvem', validators=[Optional(), Length(max=255)])
    link_notes = TextAreaField('Notas do Link', validators=[Optional()])
    audio_path = StringField('Caminho do Áudio', validators=[Optional(), Length(max=255)])
    audio_duration_seconds = IntegerField('Duração do Áudio (segundos)', validators=[Optional(), NumberRange(min=0)])

    event = QuerySelectField(
        'Evento Associado',
        query_factory=lambda: db.session.query(Event), # CORRIGIDO: Removido .all()
        get_label='title',
        allow_blank=True,
        blank_text='Nenhum Evento'
    )
    task_category = QuerySelectField(
        'Categoria da Tarefa',
        query_factory=lambda: db.session.query(TaskCategory), # CORRIGIDO: Removido .all()
        get_label='name',
        validators=[DataRequired()]
    )
    task_subcategory = QuerySelectField(
        'Subcategoria da Tarefa',
        query_factory=lambda: db.session.query(TaskSubcategory), # CORRIGIDO: Removido .all()
        get_label='name',
        allow_blank=True,
        blank_text='Nenhuma Subcategoria'
    )
    task_status_rel = QuerySelectField(
        'Status da Tarefa',
        query_factory=lambda: db.session.query(Status).filter_by(type='task'), # CORRIGIDO: Removido .all()
        get_label='name',
        validators=[DataRequired()]
    )

    kanban_status_id_hidden = HiddenField() # Campo oculto para ser preenchido via JavaScript no Kanban

    assignees = QuerySelectMultipleField(
        'Atribuído a',
        query_factory=lambda: db.session.query(User), # Retorna a query de usuários
        get_label='username',
        # Removido widget=ListWidget(prefix_label=False) e option_widget=CheckboxInput()
        # para que o campo seja renderizado como um <select multiple> por padrão.
        # Adicionado render_kw para o placeholder do Select2 e classes CSS
        render_kw={"class": "select2-multiple", "data-placeholder": "Selecione os usuários atribuídos"},
        allow_blank=True # Mantemos isso, embora Select2 lide com o placeholder.
    )

    priority = SelectField('Prioridade', choices=[
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
        ('urgent', 'Urgente')
    ], validators=[DataRequired()], default='medium')

    is_completed = BooleanField('Tarefa Concluída')
    completed_at = DateTimeField(
        'Concluída em',
        format='%Y-%m-%dT%H:%M',
        validators=[Optional()]
    )
    completed_by_user_obj = QuerySelectField(
        'Concluída por',
        query_factory=lambda: db.session.query(User), # CORRIGIDO: Removido .all()
        get_label='username',
        allow_blank=True,
        blank_text='Ninguém'
    )
    creator_id = HiddenField('ID do Criador')
    submit = SubmitField('Salvar Tarefa')


# --- Formulário de Comentários ---

class CommentForm(FlaskForm):
    content = TextAreaField('Comentário', validators=[DataRequired(), Length(min=1, max=1000)])
    task = QuerySelectField(
        'Tarefa',
        query_factory=lambda: db.session.query(Task), # CORRIGIDO: Removido .all()
        get_label='title',
        validators=[DataRequired()]
    )
    author = QuerySelectField(
        'Autor',
        query_factory=lambda: db.session.query(User), # CORRIGIDO: Removido .all()
        get_label='username',
        validators=[DataRequired()]
    )
    submit = SubmitField('Adicionar Comentário')


# --- Formulário de Pesquisa ---

class SearchForm(FlaskForm):
    search_query = StringField('Pesquisar', validators=[DataRequired()])
    submit = SubmitField('Pesquisar')


# --- Formulário de Anexo (AttachmentForm) ---

class AttachmentForm(FlaskForm):
    filename = StringField('Nome do Arquivo', validators=[DataRequired(), Length(min=2, max=100)])
    unique_filename = StringField('Nome Único do Arquivo', validators=[DataRequired(), Length(max=120)], render_kw={'readonly': True})
    storage_path = StringField('Caminho de Armazenamento', validators=[DataRequired(), Length(max=200)], render_kw={'readonly': True})
    mimetype = StringField('Tipo MIME', validators=[Optional(), Length(max=50)], render_kw={'readonly': True})
    filesize = IntegerField('Tamanho do Arquivo (bytes)', validators=[Optional(), NumberRange(min=0)], render_kw={'readonly': True})
    uploaded_at = DateTimeField('Data/Hora Upload', format='%Y-%m-%dT%H:%M:%S', validators=[DataRequired()], render_kw={'readonly': True})

    file = FileField('Upload de Arquivo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar', 'mp3', 'mp4'], 'Tipos de arquivo não permitidos!')
    ])

    task = QuerySelectField(
        'Tarefa Associada',
        query_factory=lambda: db.session.query(Task), # CORRIGIDO: Removido .all()
        get_label=lambda t: f'{t.title} (Evento: {t.event.title})' if t.event else t.title,
        allow_blank=True,
        blank_text='Nenhuma Tarefa'
    )
    event = QuerySelectField(
        'Evento Associado',
        query_factory=lambda: db.session.query(Event), # CORRIGIDO: Removido .all()
        get_label=lambda e: e.title,
        allow_blank=True,
        blank_text='Nenhum Evento'
    )
    uploader = QuerySelectField(
        'Enviado por',
        query_factory=lambda: db.session.query(User), # CORRIGIDO: Removido .all()
        get_label=lambda u: u.username,
        allow_blank=True,
        blank_text='Usuário Desconhecido'
    )
    art_approved_by = QuerySelectField(
        'Aprovado por',
        query_factory=lambda: db.session.query(User), # CORRIGIDO: Removido .all()
        get_label=lambda u: u.username,
        allow_blank=True,
        blank_text='Ninguém'
    )
    task_checklist_item = QuerySelectField(
        'Item de Checklist da Tarefa',
        # CORRIGIDO: Removido .all(). O joinedload é uma otimização do SQLAlchemy e deve permanecer.
        query_factory=lambda: db.session.query(TaskChecklistItem).options(joinedload(TaskChecklistItem.checklist_item_template)),
        get_label=lambda item: item.custom_label or (item.checklist_item_template.label if item.checklist_item_template else f'Item {item.id} (Sem Template)'),
        allow_blank=True,
        blank_text='Nenhum Item de Checklist'
    )

    art_approval_status = SelectField(
        'Status Aprovação Arte',
        choices=[
            ('not_required', 'Não Obrigatório'),
            ('pending', 'Pendente'),
            ('approved', 'Aprovado'),
            ('rejected', 'Reprovado')
        ],
        coerce=str,
        validators=[DataRequired()]
    )
    art_feedback = TextAreaField('Feedback da Arte', validators=[Optional(), Length(max=500)])
    art_approval_timestamp = DateTimeField('Data/Hora Aprovação Arte', format='%Y-%m-%dT%H:%M:%S', validators=[Optional()], render_kw={'readonly': True})
    submit = SubmitField('Salvar Anexo')