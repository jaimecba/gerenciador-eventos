// service-worker.js

// Nome do cache para armazenar os assets. É uma boa prática versionar o cache.
// *** MUITO IMPORTANTE: ALTERE ESTE NÚMERO OU STRING QUANDO HOUVER GRANDES MUDANÇAS E VOCÊ QUISER FORÇAR A ATUALIZAÇÃO DO CACHE DE ASSETS! ***
const CACHE_NAME = 'gerenciador-eventos-cache-v1.2'; // Alterado para forçar a atualização do cache

// Lista de URLs para pré-cache. Estes arquivos serão baixados e armazenados
// no cache durante a instalação do Service Worker.
// Inclua todas as dependências críticas para o funcionamento offline básico.
const urlsToCache = [
  '/', // Página inicial
  '/static/manifest.json',
  '/static/css/style.css?v=20240928v01',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',

  // Adicione aqui os links para suas bibliotecas CDN essenciais
  // Isso permite que o app funcione offline com os estilos e scripts básicos
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
  'https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/min.css',
  'https://code.jquery.com/jquery-3.7.1.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/i18n/pt-BR.js',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/locales/pt-br.global.min.js'
];

// Evento 'install':
// Disparado quando o Service Worker é instalado.
// Usado para pré-cachear os assets definidos em 'urlsToCache'.
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Instalando Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Pré-cacheando recursos:', urlsToCache);
        return cache.addAll(urlsToCache);
      })
      .catch((error) => {
        console.error('[Service Worker] Falha ao pré-cachear:', error);
      }).then(() => {
          // Força o Service Worker a ativar-se imediatamente após a instalação.
          return self.skipWaiting();
      })
  );
});

// Evento 'activate':
// Disparado quando o Service Worker é ativado.
// Usado para limpar caches antigos, garantindo que apenas a versão atual do cache seja usada.
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Ativando Service Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deletando cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
          return Promise.resolve();
        })
      );
    }).then(() => {
        // Garante que o novo Service Worker assume o controle de todas as páginas imediatamente.
        return self.clients.claim();
    })
  );
});

// Evento 'fetch':
// Disparado para cada requisição de rede que o navegador faz.
// Permite interceptar requisições e servir respostas do cache ou da rede.
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // 1. Estratégia para requisições de NAVEGAÇÃO (carregamento de páginas HTML)
  // Cache First, com fallback para rede, e um fallback explícito para página offline
  if (event.request.mode === 'navigate') {
    event.respondWith(
      caches.match(event.request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            console.log('[Service Worker] Servindo navegação do cache (Cache First):', event.request.url);
            return cachedResponse;
          }
          console.log('[Service Worker] Navegação não no cache, tentando rede:', event.request.url);
          // Tentar rede. Se falhar (offline), o .catch() será ativado.
          return fetch(event.request);
        })
        .catch((error) => { // Captura erros tanto de caches.match quanto de fetch
          console.warn('[Service Worker] Falha ao servir navegação (offline ou erro):', event.request.url, error);
          // Se a rede falhar e o cache não tiver a página, tente servir a página inicial '/' como fallback.
          // Isso é útil se o Service Worker não conseguir pegar a URL exata da navegação do cache
          // mas a homepage estiver lá.
          return caches.match('/'); // Tentar servir a homepage pré-cacheada
        })
    );
    return; // Processamento finalizado para requisições de navegação
  }

  // 2. Estratégia para recursos estáticos do mesmo domínio (Cache First, Network Second, Update Cache)
  if (requestUrl.origin === location.origin && (
      requestUrl.pathname.startsWith('/static/') ||
      requestUrl.pathname.endsWith('.js') ||
      requestUrl.pathname.endsWith('.css') ||
      requestUrl.pathname.match(/\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/) ||
      requestUrl.pathname === '/static/manifest.json' // Garante que o manifest também é coberto
     )) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          console.log('[Service Worker] Servindo recurso estático/mesma origem do cache (Cache First):', event.request.url);
          return cachedResponse;
        }

        console.log('[Service Worker] Recurso estático/mesma origem não no cache, buscando da rede e armazenando:', event.request.url);
        return fetch(event.request).then((response) => {
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
          return response;
        }).catch((error) => {
          console.error('[Service Worker] Falha ao buscar e cachear recurso estático/mesma origem:', event.request.url, error);
          // Opcionalmente, pode-se retornar um placeholder ou um Response de erro aqui
        });
      })
    );
    return; // Processamento finalizado para recursos estáticos/mesma origem
  }

  // 3. Estratégia para CDNs pré-cacheadas (Cache First, Network Second)
  // Isso cobre as CDNs listadas em urlsToCache que não são do mesmo origin.
  // Certifique-se que o .catch() lida com falhas da rede em offline.
  if (urlsToCache.includes(event.request.url)) {
      event.respondWith(
          caches.match(event.request).then((cachedResponse) => {
              if (cachedResponse) {
                  console.log('[Service Worker] Servindo CDN pré-cacheada do cache (Cache First):', event.request.url);
                  return cachedResponse;
              }
              console.log('[Service Worker] CDN não no cache, tentando rede:', event.request.url);
              return fetch(event.request).then((response) => {
                  if (!response || response.status !== 200) { // Cross-origin responses might not have type 'basic'
                      return response;
                  }
                  const responseToCache = response.clone();
                  caches.open(CACHE_NAME).then((cache) => {
                      cache.put(event.request, responseToCache);
                  });
                  return response;
              }).catch((error) => {
                  console.error('[Service Worker] Falha ao buscar CDN pré-cacheada (offline?):', event.request.url, error);
                  // Em caso de falha para CDNs pré-cacheadas, se não estiver no cache, não há muito a fazer.
                  // Uma Response vazia ou um erro pode ser retornado.
              });
          })
      );
      return;
  }

  // 4. Default: Para quaisquer outras requisições não tratadas acima, passe-as para a rede.
  // (e.g., APIs dinâmicas que não devem ser cacheadas, ou requisições de outros origins não precacheadas)
  // Se estiver offline, estas requisições falharão.
  console.log('[Service Worker] Requisição não explicitamente cacheada, indo para rede:', event.request.url);
  // Não é necessário chamar event.respondWith(fetch(event.request)); aqui, pois é o comportamento padrão.
});

// Evento 'push':
// Disparado quando uma notificação push é recebida.
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Gerenciador de Eventos';
  const options = {
    body: data.body || 'Você tem uma nova notificação.',
    icon: '/static/images/icon-192x192.png', // Ícone da notificação
    badge: '/static/images/icon-192x192.png', // Badge (iOS/Android)
    data: {
      url: data.url || '/' // URL para abrir ao clicar na notificação
    }
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// Evento 'notificationclick':
// Disparado quando o usuário clica em uma notificação.
self.addEventListener('notificationclick', (event) => {
  event.notification.close(); // Fecha a notificação

  const targetUrl = event.notification.data.url || '/'; // Pega a URL definida na notificação

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Procura por uma janela existente para focar
      for (const client of clientList) {
        if (client.url === targetUrl && 'focus' in client) {
          return client.focus();
        }
      }
      // Se nenhuma janela existir, abre uma nova
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
      return null;
    })
  );
});