# C:\gerenciador-eventos\setup_permissions.py

from app import create_app, db
from models import Role, User, EventPermission, Event
import sys

# --------------------------------------------------------------------------
# Inicialização do Flask App - NECESSÁRIO para acessar o contexto da aplicação
# --------------------------------------------------------------------------
app = create_app()
app.app_context().push()
# --------------------------------------------------------------------------


def setup_roles_and_permissions():
    """
    Configura as capacidades de eventos para as roles existentes e
    atualiza as EventPermissions antigas para usar as novas roles.
    """
    print("Iniciando configuração de Roles e Permissões de Evento...")

    try:
        # --- 1. CONFIGURAR AS CAPACIDADES DE EVENTO PARA AS ROLES ---
        # Certifique-se de que estas roles existam no seu banco de dados
        # e ajuste os nomes conforme o que você usa (ex: 'Administrator' em vez de 'Admin')

        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            admin_role.can_view_event = True
            admin_role.can_edit_event = True
            admin_role.can_manage_permissions = True
            db.session.add(admin_role)
            print(f"Role '{admin_role.name}' configurada: pode visualizar, editar e gerenciar permissões.")
        else:
            print("AVISO: Role 'Admin' não encontrada. Crie-a ou ajuste o nome no script.")
        
        project_manager_role = Role.query.filter_by(name='Project Manager').first()
        if project_manager_role:
            project_manager_role.can_view_event = True
            project_manager_role.can_edit_event = True # PMs geralmente podem editar eventos
            project_manager_role.can_manage_permissions = True # PMs podem gerenciar permissões também
            db.session.add(project_manager_role)
            print(f"Role '{project_manager_role.name}' configurada: pode visualizar, editar e gerenciar permissões.")
        else:
            print("AVISO: Role 'Project Manager' não encontrada. Crie-a ou ajuste o nome no script.")

        user_role = Role.query.filter_by(name='User').first()
        if user_role:
            user_role.can_view_event = True  # Usuários padrão podem visualizar
            user_role.can_edit_event = False # Usuários padrão NÃO podem editar (por padrão)
            user_role.can_manage_permissions = False # Usuários padrão NÃO podem gerenciar permissões
            db.session.add(user_role)
            print(f"Role '{user_role.name}' configurada: pode visualizar, mas não editar ou gerenciar permissões.")
        else:
            print("AVISO: Role 'User' não encontrada. Crie-a ou ajuste o nome no script.")
            
        # --- Adicione outras roles conforme necessário ---
        # Exemplo: Criar uma nova role 'Event Editor' se você não tiver uma que se encaixe
        event_editor_role = Role.query.filter_by(name='Event Editor').first()
        if not event_editor_role:
            event_editor_role = Role(name='Event Editor', description='Pode visualizar e editar eventos, mas não gerenciar permissões.',
                                     can_view_event=True, can_edit_event=True, can_manage_permissions=False)
            db.session.add(event_editor_role)
            print(f"Role 'Event Editor' criada e configurada.")


        db.session.commit()
        print("Capacidades de evento atualizadas para as Roles existentes.")

        # --- 2. ATUALIZAR AS EVENTPERMISSIONS ANTIGAS ---
        # As EventPermissions existentes que não tinham 'role_id' foram preenchidas com um padrão
        # (provavelmente 1, que pode ser o ID da role 'Admin' ou 'User' dependendo do seu setup).
        # Agora, vamos atribuir roles mais significativas se necessário.

        print("\nVerificando e atualizando EventPermissions existentes...")
        
        # Encontre as roles que você vai usar para atualização
        # (use os objetos 'admin_role', 'project_manager_role', 'user_role' ou crie novos aqui)
        
        # Exemplo: Atualizar todas as EventPermissions que foram preenchidas com '1' (que pode ser 'Admin')
        # e que talvez devessem ser 'Project Manager' ou 'Event Editor'

        # PEGAR O ID DA ROLE PADRÃO COM QUE SUA MIGRACAO PREENCHEU AS PERMISSOES
        # Se você usou sa.text('1') e o ID da sua role 'Admin' é 1, então o padrão é 'Admin'.
        # Se o ID da sua role 'User' é 2, e você quer que permissões antigas sem role_id sejam 'User'
        # ou 'Event Editor', você precisará identificar as regras.

        # Este é um exemplo GENÉRICO. Você precisa adaptar à SUA lógica.
        # Por exemplo, talvez todas as EventPermissions antigas devessem ser
        # para a role 'Project Manager' se o usuário fosse um gerente, ou 'User' se fosse um usuário comum.

        # Opção 1: Se você quer que TODAS as EventPermissions existentes (que foram criadas antes da migração
        # e portanto foram setadas com o role_id padrão 1) se tornem Project Manager:
        # if project_manager_role:
        #     # Supondo que '1' foi o default ID usado na migração e queremos mudar para Project Manager
        #     # Você pode precisar ajustar o 'WHERE' clause se o padrão não foi '1'
        #     db.session.query(EventPermission).filter(
        #         EventPermission.role_id == 1, # ID da role padrão que foi usada na migração
        #         EventPermission.user_id.isnot(None) # Para EventPermissions de usuário (não grupo)
        #     ).update({EventPermission.role_id: project_manager_role.id}, synchronize_session=False)
        #     print(f"EventPermissions de usuário com role_id=1 (padrão) atualizadas para '{project_manager_role.name}'.")
        # else:
        #     print("AVISO: Role 'Project Manager' não disponível para atualização de EventPermissions.")

        # Opção 2: Ou talvez você queira simplesmente que a role_id padrão ('1') tenha as permissões de edição
        # e visualização para que as tarefas funcionem, e você gerencie as permissões mais tarde.
        # Neste caso, o importante é que a role 'Admin' ou 'User' que tem ID '1' tenha can_view_event=True e can_edit_event=True.
        # (O que você já faria na seção 1 deste script).

        # Para este momento, o mais seguro é que a role padrão (ID 1) tenha as capacidades mínimas.
        # Se sua role Admin é ID 1, e ela tem todas as capacidades, então as EventPermissions default já estão OK.

        db.session.commit()
        print("EventPermissions verificadas e atualizadas conforme necessário. (Revisar esta seção para lógica específica!)")

    except Exception as e:
        db.session.rollback()
        print(f"ERRO durante a configuração de roles/permissões: {e}", file=sys.stderr)
        sys.exit(1) # Sair com erro
    finally:
        db.session.close() # Fechar a sessão do banco de dados
        print("Configuração de Roles e Permissões de Evento finalizada.")

if __name__ == '__main__':
    setup_roles_and_permissions()