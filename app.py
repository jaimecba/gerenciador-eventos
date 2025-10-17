# C:\gerenciador-eventos\app.py
from flask import Flask, render_template, url_for, flash, redirect, request, abort, jsonify, send_from_directory
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.babel import gettext
from dotenv import load_dotenv
import os
import secrets
from datetime import datetime, timedelta, date
from uuid import uuid4
import json
import base64
import requests
import re
from markupsafe import Markup, escape
from sqlalchemy.orm import joinedload # ADICIONADO: Importado para usar em Flask-Admin QuerySelectField options

# Importações de WTForms para CustomFieldTypeEnumField e para o formulário customizado
from wtforms import Field, widgets, Form, DateTimeField, SelectField # ADICIONADO Form e DateTimeField

# Importações dos modelos e extensões
from extensions import db, login_manager
from models import User, Event, Category, Status, TaskCategory, Role, Group, UserGroup, EventPermission,\
    Task, TaskAssignment, TaskHistory, ChangeLogEntry, PasswordResetToken, Attachment,\
    Notification, PushSubscription, TaskSubcategory, ChecklistTemplate, ChecklistItemTemplate, Comment, CustomFieldTypeEnum, \
    TaskChecklist, TaskChecklistItem

# Importa o Blueprint 'main' do seu arquivo routes.py
from routes import main as main_blueprint

# Importações dos forms
from forms import RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm,\
    EventForm, CategoryForm, StatusForm, TaskCategoryForm, UserForm, AdminRoleForm, GroupForm,\
    AssignUsersToGroupForm, EventPermissionForm, SearchForm, CommentForm, AttachmentForm,\
    TaskSubcategoryForm, ChecklistTemplateForm, ChecklistItemTemplateForm, TaskForm

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Instanciação do bcrypt
bcrypt = Bcrypt()

# Instanciação do mail
mail = Mail()


# =========================================================================
# FLASK-ADMIN CUSTOM VIEWS
# =========================================================================

class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('main.login', next=request.url))


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.login', next=request.url))
        return self.render('admin/index.html')


class UserAdminView(AuthenticatedModelView):
    column_list = ('id', 'username', 'email', 'role_obj', 'is_active_db', 'created_at')
    column_searchable_list = ('username', 'email')
    column_filters = ('is_active_db', 'role_obj.name')
    column_editable_list = ('is_active_db',)
    form_create_rules = ('username', 'email', 'password_hash', 'role_obj', 'is_active_db')
    form_edit_rules = ('username', 'email', 'role_obj', 'is_active_db')
    form = UserForm

    def create_form(self, obj=None):
        form = super(UserAdminView, self).create_form(obj)
        form.is_new_user = True
        return form

    def edit_form(self, obj=None):
        form = super(UserAdminView, self).edit_form(obj)
        form.original_username = obj.username
        form.original_email = obj.email
        form.is_new_user = False
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            if form.password.data:
                model.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            ChangeLogEntry.log_creation(
                current_user.id, 'User', model.id,
                {'username': model.username, 'email': model.email},
                f'Usuário {model.username} foi criado.'
            )
        else: # Update
            if form.password.data:
                model.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

            old_data = {
                'username': form.original_username,
                'email': form.original_email
            }
            new_data = {
                'username': model.username,
                'email': model.email
            }
            ChangeLogEntry.log_update(
                current_user.id, 'User', model.id,
                old_data,
                new_data,
                f'Usuário {model.username} foi atualizado.'
            )
        model.updated_at = datetime.utcnow()


class RoleAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'can_view_event', 'can_edit_event', 'can_manage_permissions', 'can_create_event', 'can_publish_event', 'can_cancel_event', 'can_duplicate_event', 'can_view_event_registrations', 'can_view_event_reports', 'can_approve_art', 'can_create_task', 'can_edit_task', 'can_delete_task', 'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio', 'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments', 'can_upload_attachments', 'can_manage_attachments')
    form_columns = ('name', 'description', 'can_view_event', 'can_edit_event', 'can_manage_permissions', 'can_create_event', 'can_publish_event', 'can_cancel_event', 'can_duplicate_event', 'can_view_event_registrations', 'can_view_event_reports', 'can_approve_art', 'can_create_task', 'can_edit_task', 'can_delete_task', 'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio', 'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments', 'can_upload_attachments', 'can_manage_attachments')
    column_searchable_list = ('name',)
    column_editable_list = ('can_view_event', 'can_edit_event', 'can_manage_permissions', 'can_create_event', 'can_publish_event', 'can_cancel_event', 'can_duplicate_event', 'can_view_event_registrations', 'can_view_event_reports', 'can_approve_art', 'can_create_task', 'can_edit_task', 'can_delete_task', 'can_complete_task', 'can_uncomplete_task', 'can_upload_task_audio', 'can_delete_task_audio', 'can_view_task_history', 'can_manage_task_comments', 'can_upload_attachments', 'can_manage_attachments')
    form = AdminRoleForm

    def edit_form(self, obj=None):
        form = super(RoleAdminView, self).edit_form(obj)
        form.original_name = obj.name
        form.original_description = obj.description
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Role', model.id,
                {'name': model.name, 'description': model.description},
                f'Papel {model.name} foi criado.'
            )
        else: # Update
            old_data = {
                'name': form.original_name,
                'description': form.original_description
            }
            new_data = {
                'name': model.name,
                'description': model.description
            }
            ChangeLogEntry.log_update(
                current_user.id, 'Role', model.id,
                old_data,
                new_data,
                f'Papel {model.name} foi atualizado.'
            )


class CategoryAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'created_at', 'updated_at')
    column_searchable_list = ('name',)
    column_filters = ('created_at', 'updated_at')
    form = CategoryForm

    def create_form(self, obj=None):
        form = super(CategoryAdminView, self).create_form(obj)
        form.original_name = None
        return form

    def edit_form(self, obj=None):
        form = super(CategoryAdminView, self).edit_form(obj)
        form.original_name = obj.name
        return form

    def on_model_change(self, form, model, is_created):
        model.updated_at = datetime.utcnow()
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Category', model.id,
                {'name': model.name, 'description': model.description},
                f'Categoria {model.name} foi criada.'
            )
        else: # Update
            old_data = {'name': form.original_name}
            new_data = {'name': model.name}
            ChangeLogEntry.log_update(
                current_user.id, 'Category', model.id,
                old_data,
                new_data,
                f'Categoria {model.name} foi atualizada.'
            )


class StatusAdminView(AuthenticatedModelView):
    column_list = ('name', 'type', 'description')
    column_searchable_list = ('name', 'type')
    column_filters = ('type',)
    form = StatusForm

    def create_form(self, obj=None):
        form = super(StatusAdminView, self).create_form(obj)
        form.original_name = None
        form.original_type = None
        return form

    def edit_form(self, obj=None):
        form = super(StatusAdminView, self).edit_form(obj)
        form.original_name = obj.name
        form.original_type = obj.type
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Status', model.id,
                {'name': model.name, 'type': model.type, 'description': model.description},
                f'Status {model.name} ({model.type}) foi criado.'
            )
        else: # Update
            old_data = {'name': form.original_name, 'type': form.original_type}
            new_data = {'name': model.name, 'type': model.type}
            ChangeLogEntry.log_update(
                current_user.id, 'Status', model.id,
                old_data,
                new_data,
                f'Status {model.name} ({model.type}) foi atualizado.'
            )


class TaskCategoryAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'created_at', 'updated_at')
    column_searchable_list = ('name',)
    column_filters = ('created_at',)
    form = TaskCategoryForm

    def create_form(self, obj=None):
        form = super(TaskCategoryAdminView, self).create_form(obj)
        form.original_name = None
        return form

    def edit_form(self, obj=None):
        form = super(TaskCategoryAdminView, self).edit_form(obj)
        form.original_name = obj.name
        return form

    def on_model_change(self, form, model, is_created):
        model.updated_at = datetime.utcnow()
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'TaskCategory', model.id,
                {'name': model.name, 'description': model.description},
                f'Categoria de Tarefa {model.name} foi criada.'
            )
        else: # Update
            old_data = {'name': form.original_name}
            new_data = {'name': model.name}
            ChangeLogEntry.log_update(
                current_user.id, 'TaskCategory', model.id,
                old_data,
                new_data,
                f'Categoria de Tarefa {model.name} foi atualizada.'
            )


class TaskSubcategoryAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'parent_category', 'requires_art_approval_on_images', 'checklist_template')
    column_searchable_list = ('name', 'description')
    column_filters = ('parent_category.name', 'requires_art_approval_on_images')
    form = TaskSubcategoryForm

    def edit_form(self, obj=None):
        form = super(TaskSubcategoryAdminView, self).edit_form(obj)
        form.original_name = obj.name
        form.original_parent_category_id = obj.task_category_id
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'TaskSubcategory', model.id,
                {'name': model.name, 'parent_category': model.parent_category.name if model.parent_category else 'N/A'},
                f'Subcategoria de Tarefa {model.name} foi criada.'
            )
        else: # Update
            old_data = {
                'name': form.original_name,
                'parent_category_id': form.original_parent_category_id
            }
            new_data = {
                'name': model.name,
                'parent_category_id': model.task_category_id,
                'parent_category': model.parent_category.name if model.parent_category else 'N/A'
            }
            ChangeLogEntry.log_update(
                current_user.id, 'TaskSubcategory', model.id,
                old_data,
                new_data,
                f'Subcategoria de Tarefa {model.name} foi atualizada.'
            )

# Campo personalizado para lidar com CustomFieldTypeEnum no formulário principal e in-line
class CustomFieldTypeEnumField(QuerySelectField):
    def __init__(self, label=None, validators=None, enum_class=None, **kwargs):
        super(CustomFieldTypeEnumField, self).__init__(
            label=label,
            validators=validators,
            query_factory=lambda: list(enum_class),
            get_pk=lambda a: a.name,
            get_label=lambda a: a.value,
            allow_blank=False,
            **kwargs
        )
        self.enum_class = enum_class

    def _get_data(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data is not None:
            return self.data
        return None

    def process_data(self, value):
        if value is None:
            self.data = None
        else:
            if isinstance(value, self.enum_class):
                self.data = value
            elif isinstance(value, str):
                try:
                    self.data = self.enum_class[value]
                except KeyError:
                    self.data = None
            else:
                self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = self.enum_class[valuelist[0]]
            except KeyError:
                self.data = None
        else:
            self.data = None


class ChecklistTemplateAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'created_at', 'updated_at')
    column_searchable_list = ('name', 'description')
    column_filters = ('created_at', 'updated_at')
    form = ChecklistTemplateForm

    inline_models = [
        (ChecklistItemTemplate, {
            'name': 'Itens do Template de Checklist',
            'form_columns': (
                'label', 'field_type', 'is_required', 'order',
                'min_images', 'max_images', 'options', 'placeholder'
            ),
            'form_extra_fields': {
                'field_type': CustomFieldTypeEnumField(
                    'Tipo de Campo',
                    enum_class=CustomFieldTypeEnum,
                    coerce=lambda x: CustomFieldTypeEnum[x] if isinstance(x, str) else x
                ),
            },
            'column_list': ('label', 'field_type', 'is_required', 'order'),
            'column_labels': {
                'field_type': 'Tipo de Campo'
            }
        })
    ]

    def edit_form(self, obj=None):
        form = super(ChecklistTemplateAdminView, self).edit_form(obj)
        form.original_name = obj.name
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'ChecklistTemplate', model.id,
                {'name': model.name, 'description': model.description},
                f'Template de Checklist {model.name} foi criado.'
            )
        else: # Update
            old_data = {'name': form.original_name}
            new_data = {'name': model.name}
            ChangeLogEntry.log_update(
                current_user.id, 'ChecklistTemplate', model.id,
                old_data,
                new_data,
                f'Template de Checklist {model.name} foi atualizado.'
            )


