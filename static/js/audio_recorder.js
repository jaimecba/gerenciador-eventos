// static/js/audio_recorder.js

document.addEventListener('DOMContentLoaded', () => {
    // Encontra todos os contêineres de gravador de áudio
    document.querySelectorAll('.audio-recorder-container').forEach(container => {
        const taskId = container.dataset.taskId;
        const recordButton = container.querySelector('.record-button');
        const stopButton = container.querySelector('.stop-button');
        const playButton = container.querySelector('.play-button');
        const deleteButton = container.querySelector('.delete-audio-button'); // Novo botão de exclusão
        const durationDisplay = container.querySelector('.duration-display');
        const statusDisplay = container.querySelector('.status-display');
        const audioPlayer = container.querySelector('.audio-player');
        const existingAudioPath = container.dataset.existingAudioPath; // Caminho do áudio existente
        const existingAudioDuration = container.dataset.existingAudioDuration; // Duração do áudio existente

        let mediaRecorder;
        let audioChunks = [];
        let audioBlob;
        let timerInterval;
        let seconds = 0;
        let currentAudioUrl = null;

        // Função para atualizar a exibição da duração
        const updateDurationDisplay = (secs) => {
            const minutes = Math.floor(secs / 60);
            const remainingSeconds = secs % 60;
            durationDisplay.textContent = 
                `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        };

        // Função para exibir mensagens flash
        function flashMessage(message, category) {
            const flashContainer = document.querySelector('.flash-messages-container') || document.createElement('div');
            if (!flashContainer.classList.contains('flash-messages-container')) {
                 flashContainer.classList.add('flash-messages-container');
                 // Cria uma div para as mensagens flash na parte superior do body
                 const body = document.querySelector('body');
                 if (body) {
                     body.prepend(flashContainer); 
                 }
            }
            const alertDiv = document.createElement('div');
            alertDiv.classList.add('alert', `alert-${category}`, 'alert-dismissible', 'fade', 'show'); // Adicionado dismissible
            alertDiv.setAttribute('role', 'alert');
            alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`; // Adicionado botão de fechar
            
            flashContainer.appendChild(alertDiv);
            
            // Remove a mensagem após 5 segundos
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alertDiv); // Usa a API do Bootstrap para fechar
                bsAlert.close();
            }, 5000); 
        }

        // Inicializa o estado do gravador/player
        const initializeRecorder = () => {
            if (existingAudioPath) {
                // Se já existe áudio, mostra o player e botões de reprodução/exclusão
                currentAudioUrl = existingAudioPath;
                audioPlayer.src = currentAudioUrl;
                audioPlayer.load(); // Carrega o áudio para o player
                audioPlayer.style.display = 'block';
                playButton.style.display = 'inline-block';
                deleteButton.style.display = 'inline-block';
                recordButton.style.display = 'none'; // Esconde o botão de gravação
                stopButton.style.display = 'none'; // Esconde o botão de parada
                statusDisplay.textContent = 'Áudio disponível';
                updateDurationDisplay(parseInt(existingAudioDuration || 0)); // Mostra a duração existente
                durationDisplay.style.display = 'inline-block';
            } else {
                // Se não há áudio existente, mostra apenas o botão de gravação
                recordButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                playButton.style.display = 'none';
                deleteButton.style.display = 'none';
                audioPlayer.style.display = 'none';
                statusDisplay.textContent = 'Pronto para gravar';
                durationDisplay.textContent = '00:00';
                durationDisplay.style.display = 'none';
            }
        };

        // Iniciar a gravação
        recordButton.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm; codecs=opus' });
                audioChunks = [];

                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/webm; codecs=opus' });
                    currentAudioUrl = URL.createObjectURL(audioBlob);
                    audioPlayer.src = currentAudioUrl;
                    audioPlayer.load(); // Carrega o áudio para o player

                    // Envia o áudio para o servidor
                    await uploadAudio(audioBlob, taskId, seconds); // Passa a duração real da gravação

                    // Esconde o botão de gravação, mostra play e delete
                    recordButton.style.display = 'none';
                    stopButton.style.display = 'none';
                    playButton.style.display = 'inline-block';
                    deleteButton.style.display = 'inline-block';
                    audioPlayer.style.display = 'block';
                    statusDisplay.textContent = 'Gravação salva';
                    updateDurationDisplay(seconds); // Atualiza duração final
                    durationDisplay.style.display = 'inline-block';

                    // Para o stream da câmera/microfone após a gravação
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                statusDisplay.textContent = 'Gravando...';
                recordButton.style.display = 'none';
                stopButton.style.display = 'inline-block';
                playButton.style.display = 'none';
                deleteButton.style.display = 'none';
                audioPlayer.style.display = 'none';
                durationDisplay.style.display = 'inline-block';
                seconds = 0;
                updateDurationDisplay(seconds);
                timerInterval = setInterval(() => {
                    seconds++;
                    updateDurationDisplay(seconds);
                }, 1000);

            } catch (err) {
                console.error('Erro ao acessar o microfone:', err);
                statusDisplay.textContent = 'Erro: Microfone não acessível.';
                flashMessage('Não foi possível acessar o microfone. Verifique as permissões.', 'danger');
                // Garante que os botões de gravação voltem ao estado inicial em caso de erro
                recordButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                playButton.style.display = 'none';
                deleteButton.style.display = 'none';
                audioPlayer.style.display = 'none';
                durationDisplay.style.display = 'none';
            }
        });

        // Parar a gravação
        stopButton.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                clearInterval(timerInterval);
                statusDisplay.textContent = 'Gravação finalizada.';
            }
        });

        // Reproduzir o áudio
        playButton.addEventListener('click', () => {
            if (audioPlayer.src) {
                audioPlayer.play();
                statusDisplay.textContent = 'Reproduzindo...';
            } else {
                statusDisplay.textContent = 'Nenhum áudio para reproduzir.';
            }
        });

        // Evento quando a reprodução termina
        audioPlayer.addEventListener('ended', () => {
            statusDisplay.textContent = 'Áudio disponível';
        });

        // Excluir o áudio
        deleteButton.addEventListener('click', async () => {
            if (!confirm('Tem certeza que deseja excluir esta gravação de áudio?')) {
                return;
            }

            try {
                const response = await fetch(`/api/task/${taskId}/delete_audio`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        // Incluir o CSRF token se necessário
                        // 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    flashMessage(data.message, 'success');
                    // Resetar o estado da UI para "pronto para gravar"
                    audioPlayer.src = '';
                    audioPlayer.style.display = 'none';
                    currentAudioUrl = null;
                    initializeRecorder(); // Reinicializa para o estado padrão sem áudio
                } else {
                    flashMessage(data.message || 'Erro ao excluir o áudio.', 'danger');
                }
            } catch (error) {
                console.error('Erro na requisição de exclusão:', error);
                flashMessage('Erro de rede ao excluir o áudio.', 'danger');
            }
        });

        // Função para upload do áudio para o servidor
        const uploadAudio = async (blob, taskId, duration) => {
            const formData = new FormData();
            formData.append('audio_file', blob, 'recorded_audio.webm'); // Nome do arquivo será 'recorded_audio.webm'
            formData.append('duration_seconds', duration);

            try {
                const response = await fetch(`/api/task/${taskId}/upload_audio`, {
                    method: 'POST',
                    body: formData,
                    // Não defina Content-Type; o navegador define para FormData
                    // Incluir o CSRF token se necessário
                    // 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                });

                const data = await response.json();

                if (response.ok) {
                    flashMessage(data.message, 'success');
                    // Se o upload foi bem-sucedido, atualiza o src do player com a URL do servidor
                    // A URL retornada pelo backend será a que a rota `static_audio_files` serve.
                    audioPlayer.src = data.audio_url_base;
                    audioPlayer.load(); // Garante que o player carregue o novo áudio
                    // Atualiza a duração exibida com a duração real do áudio no servidor, se for diferente.
                    // Para este protótipo, a duração é a que foi enviada.
                    updateDurationDisplay(duration);
                } else {
                    flashMessage(data.message || 'Erro ao fazer upload do áudio.', 'danger');
                    // Em caso de erro no upload, talvez reverter para o estado inicial ou tentar novamente
                    initializeRecorder(); // Reverte ao estado inicial
                }
            } catch (error) {
                console.error('Erro na requisição de upload:', error);
                flashMessage('Erro de rede ao fazer upload do áudio.', 'danger');
                initializeRecorder(); // Reverte ao estado inicial
            }
        };

        initializeRecorder(); // Chama a função de inicialização ao carregar a página
    });
});