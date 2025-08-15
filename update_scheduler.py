#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agendador de Verificações de Atualização
Autor: Sistema de Monitoramento
Data: 2024-01-15
Timezone: America/Sao_Paulo
"""

import time
import threading
import logging
from datetime import datetime, timezone, timedelta
from auto_updater import AutoUpdater

# Configuração do timezone para São Paulo
SAO_PAULO_TZ = timezone(timedelta(hours=-3))

class UpdateScheduler:
    """
    Classe responsável por agendar verificações automáticas de atualização
    """
    
    def __init__(self, updater: AutoUpdater):
        """
        Inicializa o agendador
        
        Args:
            updater: Instância do AutoUpdater
        """
        self.updater = updater
        self.logger = logging.getLogger("UpdateScheduler")
        self.running = False
        self.thread = None
    
    def start(self):
        """
        Inicia o agendador em thread separada
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            self.logger.info("Agendador de atualizações iniciado")
    
    def stop(self):
        """
        Para o agendador
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Agendador de atualizações parado")
    
    def _run_scheduler(self):
        """
        Loop principal do agendador
        """
        while self.running:
            try:
                # Verificar e executar atualizações se necessário
                version_info = self.updater.load_version_info()
                
                if version_info.get('auto_update_enabled', True):
                    self.logger.debug("Verificando atualizações...")
                    
                    # Executar processo de atualização
                    success = self.updater.perform_update()
                    
                    if success:
                        self.logger.info("Verificação de atualização concluída")
                    else:
                        self.logger.warning("Problema na verificação de atualização")
                
                # Aguardar intervalo configurado (padrão: 24 horas)
                interval = version_info.get('update_check_interval', 86400)
                
                # Dormir em pequenos intervalos para permitir parada rápida
                sleep_time = 0
                while sleep_time < interval and self.running:
                    time.sleep(min(60, interval - sleep_time))  # Máximo 1 minuto por vez
                    sleep_time += 60
                    
            except Exception as e:
                self.logger.error(f"Erro no agendador de atualizações: {e}")
                time.sleep(300)  # Aguardar 5 minutos em caso de erro