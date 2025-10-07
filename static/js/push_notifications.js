// static/js/push_notifications.js

// Variável global para armazenar a chave VAPID pública
let VAPID_PUBLIC_KEY = null;

// Função auxiliar para converter a chave VAPID pública de base64 para Uint8Array.
// Isso é necessário porque a API PushManager espera a chave neste formato.
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

/**
 * Inicia o processo de inscrição do usuário para notificações push.
 * Verifica a compatibilidade do navegador, pede permissão e envia a subscription
 * para o backend Flask.
 */
async function subscribeUserToPush() {
    // 1. Verificar compatibilidade com Service Workers e Push API
    if (!('serviceWorker' in navigator)) {
        console.warn('Service Workers não são suportados neste navegador.');
        return;
    }
    if (!('PushManager' in window)) {
        console.warn('Push Notifications não são suportadas neste navegador.');
        return;
    }

    try {
        // ### CORREÇÃO 1: Carregar a VAPID Public Key do backend
        if (!VAPID_PUBLIC_KEY) {
            console.log('Obtendo VAPID Public Key do backend...');
            const response = await fetch('/api/vapid-public-key');
            if (!response.ok) {
                // Tenta ler o erro do JSON, mas trata como texto se falhar
                let errorDetails = '';
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.error || response.statusText;
                } catch (e) {
                    errorDetails = response.statusText;
                }
                console.error('Falha ao obter VAPID Public Key do backend:', response.status, errorDetails);
                alert('Erro: Não foi possível configurar as notificações. Chave pública não encontrada.');
                return;
            }
            const data = await response.json();
            VAPID_PUBLIC_KEY = data.vapid_public_key;
            console.log('VAPID Public Key obtida com sucesso.');
        }

        // Se por algum motivo ainda não tivermos a chave (erro no fetch anterior)
        // A verificação agora é apenas se a chave está vazia/nula, já que ela é buscada do backend.
        // --- ALTERAÇÃO FEITA AQUI ---
        if (!VAPID_PUBLIC_KEY) {
            console.error('VAPID Public Key não configurada ou inválida após tentativa de obtenção.');
            alert('Erro: Chave de notificação não configurada corretamente. Contate o administrador.');
            return;
        }
        // --- FIM DA ALTERAÇÃO ---

        // Aguarda a prontidão do Service Worker registrado
        const registration = await navigator.serviceWorker.ready;

        // 2. Verificar o estado atual da permissão de notificação
        let permissionState = await registration.pushManager.permissionState({ userVisibleOnly: true });
        if (permissionState === 'denied') {
            console.warn('Permissão de notificação negada permanentemente pelo usuário.');
            alert('As notificações foram bloqueadas. Para ativá-las, você precisará mudar as configurações do seu navegador.');
            return;
        }

        const applicationServerKey = urlBase64ToUint8Array(VAPID_PUBLIC_KEY);

        // 3. Tentar obter uma subscription existente para evitar criar duplicatas
        let subscription = await registration.pushManager.getSubscription();

        if (subscription) {
            console.log('Usuário já está inscrito para Push Notifications:', subscription);
            // Se já está inscrito, envie para o backend para garantir que o backend também tem
            await sendSubscriptionToBackend(subscription);
        } else {
            console.log('Usuário ainda não inscrito, solicitando permissão...');
            // 4. Solicitar nova inscrição se não houver uma existente
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true, // Indica que todas as notificações serão visíveis ao usuário
                applicationServerKey: applicationServerKey // A chave pública do seu servidor VAPID
            });
            console.log('Usuário inscrito com sucesso:', subscription);

            // 5. Enviar a nova subscription para o seu backend Flask
            await sendSubscriptionToBackend(subscription);
        }

    } catch (error) {
        if (Notification.permission === 'denied') {
            console.warn('Permissão de notificação negada pelo usuário durante a solicitação.');
            alert('As notificações foram bloqueadas. Para ativá-las, você precisará mudar as configurações do seu navegador.');
        } else {
            console.error('Falha ao inscrever o usuário para Push:', error);
            debugger; 
            alert('Não foi possível ativar as notificações. Por favor, tente novamente mais tarde.');
        }
    }
}

/**
 * Envia o objeto PushSubscription obtido do navegador para o backend Flask,
 * que deverá armazená-lo para enviar notificações futuras.
 * @param {PushSubscription} subscription - O objeto PushSubscription a ser enviado.
 */
async function sendSubscriptionToBackend(subscription) {
    // Endpoint do seu backend Flask para receber a subscription
    debugger;
    const response = await fetch('/api/subscribe', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(subscription) // Envia o objeto subscription como JSON
    });

    if (!response.ok) {
        console.error('Falha ao enviar subscription para o backend:', response.status, response.statusText);
        throw new Error('Falha ao enviar subscription para o backend.');
    }
    console.log('Subscription enviada para o backend com sucesso.');
}

// Opcional: Se você quiser um botão para ativar as notificações, remova o
// window.addEventListener('load', subscribeUserToPush) do base.html e chame
// subscribeUserToPush() no evento de clique do botão.
// Exemplo de como você chamará esta função no base.html ou em outro lugar:
// window.addEventListener('load', subscribeUserToPush);