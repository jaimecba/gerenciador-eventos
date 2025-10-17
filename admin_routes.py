# app/routes/admin_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError # Importar para lidar com erros de unicidade (ex: nome de grupo duplicado)

# Importe os modelos necessários.
# Certifique-se de que estes modelos (Group, User, Event) estão definidos no seu models.py
from models import Group, User, Event

# Importe os formulários que criamos anteriormente
# Certifique-se de que GroupForm, AssignUsersToGroupForm e EventPermissionForm estão no seu forms.py
from forms import GroupForm, AssignUsersToGroupForm, EventPermissionForm

# Importe a instância do SQLAlchemy.
# Certifique-se de que 'extensions.py' configura corretamente a sua variável 'db'
from extensions import db

# ----------------------------------------------------------------------
# 1. Criação do Blueprint 'admin_bp'
# ----------------------------------------------------------------------
# Um Blueprint ajuda a organizar seu código, agrupando rotas, templates, etc.
# 'admin_bp' é o nome do Blueprint.
# '__name__' é o nome do módulo Python atual.
# 'template_folder' aponta para onde os templates HTML específicos deste Blueprint serão procurados.
#   Neste caso, ele procura em 'seu_projeto/templates/admin/' (subindo dois diretórios do 'app/routes').
# 'url_prefix' adiciona um prefixo a todas as URLs definidas neste Blueprint.
#   Ex: '/groups' dentro deste Blueprint se tornará '/admin/groups'.

# CORRIGIDO AQUI: O nome do blueprint foi alterado de 'admin' para 'custom_admin'
admin_bp = Blueprint('custom_admin', __name__, template_folder='../../templates/admin', url_prefix='/admin')


# ----------------------------------------------------------------------
# 2. Decorador de Permissão de Administrador
# ----------------------------------------------------------------------
# Este decorador será usado para proteger as rotas administrativas,
# garantindo que apenas usuários com a função de 'admin' possam acessá-las.
def admin_required(f):
    @login_required # Garante que o usuário esteja logado
    def wrap(*args, **kwargs):
        # Verifica se o usuário logado tem o atributo 'is_admin' e se ele é True.
        # VOCÊ PRECISARÁ AJUSTAR ISSO CONFORME COMO VOCÊ DEFINE UM ADMINISTRADOR NO SEU MODELO 'User'.
        # Por exemplo, se você tiver uma coluna 'role' com o valor 'admin',
        # pode ser 'current_user.role == 'admin'' ou uma propriedade '@property is_admin' no seu modelo User.
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return f(*args, **kwargs) # Permite o acesso se for administrador
        else:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('home')) # Redireciona para a página inicial
    
    # O Flask precisa que o nome da função embrulhada seja o mesmo da função original para roteamento.
    wrap.__name__ = f.__name__
    return wrap


# ----------------------------------------------------------------------
# 3. Rotas de Gerenciamento de Grupos
# ----------------------------------------------------------------------

@admin_bp.route('/groups')
@admin_required # Apenas administradores podem acessar esta rota
def list_groups():
    """
    Exibe uma lista de todos os grupos cadastrados.
    """
    groups = Group.query.all() # Busca todos os grupos do banco de dados
    # Renderiza o template HTML para listar os grupos.
    # O caminho é relativo ao 'template_folder' definido no Blueprint.
    return render_template('groups/list_groups.html', groups=groups)


@admin_bp.route('/groups/create', methods=['GET', 'POST'])
@admin_required # Apenas administradores podem acessar esta rota
def create_group():
    """
    Permite a criação de um novo grupo.
    GET: Exibe o formulário de criação.
    POST: Processa o envio do formulário, cria e salva o novo grupo.
    """
    form = GroupForm() # Instancia o formulário GroupForm
    if form.validate_on_submit(): # Verifica se o formulário foi submetido e é válido
        new_group = Group(name=form.name.data, description=form.description.data)
        try:
            db.session.add(new_group) # Adiciona o novo grupo à sessão do banco de dados
            db.session.commit() # Salva as alterações no banco de dados
            flash('Grupo criado com sucesso!', 'success') # Mensagem de sucesso
            # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
            return redirect(url_for('custom_admin.list_groups')) # Redireciona para a lista de grupos
        except IntegrityError: # Captura erro de unicidade (se o nome do grupo já existir)
            db.session.rollback() # Desfaz a transação para evitar inconsistências
            flash('Erro: Um grupo com este nome já existe.', 'danger') # Mensagem de erro
    
    # Renderiza o template com o formulário para criação/edição.
    return render_template('groups/create_edit_group.html', title='Criar Grupo', form=form)


