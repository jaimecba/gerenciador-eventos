## Configurações básicas do Flask
FLASK_APP=app.py
FLASK_DEBUG=1

# Configurações do Banco de Dados PostgreSQL
# Usuario: flask_user
# Senha: flaskpass
# Host: localhost
# Porta: 5432
# Nome do Banco: gerenciador_eventos_db
DATABASE_URL=postgresql://flask_user:minhasenha@localhost:5432/gerenciador_eventos_db

# --- Configurações de E-mail para Teste Local ---
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=587
MAIL_USE_TLS='True'
EMAIL_USER='gerenciador.eventos@grandetemplo.com.br'
EMAIL_PASS='lrjrnyyjekfoyinh' # <--- AGORA DEFINIDA COM A SENHA DO APLICATIVO
MAIL_DEFAULT_SENDER='gerenciador.eventos@grandetemplo.com.br' # <--- SUBSTITUA com seu e-mail real


# Chaves VAPID para Notificações Push
VAPID_PUBLIC_KEY="BC98BG7jHcyte4cJiCXFBwycjUIoN9dKBo26MltK_MwiKYMSqL6xF0bnGrX8fS0GQX3uQ59BzmKOAtvuQ6A05ZY"
VAPID_PRIVATE_KEY="F4rU7IKNXHF-PJsQkfOPexfuqkeDIWOPjyXS-_ajxRU"
VAPID_CLAIMS="{'sub': 'mailto:gerenciador.eventos@grandetemplo.com.br'}"