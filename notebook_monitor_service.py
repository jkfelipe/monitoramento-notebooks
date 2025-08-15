import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import threading
import requests
import subprocess
import json
import os
import getpass
from datetime import datetime
import logging
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pytz
from auto_updater import AutoUpdater
from update_scheduler import UpdateScheduler

class NotebookMonitorService(win32serviceutil.ServiceFramework):
    """Serviço Windows para monitoramento de notebooks com PostgreSQL"""
    
    _svc_name_ = "NotebookMonitorService"
    _svc_display_name_ = "Serviço de Monitoramento de Notebooks"
    _svc_description_ = "Monitora localização, rede e informações do sistema dos notebooks da empresa"
    _svc_reg_class_ = "NotebookMonitorService"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        
        # Carrega variáveis de ambiente com caminho absoluto
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        load_dotenv(env_path)
        
        # Log do caminho do .env para debug
        self.setup_logging_early()
        self.logger.info(f"Carregando arquivo .env de: {env_path}")
        self.logger.info(f"Arquivo .env existe: {os.path.exists(env_path)}")
        
        # Configurações do banco de dados
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'monitoramento_notebooks'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'sslmode': os.getenv('DB_SSL_MODE', 'prefer')
        }
        
        # Log das configurações carregadas (sem mostrar senha)
        self.logger.info(f"DB_HOST carregado: {self.db_config['host']}")
        self.logger.info(f"DB_USER carregado: {self.db_config['user']}")
        self.logger.info(f"DB_PASSWORD carregado: {'***' if self.db_config['password'] else 'VAZIO'}")
        
        # Configurações do serviço
        self.monitor_interval = int(os.getenv('MONITOR_INTERVAL', 300))  # 5 minutos
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Timezone do Brasil
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
        self.setup_logging()
        self.test_database_connection()
        
    def setup_logging_early(self):
        """Configura logging básico para debug inicial"""
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notebook_monitor.log')
        
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        log_path = os.path.join(os.path.dirname(__file__), 'notebook_monitor.log')
        
        # Converte string do nível para constante
        log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        logging.basicConfig(
            filename=log_path,
            level=log_levels.get(self.log_level, logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def test_database_connection(self):
        """Testa a conexão com o banco de dados"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            self.logger.info("Conexão com PostgreSQL estabelecida com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao conectar com PostgreSQL: {e}")
            raise
            
    def get_db_connection(self):
        """Obtém conexão com o banco de dados"""
        return psycopg2.connect(**self.db_config)
        
    def get_external_ip(self) -> Optional[str]:
        """Obtém o IP externo do dispositivo"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=10)
            return response.json()['ip']
        except Exception as e:
            self.logger.error(f"Erro ao obter IP externo: {e}")
            return None
            
    def get_wifi_info(self) -> Dict[str, any]:
        """Obtém informações sobre WiFi conectado e redes disponíveis"""
        wifi_info = {
            'connected_wifi': None,
            'available_networks': []
        }
        
        try:
            # Obtém rede WiFi conectada
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True, text=True, encoding='utf-8'
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'SSID' in line and ':' in line:
                        ssid = line.split(':')[1].strip()
                        if ssid and ssid != '':
                            wifi_info['connected_wifi'] = ssid
                            break
            
            # Obtém redes disponíveis
            scan_result = subprocess.run(
                ['netsh', 'wlan', 'show', 'profiles'],
                capture_output=True, text=True, encoding='utf-8'
            )
            
            if scan_result.returncode == 0:
                lines = scan_result.stdout.split('\n')
                for line in lines:
                    if 'Perfil de Todos os Usuários' in line or 'All User Profile' in line:
                        network_name = line.split(':')[1].strip()
                        if network_name and network_name not in wifi_info['available_networks']:
                            wifi_info['available_networks'].append(network_name)
                            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações WiFi: {e}")
            
        return wifi_info
        
    def get_location(self) -> Dict[str, Optional[float]]:
        """Obtém localização aproximada via IP"""
        location = {
            'latitude': None,
            'longitude': None,
            'accuracy': None
        }
        
        try:
            # Usa serviço de geolocalização por IP
            response = requests.get('http://ip-api.com/json/', timeout=10)
            data = response.json()
            
            if data['status'] == 'success':
                location['latitude'] = data.get('lat')
                location['longitude'] = data.get('lon')
                location['accuracy'] = data.get('accuracy', 1000)  # Precisão em metros
                
        except Exception as e:
            self.logger.error(f"Erro ao obter localização: {e}")
            
        return location
        
    def get_system_info(self) -> Dict[str, any]:
        """Obtém informações do sistema"""
        try:
            # Tempo de atividade
            uptime_result = subprocess.run(
                ['wmic', 'os', 'get', 'LastBootUpTime', '/value'],
                capture_output=True, text=True
            )
            
            boot_time = None
            uptime_seconds = 0
            
            if uptime_result.returncode == 0:
                for line in uptime_result.stdout.split('\n'):
                    if 'LastBootUpTime=' in line:
                        boot_time_str = line.split('=')[1].strip()
                        if boot_time_str:
                            # Converte formato WMI para datetime com timezone
                            boot_time_naive = datetime.strptime(boot_time_str[:14], '%Y%m%d%H%M%S')
                            boot_time = self.timezone.localize(boot_time_naive)
                            current_time = datetime.now(self.timezone)
                            uptime_seconds = int((current_time - boot_time).total_seconds())
                        break
            
            # Versão do OS
            os_result = subprocess.run(
                ['wmic', 'os', 'get', 'Caption', '/value'],
                capture_output=True, text=True
            )
            
            os_version = "Windows"
            if os_result.returncode == 0:
                for line in os_result.stdout.split('\n'):
                    if 'Caption=' in line:
                        os_version = line.split('=')[1].strip()
                        break
            
            return {
                'hostname': socket.gethostname(),
                'username': getpass.getuser(),
                'uptime_seconds': uptime_seconds,
                'os_version': os_version,
                'last_boot_time': boot_time
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do sistema: {e}")
            return {
                'hostname': socket.gethostname(),
                'username': getpass.getuser(),
                'uptime_seconds': 0,
                'os_version': 'Windows',
                'last_boot_time': None
            }
            
    def collect_and_store_data(self):
        """Coleta todas as informações e armazena no PostgreSQL"""
        try:
            self.logger.info("Iniciando coleta de dados...")
            
            # Coleta informações
            external_ip = self.get_external_ip()
            wifi_info = self.get_wifi_info()
            location = self.get_location()
            system_info = self.get_system_info()
            
            # Armazena no banco de dados PostgreSQL
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Timestamp com timezone do Brasil
            current_timestamp = datetime.now(self.timezone)
            
            cursor.execute("""
                INSERT INTO monitoring_data (
                    timestamp, hostname, username, external_ip, connected_wifi, 
                    available_networks, latitude, longitude, location_accuracy,
                    uptime_seconds, os_version, last_boot_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                current_timestamp,
                system_info['hostname'],
                system_info['username'],
                external_ip,
                wifi_info['connected_wifi'],
                json.dumps(wifi_info['available_networks']),
                location['latitude'],
                location['longitude'],
                location['accuracy'],
                system_info['uptime_seconds'],
                system_info['os_version'],
                system_info['last_boot_time']
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info("Dados coletados e armazenados com sucesso no PostgreSQL")
            
        except Exception as e:
            self.logger.error(f"Erro durante coleta de dados: {e}")
            
    def monitor_loop(self):
        """Loop principal de monitoramento"""
        while self.running:
            try:
                self.collect_and_store_data()
                
                # Aguarda o intervalo ou sinal de parada
                if win32event.WaitForSingleObject(self.hWaitStop, self.monitor_interval * 1000) == win32event.WAIT_OBJECT_0:
                    break
                    
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(60)  # Aguarda 1 minuto antes de tentar novamente
                
    def SvcStop(self):
        """Para o serviço"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        self.logger.info("Serviço de monitoramento parado")
        
    def SvcDoRun(self):
        """Inicia o serviço"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.logger.info("Serviço de monitoramento iniciado")
        
        # Inicia o loop de monitoramento em thread separada
        monitor_thread = threading.Thread(target=self.monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Inicializar sistema de atualização
        self.auto_updater = AutoUpdater()
        self.update_scheduler = UpdateScheduler(self.auto_updater)
    
        try:
            # Iniciar agendador de atualizações
            self.update_scheduler.start()
            
            # Aguarda sinal de parada
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        except Exception as e:
            self.logger.error(f"Erro no loop de monitoramento: {e}")
            time.sleep(60)  # Aguarda 1 minuto antes de tentar novamente
            
        # Parar agendador de atualizações
        if hasattr(self, 'update_scheduler'):
            self.update_scheduler.stop()
        
        self.logger.info("Serviço de monitoramento parado")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(NotebookMonitorService)