@admin_bp.route('/groups/edit/<int:group_id>', methods=['GET', 'POST'])
@admin_required # Apenas administradores podem acessar esta rota
def edit_group(group_id):
    """
    Permite a edição de um grupo existente.
    GET: Preenche o formulário com os dados atuais do grupo.
    POST: Processa o envio do formulário, atualiza e salva o grupo.
    """
    group = Group.query.get_or_404(group_id) # Busca o grupo pelo ID ou retorna 404 se não encontrar
    
    # Instancia o formulário GroupForm, passando o nome original do grupo.
    # Isso é crucial para a validação de unicidade no formulário, permitindo que o próprio grupo
    # mantenha seu nome sem disparar um erro de "nome já existe".
    form = GroupForm(original_name=group.name)
    
    if form.validate_on_submit(): # Se o formulário foi submetido e é válido
        group.name = form.name.data # Atualiza o nome do grupo
        group.description = form.description.data # Atualiza a descrição
        try:
            db.session.commit() # Salva as alterações no banco de dados
            flash('Grupo atualizado com sucesso!', 'success') # Mensagem de sucesso
            # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
            return redirect(url_for('custom_admin.list_groups')) # Redireciona para a lista de grupos
        except IntegrityError: # Captura erro de unicidade
            db.session.rollback()
            flash('Erro: Um grupo com este nome já existe.', 'danger')
    elif request.method == 'GET': # Se a requisição for GET (primeira vez que a página é carregada)
        form.name.data = group.name # Preenche o campo 'name' do formulário com o nome atual do grupo
        form.description.data = group.description # Preenche o campo 'description'
    
    # Renderiza o template com o formulário pré-preenchido ou com erros de validação.
    return render_template('groups/create_edit_group.html', title='Editar Grupo', form=form)


@admin_bp.route('/groups/delete/<int:group_id>', methods=['POST'])
@admin_required # Apenas administradores podem acessar esta rota
def delete_group(group_id):
    """
    Exclui um grupo específico.
    Esta rota aceita apenas requisições POST para evitar exclusões acidentais.
    """
    group = Group.query.get_or_404(group_id) # Busca o grupo ou retorna 404
    try:
        db.session.delete(group) # Marca o grupo para exclusão
        db.session.commit() # Efetiva a exclusão no banco de dados
        flash('Grupo excluído com sucesso!', 'success') # Mensagem de sucesso
    except Exception as e: # Captura outros possíveis erros na exclusão
        db.session.rollback()
        flash(f'Erro ao excluir o grupo: {e}', 'danger') # Mensagem de erro
    # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
    return redirect(url_for('custom_admin.list_groups')) # Redireciona para a lista de grupos