class ChecklistItemTemplateAdminView(AuthenticatedModelView):
    column_list = ('template', 'label', 'field_type', 'is_required', 'order', 'min_images', 'max_images', 'options', 'placeholder')
    column_searchable_list = ('label',)
    column_filters = ('template.name', 'field_type', 'is_required')
    form = ChecklistItemTemplateForm

    form_extra_fields = {
        'field_type': CustomFieldTypeEnumField(
            'Tipo de Campo',
            enum_class=CustomFieldTypeEnum,
            coerce=lambda x: CustomFieldTypeEnum[x] if isinstance(x, str) else x
        ),
    }

    def edit_form(self, obj=None):
        form = super(ChecklistItemTemplateAdminView, self).edit_form(obj)
        form.original_label = obj.label
        form.original_field_type = obj.field_type.name if obj.field_type else None
        return form

    def create_model(self, form):
        try:
            model = self.model()
            form.populate_obj(model)
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
            return True
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Falha ao criar registro. %(error)s', error=str(ex)), 'error')
            self.session.rollback()
            return False

    def update_model(self, form, model):
        try:
            form.populate_obj(model)
            self._on_model_change(form, model, False)
            self.session.commit()
            return True
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Falha ao atualizar registro. %(error)s', error=str(ex)), 'error')
            self.session.rollback()
            return False

    def on_model_change(self, form, model, is_created):
        field_type_for_log = model.field_type.name if isinstance(model.field_type, CustomFieldTypeEnum) else str(model.field_type)

        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'ChecklistItemTemplate', model.id,
                {'label': model.label, 'field_type': field_type_for_log},
                f'Item de Template de Checklist "{model.label}" (Template: {model.template.name if model.template else "N/A"}) foi criado.'
            )
        else: # Update
            old_data = {'label': form.original_label, 'field_type': field_type_for_log} # Fix for original_field_type if it was not enum
            new_data = {'label': model.label, 'field_type': field_type_for_log}
            ChangeLogEntry.log_update(
                current_user.id, 'ChecklistItemTemplate', model.id,
                old_data,
                new_data,
                f'Item de Template de Checklist "{model.label}" (Template: {model.template.name if model.template else "N/A"}) foi atualizado.'
            )


class GroupAdminView(AuthenticatedModelView):
    column_list = ('name', 'description', 'created_at', 'updated_at')
    column_searchable_list = ('name',)
    column_filters = ('created_at',)
    form = GroupForm

    def create_form(self, obj=None):
        form = super(GroupAdminView, self).create_form(obj)
        form.original_name = None
        return form

    def edit_form(self, obj=None):
        form = super(GroupAdminView, self).edit_form(obj)
        form.original_name = obj.name
        return form

    def on_model_change(self, form, model, is_created):
        model.updated_at = datetime.utcnow()
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Group', model.id,
                {'name': model.name, 'description': model.description},
                f'Grupo {model.name} foi criado.'
            )
        else: # Update
            old_data = {'name': form.original_name}
            new_data = {'name': model.name}
            ChangeLogEntry.log_update(
                current_user.id, 'Group', model.id,
                old_data,
                new_data,
                f'Grupo {model.name} foi atualizado.'
            )


class ChangeLogAdminView(AuthenticatedModelView):
    column_list = ('timestamp', 'action', 'record_type', 'record_id', 'user_associated_with_log', 'description')
    column_sortable_list = ('timestamp', 'action', 'record_type')
    column_searchable_list = ('action', 'record_type', 'description')
    column_filters = ('action', 'record_type', 'user_associated_with_log.username')
    can_create = False
    can_edit = False
    can_delete = True
    column_formatters = {
        'old_data': lambda v, c, m, p: m.old_data_dict if m.old_data else {},
        'new_data': lambda v, c, m, p: m.new_data_dict if m.new_data else {},
    }


class NotificationAdminView(AuthenticatedModelView):
    column_list = ('timestamp', 'user', 'message', 'is_read', 'link_url', 'related_object_type', 'related_object_id')
    column_searchable_list = ('message', 'user.username', 'related_object_type')
    column_filters = ('is_read', 'user.username', 'related_object_type')
    can_create = False
    can_edit = True
    can_delete = True


class PushSubscriptionAdminView(AuthenticatedModelView):
    column_list = ('user', 'endpoint', 'timestamp')
    column_searchable_list = ('user.username', 'endpoint')
    column_filters = ('user.username',)
    can_create = False
    can_edit = False
    can_delete = True


class EventAdminView(AuthenticatedModelView):
    column_list = ('title', 'author', 'category', 'event_status', 'due_date', 'end_date', 'location', 'is_published', 'is_cancelled', 'created_at', 'updated_at')
    column_searchable_list = ('title', 'description', 'location')
    column_filters = ('category.name', 'event_status.name', 'author.username', 'is_published', 'is_cancelled')
    
    # AQUI ESTÁ A CORREÇÃO CRÍTICA: Use 'event_status' e não 'status'
    form_columns = ('title', 'description', 'due_date', 'end_date', 'location', 'category', 'event_status', 'author', 'is_published', 'is_cancelled') 

    form_args = {
        'due_date': {'render_kw': {'type': 'datetime-local'}},
        'end_date': {'render_kw': {'type': 'datetime-local'}}
    }

    inline_models = [
        (EventPermission, {
            'name': 'Permissões do Evento',
            'form_columns': ('user',),
            'column_list': ('user',),
            'column_labels': {'user': 'Usuário'}
        })
    ]

    def edit_form(self, obj=None):
        form = super(EventAdminView, self).edit_form(obj)
        form.original_title = obj.title
        return form

    def on_model_change(self, form, model, is_created):
        model.updated_at = datetime.utcnow()
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Event', model.id,
                {'title': model.title, 'event_id': model.id},
                f'Evento "{model.title}" foi criado.'
            )
        else: # Update
            old_data = {'title': form.original_title}
            new_data = {'title': model.title}
            ChangeLogEntry.log_update(
                current_user.id, 'Event', model.id,
                old_data,
                new_data,
                f'Evento "{model.title}" foi atualizado.'
            )


