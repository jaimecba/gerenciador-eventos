# firebase_config.py

import firebase_admin
from firebase_admin import credentials
import os

def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Modifique ESTA LINHA para apontar para o nome do SEU novo arquivo JSON
            # Exemplo: 'firebase-admin-sdk.json' ou 'serviceAccountKey.json'
            # Use o nome exato que você deu ao arquivo baixado.
            cred_filename = 'firebase-admin-sdk.json' # <--- ALTERE AQUI PARA O NOME DO SEU ARQUIVO

            cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cred_filename)

            if not os.path.exists(cred_path):
                print(f"ERRO: Arquivo de credenciais do Firebase Admin SDK não encontrado em: {cred_path}")
                return

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK inicializado com sucesso!")
        except Exception as e:
            print(f"Erro FATAL ao inicializar Firebase Admin SDK: {e}")
    else:
        print("Firebase Admin SDK já está inicializado (pulando nova inicialização).")