@admin_bp.route('/groups/manage_members/<int:group_id>', methods=['GET', 'POST'])
@admin_required # Apenas administradores podem acessar esta rota
def manage_group_members(group_id):
    """
    Gerencia os usuários membros de um grupo específico.
    GET: Exibe o formulário com os usuários atuais do grupo.
    POST: Processa o envio do formulário, atualiza os membros do grupo.
    """
    group = Group.query.get_or_404(group_id) # Busca o grupo ou retorna 404
    form = AssignUsersToGroupForm() # Instancia o formulário de atribuição de usuários

    # O QuerySelectField para 'group' no formulário precisa de um objeto 'Group'.
    # O QuerySelectMultipleField para 'users' precisa de uma lista de objetos 'User'.
    if request.method == 'GET':
        form.group.data = group # Preenche o campo de seleção do grupo com o grupo atual
        form.users.data = group.users # Preenche os checkboxes com os usuários que já são membros

    elif form.validate_on_submit(): # Se o formulário foi submetido e é válido
        # Validação extra: Garante que o grupo selecionado no formulário
        # (se o campo não for desabilitado no template) é o mesmo que estamos editando na URL.
        if form.group.data and form.group.data.id != group.id:
            flash('Erro: Grupo selecionado no formulário não corresponde ao grupo que está sendo editado.', 'danger')
            # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
            return redirect(url_for('custom_admin.list_groups'))

        # Atualiza a relação many-to-many. O SQLAlchemy gerencia as inserções/exclusões na tabela 'user_group'.
        group.users = form.users.data 
        db.session.commit() # Salva as alterações
        flash(f'Membros do grupo "{group.name}" atualizados com sucesso!', 'success')
        # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
        return redirect(url_for('custom_admin.list_groups')) # Redireciona para a lista de grupos

    # Renderiza o template para gerenciar membros.
    return render_template('groups/manage_group_members.html', title=f'Gerenciar Membros de {group.name}', form=form, group=group)


# ----------------------------------------------------------------------
# 4. Rota para Permissões de Evento (Ainda para Implementar a Lógica de Salvamento)
# ----------------------------------------------------------------------

@admin_bp.route('/event_permissions', methods=['GET', 'POST'])
@admin_required
def set_event_permissions():
    """
    Define permissões para eventos para usuários ou grupos.
    A lógica completa para salvar e gerenciar as permissões no banco de dados
    precisará ser implementada aqui, utilizando o modelo EventPermission.
    """
    form = EventPermissionForm()
    if form.validate_on_submit():
        event = form.event.data
        user = form.user.data # Objeto User (ou None)
        group = form.group.data # Objeto Group (ou None)
        can_view = form.can_view.data
        can_edit = form.can_edit.data

        # --- LÓGICA DE SALVAMENTO DE PERMISSÕES VEM AQUI ---
        # Exemplo BÁSICO do que precisaria ser feito:
        # from models import EventPermission # Certifique-se que está importado no topo

        # if user:
        #     # Busca ou cria a permissão para o usuário no evento
        #     permission = EventPermission.query.filter_by(event_id=event.id, user_id=user.id).first()
        #     if not permission:
        #         permission = EventPermission(event=event, user=user)
        #     permission.can_view = can_view
        #     permission.can_edit = can_edit
        #     db.session.add(permission)
        # elif group:
        #     # Busca ou cria a permissão para o grupo no evento
        #     permission = EventPermission.query.filter_by(event_id=event.id, group_id=group.id).first()
        #     if not permission:
        #         permission = EventPermission(event=event, group=group)
        #     permission.can_view = can_view
        #     permission.can_edit = can_edit
        #     db.session.add(permission)
        # try:
        #    db.session.commit()
        #    flash('Permissões de evento atualizadas com sucesso!', 'success')
        #    # ATENÇÃO: Se você usa 'admin.some_permissions_list_route' em outros lugares, terá que mudar para 'custom_admin.some_permissions_list_route'
        #    return redirect(url_for('custom_admin.some_permissions_list_route')) # Crie uma rota para listar permissões
        # except Exception as e:
        #    db.session.rollback()
        #    flash(f'Erro ao salvar permissões: {e}', 'danger')
        
        flash('Permissões de evento definidas (Lógica de salvamento ainda precisa ser implementada)!', 'info')
        # Idealmente, redirecione para uma página de listagem de permissões ou de volta para a lista de eventos
        # ATENÇÃO: Se você usa 'admin.list_groups' em outros lugares, terá que mudar para 'custom_admin.list_groups'
        return redirect(url_for('custom_admin.list_groups')) # Apenas para exemplo, mude isso depois
    
    # Renderiza o template para definir permissões.
    return render_template('event_permissions/set_permissions.html', title='Definir Permissões de Evento', form=form)