class TaskAdminView(AuthenticatedModelView):
    column_list = ('title', 'event', 'task_category', 'task_subcategory', 'task_status_rel', 'due_date', 'is_completed', 'completed_by_user_obj', 'created_at')
    column_searchable_list = ('title', 'description', 'notes')
    column_filters = ('event.title', 'task_category.name', 'task_subcategory.name', 'task_status_rel.name', 'is_completed', 'completed_by_user_obj.username')
    form_columns = ('title', 'description', 'notes', 'due_date', 'cloud_storage_link', 'link_notes',
                    'audio_path', 'audio_duration_seconds',
                    'event', 'task_category', 'task_subcategory', 'task_status_rel',
                    'is_completed', 'completed_at', 'completed_by_user_obj', 'creator_id')
    form_args = {
        'due_date': {'render_kw': {'type': 'datetime-local'}},
        'completed_at': {'render_kw': {'type': 'datetime-local'}}
    }
    inline_models = [
        (TaskAssignment, {
            'name': 'Atribuições de Tarefa',
            'form_columns': ('user', 'assigned_at'),
            'column_list': ('user', 'assigned_at'),
            'column_labels': {'user': 'Usuário', 'assigned_at': 'Atribuído em'}
        }),
        (TaskHistory, {
            'name': 'Histórico da Tarefa',
            'can_create': False,
            'can_edit': False,
            'form_columns': ('action_type', 'description', 'old_value', 'new_value', 'author', 'timestamp'),
            'column_list': ('action_type', 'description', 'author', 'timestamp'),
            'column_labels': {'action_type': 'Tipo de Ação', 'author': 'Autor'}
        }),
        (Comment, {
            'name': 'Comentários',
            'form_columns': ('content', 'author', 'timestamp'),
            'column_list': ('content', 'author', 'timestamp'),
            'column_labels': {'content': 'Conteúdo', 'author': 'Autor', 'timestamp': 'Data/Hora'}
        })
    ]

    def edit_form(self, obj=None):
        form = super(TaskAdminView, self).edit_form(obj)
        form.original_title = obj.title
        form.original_is_completed = obj.is_completed
        return form

    def on_model_change(self, form, model, is_created):
        model.updated_at = datetime.utcnow()
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Task', model.id,
                {'title': model.title, 'event': model.event.title if model.event else "N/A"},
                f'Tarefa "{model.title}" (Evento: {model.event.title if model.event else "N/A"}) foi criada.'
            )
        else: # Update
            old_data = {'title': form.original_title, 'is_completed': form.original_is_completed}
            new_data = {'title': model.title, 'event': model.event.title if model.event else "N/A", 'is_completed': model.is_completed}
            ChangeLogEntry.log_update(
                current_user.id, 'Task', model.id,
                old_data,
                new_data,
                f'Tarefa "{model.title}" (Evento: {model.event.title if model.event else "N/A"}) foi atualizada.'
            )
        if not is_created: # Apenas para atualizações
            if 'is_completed' in form and form.is_completed.data and not form.original_is_completed:
                model.completed_at = datetime.utcnow()
                model.completed_by_id = current_user.id
            elif 'is_completed' in form and not form.is_completed.data and form.original_is_completed:
                model.completed_at = None
                model.completed_by_id = None


# --- NOVO: Classe de formulário customizada para TaskChecklist ---
class TaskChecklistForm(Form): # Usamos wtforms.Form para o formulário base
    task = QuerySelectField(
        'Tarefa',
        query_factory=lambda: Task.query.all(), # Importar Task do models
        get_label=lambda t: t.title,
        allow_blank=False,
        blank_text='Selecione uma Tarefa'
    )
    task_subcategory = QuerySelectField(
        'Subcategoria de Tarefa',
        query_factory=lambda: TaskSubcategory.query.all(), # Importar TaskSubcategory do models
        get_label=lambda ts: ts.name,
        allow_blank=True,
        blank_text='Nenhuma Subcategoria'
    )
    created_at = DateTimeField('Criado em', render_kw={'readonly': True})
    updated_at = DateTimeField('Atualizado em', render_kw={'readonly': True})

