# C:\gerenciador-eventos\test_password_debug.py

from app import create_app # Importa a função create_app do seu arquivo app.py
from extensions import db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash

# Crie uma instância do aplicativo Flask
app = create_app()

# Define o contexto da aplicação para que o SQLAlchemy e outros módulos funcionem
with app.app_context():
    print("--- INICIANDO TESTE DE SENHA ---")
    TEST_PASSWORD = 'senhafacil123'
    
    # 1. Recupere o usuário admin
    admin_user = User.query.filter_by(username='admin_test').first()

    if admin_user:
        print(f"DEBUG: Usuário '{admin_user.username}' ({admin_user.email}) encontrado.")
        
        # 2. Defina a nova senha usando a função set_password
        print(f"DEBUG: Definindo nova senha para '{TEST_PASSWORD}'...")
        admin_user.set_password(TEST_PASSWORD)
        db.session.commit()
        print(f"DEBUG: Senha para '{admin_user.email}' definida para '{TEST_PASSWORD}' e commitada no DB.")
        print(f"DEBUG: Hash da senha armazenado no objeto (após set_password): {admin_user.password_hash}")

        # 3. Recupere o USUÁRIO NOVAMENTE do banco de dados para garantir que a leitura está correta
        # Isso simula o que aconteceria em um novo request ou após reiniciar a aplicação.
        admin_user_reloaded = User.query.filter_by(username='admin_test').first()

        if admin_user_reloaded:
            print(f"DEBUG: Usuário recarregado do DB. Hash armazenado (do recarregado): {admin_user_reloaded.password_hash}")

            # 4. Teste a senha COM O USUÁRIO RECEM-CARREGADO
            print(f"DEBUG: Verificando a senha '{TEST_PASSWORD}' para o usuário recarregado...")
            if admin_user_reloaded.check_password(TEST_PASSWORD):
                print(f"*** SUCESSO ABSOLUTO: '{TEST_PASSWORD}' funciona para o usuário recarregado! ***")
                print("Você pode tentar fazer login com essa senha no navegador agora.")
            else:
                print(f"### FALHA INESPERADA: '{TEST_PASSWORD}' NÃO funciona para o usuário recarregado. ###")
                print(f"Hash armazenado (do recarregado): {admin_user_reloaded.password_hash}")
                # Para depuração mais profunda, vamos verificar o check_password_hash diretamente
                direct_check_result = check_password_hash(admin_user_reloaded.password_hash, TEST_PASSWORD)
                print(f"Resultado de check_password_hash(hash_do_db, '{TEST_PASSWORD}'): {direct_check_result}")

        else:
            print("ERRO CRÍTICO: Usuário 'admin_test' não foi encontrado após commit. Algo está MUITO errado com a persistência no DB.")
    else:
        print("ERRO CRÍTICO: Usuário 'admin_test' não encontrado no banco de dados. Verifique se ele foi criado (use 'flask create-db').")

    print("--- TESTE DE SENHA FINALIZADO ---")
