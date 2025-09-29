# C:\gerenciador-eventos\utils\push_notification_sender.py

from flask import current_app
from pywebpush import webpush, WebPushException
# IMPORTAÇÕES CORRIGIDAS: models.py e extensions.py estão na raiz do projeto
from models import PushSubscription, User
from extensions import db
import json
import threading

# ### CORREÇÃO ADICIONAL: Adicionado 'app' como primeiro argumento para a função assíncrona
def _send_notification_async(app, subscription, json_payload, vapid_private_key, vapid_public_key, vapid_claims, user_id):
    """
    Função auxiliar para enviar uma notificação push.
    Executada em uma thread separada.
    """
    # ### CORREÇÃO ADICIONAL: Empurra o contexto da aplicação para toda a execução da thread
    with app.app_context():
        try:
            webpush(
                subscription_info=subscription.to_dict(),
                data=json_payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims
            )
            # ### CORREÇÃO ADICIONAL: Usando 'app.logger' em vez de 'current_app.logger'
            app.logger.info(f"Notificação push enviada para o usuário {user_id} ({subscription.endpoint}).")
        except WebPushException as e:
            if e.response and e.response.status_code in [404, 410]: # Not Found ou Gone (Subscription expirada)
                # ### CORREÇÃO ADICIONAL: Usando 'app.logger' em vez de 'current_app.logger'
                app.logger.warning(f"Subscription push expirada/inválida para o usuário {user_id}. Removendo do banco de dados: {subscription.endpoint}")
                # As operações de DB já estavam protegidas, mas agora toda a função está
                db.session.delete(subscription)
                db.session.commit()
            else:
                # ### CORREÇÃO ADICIONAL: Usando 'app.logger' em vez de 'current_app.logger'
                app.logger.error(f"Erro ao enviar notificação push para o usuário {user_id} ({subscription.endpoint}): {e}")
        except Exception as e:
            # ### CORREÇÃO ADICIONAL: Usando 'app.logger' em vez de 'current_app.logger'
            app.logger.error(f"Erro inesperado ao enviar notificação push para o usuário {user_id} ({subscription.endpoint}): {e}")

def send_push_to_user(user_id, message_payload, link_url='/', notification_title='Gerenciador de Eventos'):
    """
    Envia uma notificação push para todas as subscriptions ativas de um usuário específico
    em uma thread separada para não bloquear a requisição HTTP principal.

    Args:
        user_id (int): O ID do usuário para o qual enviar a notificação.
        message_payload (dict): O payload da mensagem a ser enviado na notificação.
                                Deve conter 'body' e pode conter 'title', 'icon', 'badge', 'data'.
        link_url (str): A URL para onde o usuário será direcionado ao clicar na notificação.
        notification_title (str): O título padrão da notificação se não especificado no payload.
    """

    # Garante que as chaves VAPID estão configuradas
    vapid_public_key = current_app.config.get('VAPID_PUBLIC_KEY')
    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_claims = current_app.config.get('VAPID_CLAIMS')

    if not all([vapid_public_key, vapid_private_key, vapid_claims]):
        current_app.logger.error("Chaves VAPID não configuradas no aplicativo. Não é possível enviar notificações push.")
        return

    # Obter todas as subscriptions ativas para o usuário
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()

    if not subscriptions:
        current_app.logger.info(f"Nenhuma subscription push encontrada para o usuário {user_id}.")
        return

    # Prepara o payload da notificação para o service worker
    final_payload = {
        'title': notification_title,
        'body': message_payload.get('body', 'Você tem uma nova notificação.'),
        'icon': message_payload.get('icon', '/static/images/icon-192x192.png'),
        'badge': message_payload.get('badge', '/static/images/icon-192x192.png'),
        'data': {
            'url': message_payload.get('url', link_url),
            'type': message_payload.get('type', 'generic'),
            'task_id': message_payload.get('task_id'), # Incluir task_id no payload
            'event_id': message_payload.get('event_id') # Incluir event_id no payload
        }
    }

    # Transforma o payload em string JSON para enviar
    json_payload = json.dumps(final_payload)

    # Envia as notificações em threads separadas para não bloquear a requisição principal
    for subscription in subscriptions:
        # ### CORREÇÃO ADICIONAL: Passa o objeto 'app' real para a thread
        # Usamos current_app._get_current_object() para pegar o objeto real da aplicação,
        # e não o proxy de contexto, que pode causar problemas em threads.
        thread = threading.Thread(
            target=_send_notification_async,
            args=(current_app._get_current_object(), subscription, json_payload, vapid_private_key, vapid_public_key, vapid_claims, user_id)
        )
        thread.start()