# --- FIM NOVO: Classe de formulário customizada ---


class TaskChecklistAdminView(AuthenticatedModelView):
    # Set the custom form class here, overriding scaffolding for the parent view
    form = TaskChecklistForm # <-- AQUI ESTÁ A CORREÇÃO CHAVE

    column_list = ('id', 'task', 'task_subcategory', 'created_at', 'updated_at')
    column_labels = {
        'id': 'ID',
        'task': 'Tarefa',
        'task_subcategory': 'Subcategoria de Tarefa',
        'created_at': 'Criado em',
        'updated_at': 'Atualizado em'
    }
    column_searchable_list = ('task.title', 'task_subcategory.name')
    column_filters = ('task.title', 'task_subcategory.name')

    can_create = False
    can_edit = True
    can_delete = True

    # As seguintes configurações (form_columns, form_excluded_columns, form_overrides, form_args)
    # são ignoradas para a view pai quando 'form' é definido explicitamente.
    # Elas foram removidas para clareza.

    inline_models = [
        (TaskChecklistItem, {
            'name': 'Itens do Checklist da Tarefa',
            'form_columns': (
                'label',
                'custom_label',
                'custom_field_type',
                'is_required',
                'order',
                'value_text',
                'value_date',
                'value_time',
                'value_datetime',
                'value_number',
                'value_boolean',
                'is_completed',
                'completed_at',
                'completed_by_user_rel'
            ),
            'form_extra_fields': {
                'custom_field_type': CustomFieldTypeEnumField(
                    'Tipo de Campo Personalizado',
                    enum_class=CustomFieldTypeEnum,
                    coerce=lambda x: CustomFieldTypeEnum[x] if isinstance(x, str) else x
                ),
            },
            'column_list': ('label', 'custom_field_type', 'is_completed', 'order'),
            'column_labels': {
                'custom_field_type': 'Tipo de Campo',
                'completed_by_user_rel': 'Concluído por',
            }
        })
    ]

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'TaskChecklist', model.id,
                {'task_id': model.task_id, 'subcategory_id': model.task_subcategory_id},
                f'Checklist para a Tarefa "{model.task.title}" foi criado.'
            )
        else:
            ChangeLogEntry.log_update(
                current_user.id, 'TaskChecklist', model.id,
                {'task_id': form.task.data.id, 'subcategory_id': form.task_subcategory.data.id if form.task_subcategory.data else None},
                {'task_id': model.task.id, 'subcategory_id': model.task_subcategory.id if model.task_subcategory else None},
                f'Checklist para a Tarefa "{model.task.title}" foi atualizado.'
            )
        model.updated_at = datetime.utcnow()


