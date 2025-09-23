# make_admin.py
import os
from flask import Flask
from extensions import db
from models import User

# Inicializa o aplicativo Flask para ter acesso ao contexto do banco de dados
# Ajuste 'app' aqui para o nome da sua instância do Flask (geralmente é 'app')
app = Flask(__name__)

# Carrega a configuração do seu aplicativo
# Se você tem um arquivo de configuração (config.py), importe-o aqui
# Por exemplo: app.config.from_object('config.Config')
# Ou se suas configurações estão diretamente em app.py, você pode ignorar esta linha
# e garantir que suas variáveis de ambiente ou configurações de DB estejam ativas.
# Para garantir, vamos simular o mínimo de configuração para o DB
# Substitua 'sqlite:///events.db' pelo seu DATABASE_URL real se for diferente
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o db com o app
db.init_app(app)

# Entra no contexto da aplicação para interagir com o banco de dados
with app.app_context():
    # --- PASSO 1: ENCONTRE O USUÁRIO QUE VOCÊ QUER TORNAR ADMINISTRADOR ---
    # Substitua 'SEU_USERNAME_AQUI' pelo nome de usuário exato de um usuário já registrado no seu sistema.
    # Por exemplo, se você registrou um usuário com o nome 'meuadmin', use 'meuadmin'.
    username_para_admin = 'jaimecba@gmail.com' 
    user_to_make_admin = User.query.filter_by(username=username_para_admin).first()

    if user_to_make_admin:
        # --- PASSO 2: ATRIBUI O PAPEL DE ADMINISTRADOR ---
        if user_to_make_admin.role != 'administrador':
            user_to_make_admin.role = 'administrador'
            db.session.commit()
            print(f"SUCESSO: O usuário '{user_to_make_admin.username}' agora é 'administrador'.")
        else:
            print(f"INFO: O usuário '{user_to_make_admin.username}' já é 'administrador'. Nenhuma alteração feita.")
    else:
        print(f"ERRO: Usuário '{username_para_admin}' não encontrado no banco de dados.")
        print("Por favor, verifique o username digitado ou registre um novo usuário se não tiver nenhum.")
