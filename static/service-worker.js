// service-worker.js

// Nome do cache para armazenar os assets. É uma boa prática versionar o cache.
const CACHE_NAME = 'gerenciador-eventos-cache-v1.0';

// Lista de URLs para pré-cache. Estes arquivos serão baixados e armazenados
// no cache durante a instalação do Service Worker.
// Inclua todas as dependências críticas para o funcionamento offline básico.
const urlsToCache = [
  '/', // Página inicial
  '/static/manifest.json',
  '/static/css/style.css',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',

  // Adicione aqui os links para suas bibliotecas CDN essenciais
  // Isso permite que o app funcione offline com os estilos e scripts básicos
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
  'https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/main.min.css',
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
        // Força o Service Worker a assumir o controle imediatamente
        // para que a página aberta possa usar o novo Service Worker.
        return self.clients.claim();
    })
  );
});

// Evento 'fetch':
// Disparado para cada requisição de rede que o navegador faz.
// Permite interceptar requisições e servir respostas do cache ou da rede.
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // Verifique se a requisição é do mesmo domínio e para um recurso estático ou página principal
  // Estratégia: Cache First, Network Second, e então Atualiza Cache
  if (requestUrl.origin === location.origin && (
      requestUrl.pathname === '/' || // Home page
      requestUrl.pathname.startsWith('/static/') || // Conteúdo estático
      requestUrl.pathname.endsWith('.js') ||
      requestUrl.pathname.endsWith('.css') ||
      requestUrl.pathname.match(/\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/) // Imagens e fontes
     )) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          console.log('[Service Worker] Servindo do cache:', event.request.url);
          return cachedResponse;
        }

        console.log('[Service Worker] Buscando da rede e armazenando em cache:', event.request.url);
        return fetch(event.request).then((response) => {
          // Garante que só cacheamos respostas válidas (status 200) e que não são para requisições de tipo 'basic'
          // 'basic' significa requisições que não são de origem cruzada.
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clona a resposta para que ela possa ser consumida tanto pelo cache quanto pelo navegador.
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
          return response;
        }).catch((error) => {
          console.error('[Service Worker] Falha ao buscar e cachear:', event.request.url, error);
          // Se falhar a rede e não houver cache, pode retornar uma página offline.
          // Por enquanto, apenas falha.
        });
      })
    );
  } else if (event.request.mode === 'navigate') {
    // Para todas as requisições de navegação (carregar uma nova página HTML),
    // tente a rede primeiro para garantir conteúdo mais fresco.
    // Se a rede falhar, tente o cache.
    event.respondWith(
      fetch(event.request).catch(() => {
        console.log('[Service Worker] Rede offline para navegação, tentando cache:', event.request.url);
        return caches.match(event.request);
      })
    );
  }
  // Para outras requisições (como API, etc.) que não correspondem aos padrões acima,
  // elas não são interceptadas e vão diretamente para a rede (comportamento padrão).
  // Você pode adicionar mais lógica aqui se precisar cachear API responses ou ter
  // uma estratégia offline mais complexa para dados dinâmicos.
});

// Evento 'push': (PARA FUTURA IMPLEMENTAÇÃO DE NOTIFICAÇÕES PUSH)
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

// Evento 'notificationclick': (PARA FUTURA IMPLEMENTAÇÃO DE NOTIFICAÇÕES PUSH)
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