# === NOVA CLASSE: AttachmentAdmin (Corrigida e Reforçada) ===
class AttachmentAdmin(AuthenticatedModelView):
    column_list = (
        'id', 'filename', 'mimetype', 'filesize', 'task', 'event',
        'uploader',
        'uploaded_at',
        'art_approval_status',
        'art_approved_by', 'art_approval_timestamp', 'task_checklist_item', 'public_url'
    )
    column_labels = {
        'id': 'ID',
        'filename': 'Nome do Arquivo',
        'mimetype': 'Tipo MIME',
        'filesize': 'Tamanho (bytes)',
        'task': 'Tarefa Associada',
        'event': 'Evento Associado',
        'uploader': 'Enviado por',
        'uploaded_at': 'Data/Hora Upload',
        'art_approval_status': 'Status Aprovação Arte',
        'art_approved_by': 'Aprovado por',
        'art_approval_timestamp': 'Data/Hora Aprovação',
        'task_checklist_item': 'Item de Checklist',
        'public_url': 'Link Público'
    }

    column_searchable_list = ('filename', 'unique_filename', 'mimetype', 'art_approval_status')
    column_filters = (
        'task.title', 'event.title', 'uploader.username',
        'art_approval_status', 'art_approved_by.username', 'uploaded_at'
    )

    can_create = False
    can_edit = True
    can_delete = True

    column_formatters = {
        'public_url': lambda v, c, m, p: Markup(f'<a href="{url_for("main.serve_attachment_file", filename=m.unique_filename)}" >Download</a>') if m.unique_filename else ''
    }

    # === AQUI A CORREÇÃO CRÍTICA: Definir explicitamente o formulário a ser usado ===
    form = AttachmentForm

    # --- REMOVIDO: form_columns, form_overrides, form_args ---
    # Ao definir 'form = AttachmentForm', Flask-Admin usará seu formulário WTForms
    # customizado e ignorará as configurações de scaffolding automático (form_columns,
    # form_overrides, form_args) para a geração do formulário de edição/criação.
    # Elas seriam redundantes e poderiam causar conflitos.

    def edit_form(self, obj=None):
        form = super(AttachmentAdmin, self).edit_form(obj)
        if obj:
            # 'original_art_approval_status' é usado em on_model_change
            # Certifique-se de que o formulário é populado com os dados do objeto.
            # A chamada super().edit_form(obj) geralmente cuida disso.
            form.original_art_approval_status = obj.art_approval_status
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Attachment', model.id,
                {'filename': model.filename, 'status': model.art_approval_status},
                f'Anexo "{model.filename}" (ID: {model.id}) foi criado. Status de aprovação: {model.art_approval_status}.'
            )
        else: # Update
            old_data = {'status': form.original_art_approval_status}
            new_data = {'status': model.art_approval_status, 'feedback': model.art_feedback}
            ChangeLogEntry.log_update(
                current_user.id, 'Attachment', model.id,
                old_data,
                new_data,
                f'Anexo "{model.filename}" (ID: {model.id}) foi atualizado. Status de aprovação: {model.art_approval_status}.'
            )
        if not is_created and hasattr(form, 'art_approval_status') and hasattr(form, 'original_art_approval_status') and form.art_approval_status.data != form.original_art_approval_status:
            model.art_approved_by_id = current_user.id
            model.art_approval_timestamp = datetime.utcnow()
# === FIM DA CLASSE AttachmentAdmin CORRIGIDA ===


class CommentAdminView(AuthenticatedModelView):
    column_list = ('content', 'author', 'task', 'timestamp')
    column_searchable_list = ('content', 'author.username')
    column_filters = ('author.username', 'task.title', 'timestamp')
    can_create = False
    can_edit = True
    can_delete = True
    form_columns = ('content', 'author', 'task')

    def edit_form(self, obj=None):
        form = super(CommentAdminView, self).edit_form(obj)
        form.original_content = obj.content
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'Comment', model.id,
                {'content': model.content, 'task': model.task.title if model.task else 'N/A'},
                f'Comentário (ID: {model.id}) para Tarefa "{model.task.title}" foi criado.'
            )
        else: # Update
            old_data = {'content': form.original_content}
            new_data = {'content': model.content}
            ChangeLogEntry.log_update(
                current_user.id, 'Comment', model.id,
                old_data,
                new_data,
                f'Comentário (ID: {model.id}) para Tarefa "{model.task.title}" foi atualizado.'
            )


class EventPermissionAdminView(AuthenticatedModelView):
    column_list = ('event', 'user', 'created_at', 'updated_at')
    column_searchable_list = ('event.title', 'user.username')
    column_filters = ('event.title', 'user.username')
    form_columns = ('event', 'user')

    def edit_form(self, obj=None):
        form = super(EventPermissionAdminView, self).edit_form(obj)
        form.original_event_id = obj.event_id
        form.original_user_id = obj.user_id
        return form

    def on_model_change(self, form, model, is_created):
        if is_created:
            ChangeLogEntry.log_creation(
                current_user.id, 'EventPermission', model.id,
                {'event_id': model.event_id, 'user_id': model.user_id},
                f'Permissão de Evento (Evento: {model.event.title if model.event else "N/A"}, Usuário: {model.user.username if model.user else "N/A"}) foi criada.'
            )
        else: # Update
            old_data = {'event_id': form.original_event_id, 'user_id': form.original_user_id}
            new_data = {'event_id': model.event_id, 'user_id': model.user_id}
            ChangeLogEntry.log_update(
                current_user.id, 'EventPermission', model.id,
                old_data,
                new_data,
                f'Permissão de Evento (Evento: {model.event.title if model.event else "N/A"}, Usuário: {model.user.username if model.user else "N/A"}) foi atualizada.'
            )


