// *** service-worker.js ***

// Nome do cache para armazenar os assets. Versione para forçar atualizações!
const CACHE_NAME = 'gerenciador-eventos-cache-v1.3'; // Atualize a versão sempre que necessário

// URLs para pré-cache. Estes arquivos serão baixados e armazenados no cache durante a instalação
const URLS_TO_CACHE = [
  '/',
  '/static/css/styles.css', // Exemplo: arquivo de estilos
  '/static/js/app.js',      // Exemplo: arquivo JS principal
  '/static/icons/icon-192x192.png', // Ícone padrão para PWA
  '/static/icons/icon-512x512.png', // Ícone padrão para PWA
];

// O evento de instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Instalando...');

  // Faz o pré-cache de assets
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Fazendo o pré-cache dos arquivos necessários...');
      return cache.addAll(URLS_TO_CACHE);
    })
  );
});

// O evento de ativação
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Ativando...');

  // Remove caches antigos
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log(`[Service Worker] Deletando cache antigo: ${cache}`);
            return caches.delete(cache);
          }
        })
      );
    })
  );

  // Garante que o Service Worker mais recente será utilizado
  return self.clients.claim();
});

// O evento de "fetch" para interceptar requisições e servir arquivos do cache
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Retorna o arquivo do cache, se disponível
      if (response) {
        console.log(`[Service Worker] Servindo do cache: ${event.request.url}`);
        return response;
      }
      console.log(`[Service Worker] Buscando: ${event.request.url}`);
      return fetch(event.request);
    })
  );
});

// Gerenciamento de notificações push
self.addEventListener('push', (event) => {
  console.log('[Service Worker] Recebeu uma notificação push.');

  // Dados da notificação
  let data = {};
  if (event.data) {
    data = event.data.json();
  }

  // Detalhes da notificação
  const title = data.title || 'Nova Notificação';
  const message = data.message || 'Você tem novas mensagens!';
  const icon = data.icon || '/static/icons/icon-192x192.png';
  const url = data.url || '/';

  // Exibe a notificação
  event.waitUntil(
    self.registration.showNotification(title, {
      body: message,
      icon: icon,
      data: { url }, // Guarda a URL para abrir ao clicar
    })
  );
});

// Gerenciamento do clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('[Service Worker] Notificação clicada.');
  event.notification.close();

  // Abrir ou focar na URL armazenada na notificação
  const notificationData = event.notification.data;
  const targetUrl = notificationData && notificationData.url ? notificationData.url : '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === targetUrl && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
      return null;
    })
  );
});