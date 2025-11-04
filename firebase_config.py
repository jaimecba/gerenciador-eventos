# firebase_config.py

import firebase_admin
from firebase_admin import credentials
import os # Importar para lidar com caminhos

def initialize_firebase():
    """
    Inicializa o Firebase Admin SDK.
    Esta função verifica se o Firebase já foi inicializado para evitar erros.
    """
    if not firebase_admin._apps: # Verifica se o Firebase Admin SDK já foi inicializado
        try:
            # Caminho para o arquivo google-services.json
            # Assumimos que 'google-services.json' está na raiz do projeto,
            # no mesmo nível do wsgi.py e firebase_config.py
            cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-services.json')
            
            # Se você tem certeza que o script SEMPRE será executado da raiz do projeto,
            # 'google-services.json' direto também funcionaria.
            # No entanto, cred_path com os.path.join torna mais robusto.
            
            if not os.path.exists(cred_path):
                print(f"ERRO: Arquivo de credenciais do Firebase não encontrado em: {cred_path}")
                # Você pode levantar uma exceção ou lidar com este erro de outra forma
                return

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK inicializado com sucesso!")
        except Exception as e:
            print(f"Erro FATAL ao inicializar Firebase Admin SDK: {e}")
            # Em uma aplicação real, você pode querer registrar este erro e sair
            # ou levantar uma exceção para impedir que o app inicie sem Firebase.
            # raise e # Descomente para parar a aplicação se a inicialização falhar
    else:
        print("Firebase Admin SDK já está inicializado (pulando nova inicialização).")