# =========================================================================
# FLASK APP FACTORY
# =========================================================================
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configurações de Email
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    # Configurações de VAPID para WebPush
    app.config['VAPID_PUBLIC_KEY'] = os.environ.get('VAPID_PUBLIC_KEY')
    app.config['VAPID_PRIVATE_KEY'] = os.environ.get('VAPID_PRIVATE_KEY')
    app.config['VAPID_CLAIMS'] = {'sub': os.environ.get('VAPID_CLAIMS_SUB')}

    # Configurações de pastas para upload (NÃO USAR app.root_path DIRETAMENTE)
    app.config['UPLOAD_FOLDER_AUDIO'] = os.path.join(app.instance_path, 'uploads', 'audio')
    app.config['UPLOAD_FOLDER_ATTACHMENTS'] = os.path.join(app.instance_path, 'uploads', 'attachments')
    os.makedirs(app.config['UPLOAD_FOLDER_AUDIO'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_ATTACHMENTS'], exist_ok=True)

    # --- REGISTRO DO FILTRO CUSTOMIZADO regex_replace ---
    @app.template_filter('regex_replace')
    def regex_replace(s, pattern, replace):
        """Applies a regular expression replacement to a string."""
        if s is None:
            return Markup('')
        return Markup(re.sub(pattern, replace, escape(s)))
    # --- FIM REGISTRO DO FILTRO ---

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)

    # Configurações do Flask-Login
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'

    # Inicialização do Flask-Admin
    admin = Admin(app, name='Gerenciador de Eventos', template_mode='bootstrap3', index_view=MyAdminIndexView())

    # Adicionando Views para os modelos no Admin
    admin.add_view(UserAdminView(User, db.session, name='Usuários', category='Administração'))
    admin.add_view(RoleAdminView(Role, db.session, name='Papéis', category='Administração'))
    admin.add_view(GroupAdminView(Group, db.session, name='Grupos', category='Administração'))
    admin.add_view(ChangeLogAdminView(ChangeLogEntry, db.session, name='Log de Alterações', category='Administração'))
    admin.add_view(NotificationAdminView(Notification, db.session, name='Notificações', category='Administração'))
    admin.add_view(PushSubscriptionAdminView(PushSubscription, db.session, name='Inscrições Push', category='Administração'))
    admin.add_view(EventAdminView(Event, db.session, name='Eventos', category='Eventos e Tarefas'))
    admin.add_view(CategoryAdminView(Category, db.session, name='Categorias de Evento', category='Eventos e Tarefas'))
    admin.add_view(StatusAdminView(Status, db.session, name='Status de Evento/Tarefa', category='Eventos e Tarefas'))
    admin.add_view(TaskAdminView(Task, db.session, name='Tarefas', category='Eventos e Tarefas'))
    # === REGISTRO DA CLASSE TaskChecklistAdminView COM FORMULÁRIO CUSTOMIZADO ===
    admin.add_view(TaskChecklistAdminView(TaskChecklist, db.session, name='Checklists de Tarefa', category='Eventos e Tarefas'))
    # === FIM DO REGISTRO ===
    admin.add_view(TaskCategoryAdminView(TaskCategory, db.session, name='Categorias de Tarefa', category='Eventos e Tarefas'))
    admin.add_view(TaskSubcategoryAdminView(TaskSubcategory, db.session, name='Subcategorias de Tarefa', category='Eventos e Tarefas'))
    admin.add_view(ChecklistTemplateAdminView(ChecklistTemplate, db.session, name='Templates de Checklist', category='Eventos e Tarefas'))
    admin.add_view(ChecklistItemTemplateAdminView(ChecklistItemTemplate, db.session, name='Itens de Template de Checklist', category='Eventos e Tarefas'))
    admin.add_view(AttachmentAdmin(Attachment, db.session, name='Anexos', category='Eventos e Tarefas'))
    admin.add_view(CommentAdminView(Comment, db.session, name='Comentários', category='Eventos e Tarefas'))
    admin.add_view(EventPermissionAdminView(EventPermission, db.session, name='Permissões de Evento', category='Eventos e Tarefas'))

    # =========================================================================
    # REGISTRA O BLUEPRINT 'MAIN' DA SUA APLICAÇÃO
    # =========================================================================
    app.register_blueprint(main_blueprint)

    # Rota raiz que redireciona para a home do Blueprint
    @app.route("/")
    def index_redirect():
        return redirect(url_for('main.home'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
