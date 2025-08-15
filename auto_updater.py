#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Atualização Automática para Notebook Monitor Service
Autor: Sistema de Monitoramento
Data: 2024-01-15
Timezone: America/Sao_Paulo
"""

import os
import json
import requests
import hashlib
import shutil
import zipfile
import tempfile
import subprocess
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Configuração do timezone para São Paulo
SAO_PAULO_TZ = timezone(timedelta(hours=-3))

class AutoUpdater:
    """
    Classe responsável pela atualização automática do serviço
    """
    
    def __init__(self, base_dir: str = None):
        """
        Inicializa o sistema de atualização
        
        Args:
            base_dir: Diretório base do projeto
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.version_file = self.base_dir / "version.json"
        self.backup_dir = self.base_dir / "backups"
        self.temp_dir = self.base_dir / "temp_update"
        self.service_name = "NotebookMonitorService"
        
        # Configurar logging
        self.logger = logging.getLogger("AutoUpdater")
        self.logger.setLevel(logging.INFO)
        
        # Criar diretórios necessários
        self.backup_dir.mkdir(exist_ok=True)
        
    def load_version_info(self) -> Dict:
        """
        Carrega informações da versão atual
        
        Returns:
            Dict com informações da versão
        """
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Criar arquivo de versão padrão
                default_version = {
                    "version": "1.0.0",
                    "build_date": datetime.now(SAO_PAULO_TZ).isoformat(),
                    "commit_hash": "initial",
                    "update_url": "https://api.github.com/repos/seu-usuario/monitoramento-notebooks/releases/latest",
                    "auto_update_enabled": True,
                    "update_check_interval": 86400,  # 24 horas em segundos
                    "last_update_check": None,
                    "backup_retention_days": 7
                }
                self.save_version_info(default_version)
                return default_version
        except Exception as e:
            self.logger.error(f"Erro ao carregar informações de versão: {e}")
            return {}
    
    def save_version_info(self, version_info: Dict) -> bool:
        """
        Salva informações da versão
        
        Args:
            version_info: Dicionário com informações da versão
            
        Returns:
            True se salvou com sucesso
        """
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar informações de versão: {e}")
            return False
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Verifica se há atualizações disponíveis
        
        Returns:
            Dict com informações da nova versão ou None se não há atualizações
        """
        try:
            version_info = self.load_version_info()
            
            # Verificar se deve checar atualizações
            if not version_info.get('auto_update_enabled', True):
                return None
            
            # Verificar intervalo de checagem
            last_check = version_info.get('last_update_check')
            if last_check:
                last_check_time = datetime.fromisoformat(last_check)
                now = datetime.now(SAO_PAULO_TZ)
                interval = version_info.get('update_check_interval', 86400)
                
                if (now - last_check_time).total_seconds() < interval:
                    self.logger.info("Ainda não é hora de verificar atualizações")
                    return None
            
            # Fazer requisição para verificar nova versão
            update_url = version_info.get('update_url')
            if not update_url:
                self.logger.warning("URL de atualização não configurada")
                return None
            
            self.logger.info(f"Verificando atualizações em: {update_url}")
            
            response = requests.get(update_url, timeout=30)
            response.raise_for_status()
            
            release_info = response.json()
            
            # Atualizar timestamp da última verificação
            version_info['last_update_check'] = datetime.now(SAO_PAULO_TZ).isoformat()
            self.save_version_info(version_info)
            
            # Comparar versões
            current_version = version_info.get('version', '0.0.0')
            latest_version = release_info.get('tag_name', '').lstrip('v')
            
            if self._is_newer_version(latest_version, current_version):
                self.logger.info(f"Nova versão disponível: {latest_version} (atual: {current_version})")
                return {
                    'version': latest_version,
                    'download_url': self._get_download_url(release_info),
                    'release_notes': release_info.get('body', ''),
                    'published_at': release_info.get('published_at'),
                    'checksum': self._get_checksum_from_release(release_info)
                }
            else:
                self.logger.info(f"Versão atual ({current_version}) está atualizada")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar atualizações: {e}")
            return None
    
    def _is_newer_version(self, new_version: str, current_version: str) -> bool:
        """
        Compara se a nova versão é mais recente
        
        Args:
            new_version: Nova versão (ex: "1.2.3")
            current_version: Versão atual (ex: "1.1.0")
            
        Returns:
            True se a nova versão é mais recente
        """
        try:
            def version_tuple(v):
                return tuple(map(int, v.split('.')))
            
            return version_tuple(new_version) > version_tuple(current_version)
        except:
            return False
    
    def _get_download_url(self, release_info: Dict) -> Optional[str]:
        """
        Extrai URL de download do release
        
        Args:
            release_info: Informações do release do GitHub
            
        Returns:
            URL de download ou None
        """
        assets = release_info.get('assets', [])
        
        # Procurar por arquivo .zip
        for asset in assets:
            if asset.get('name', '').endswith('.zip'):
                return asset.get('browser_download_url')
        
        # Fallback para zipball_url
        return release_info.get('zipball_url')
    
    def _get_checksum_from_release(self, release_info: Dict) -> Optional[str]:
        """
        Extrai checksum do release (se disponível)
        
        Args:
            release_info: Informações do release
            
        Returns:
            Checksum SHA256 ou None
        """
        # Procurar por arquivo de checksum nos assets
        assets = release_info.get('assets', [])
        for asset in assets:
            name = asset.get('name', '').lower()
            if 'sha256' in name or 'checksum' in name:
                try:
                    checksum_url = asset.get('browser_download_url')
                    response = requests.get(checksum_url, timeout=10)
                    return response.text.strip().split()[0]  # Primeiro hash
                except:
                    continue
        return None
    
    def create_backup(self) -> Optional[str]:
        """
        Cria backup da versão atual
        
        Returns:
            Caminho do backup criado ou None em caso de erro
        """
        try:
            version_info = self.load_version_info()
            current_version = version_info.get('version', 'unknown')
            timestamp = datetime.now(SAO_PAULO_TZ).strftime('%Y%m%d_%H%M%S')
            
            backup_name = f"backup_v{current_version}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_name
            
            self.logger.info(f"Criando backup em: {backup_path}")
            
            # Arquivos a serem incluídos no backup
            files_to_backup = [
                'notebook_monitor_service.py',
                'version.json',
                '.env',
                'requirements.txt',
                'database_schema.sql'
            ]
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_name in files_to_backup:
                    file_path = self.base_dir / file_name
                    if file_path.exists():
                        zipf.write(file_path, file_name)
                        self.logger.debug(f"Adicionado ao backup: {file_name}")
            
            self.logger.info(f"Backup criado com sucesso: {backup_path}")
            
            # Limpar backups antigos
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return None
    
    def download_update(self, update_info: Dict) -> Optional[str]:
        """
        Baixa a atualização
        
        Args:
            update_info: Informações da atualização
            
        Returns:
            Caminho do arquivo baixado ou None em caso de erro
        """
        try:
            download_url = update_info.get('download_url')
            if not download_url:
                self.logger.error("URL de download não encontrada")
                return None
            
            # Criar diretório temporário
            self.temp_dir.mkdir(exist_ok=True)
            
            # Nome do arquivo
            version = update_info.get('version', 'unknown')
            download_file = self.temp_dir / f"update_v{version}.zip"
            
            self.logger.info(f"Baixando atualização de: {download_url}")
            
            # Download com progress
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log a cada MB
                                self.logger.info(f"Download: {progress:.1f}% ({downloaded}/{total_size} bytes)")
            
            self.logger.info(f"Download concluído: {download_file}")
            
            # Verificar checksum se disponível
            expected_checksum = update_info.get('checksum')
            if expected_checksum:
                if not self._verify_checksum(download_file, expected_checksum):
                    self.logger.error("Checksum da atualização não confere")
                    download_file.unlink()  # Remover arquivo corrompido
                    return None
            
            return str(download_file)
            
        except Exception as e:
            self.logger.error(f"Erro ao baixar atualização: {e}")
            return None
    
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """
        Verifica o checksum SHA256 do arquivo
        
        Args:
            file_path: Caminho do arquivo
            expected_checksum: Checksum esperado
            
        Returns:
            True se o checksum confere
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar checksum: {e}")
            return False
    
    def install_update(self, update_file: str, update_info: Dict) -> bool:
        """
        Instala a atualização
        
        Args:
            update_file: Caminho do arquivo de atualização
            update_info: Informações da atualização
            
        Returns:
            True se a instalação foi bem-sucedida
        """
        try:
            self.logger.info("Iniciando instalação da atualização")
            
            # Parar o serviço
            if not self._stop_service():
                self.logger.error("Falha ao parar o serviço")
                return False
            
            # Extrair atualização
            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(update_file, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            # Encontrar diretório principal (pode estar em subdiretório)
            main_dir = self._find_main_directory(extract_dir)
            if not main_dir:
                self.logger.error("Diretório principal não encontrado na atualização")
                return False
            
            # Copiar arquivos atualizados
            files_to_update = [
                'notebook_monitor_service.py',
                'requirements.txt',
                'database_schema.sql'
            ]
            
            for file_name in files_to_update:
                src_file = main_dir / file_name
                dst_file = self.base_dir / file_name
                
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
                    self.logger.info(f"Arquivo atualizado: {file_name}")
            
            # Atualizar version.json
            version_info = self.load_version_info()
            version_info['version'] = update_info.get('version')
            version_info['build_date'] = datetime.now(SAO_PAULO_TZ).isoformat()
            version_info['last_update'] = datetime.now(SAO_PAULO_TZ).isoformat()
            self.save_version_info(version_info)
            
            self.logger.info("Atualização instalada com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao instalar atualização: {e}")
            return False
    
    def validate_update(self) -> bool:
        """
        Valida se a atualização foi bem-sucedida
        
        Returns:
            True se a validação passou
        """
        try:
            self.logger.info("Validando atualização")
            
            # Tentar iniciar o serviço
            if not self._start_service():
                self.logger.error("Falha ao iniciar serviço após atualização")
                return False
            
            # Aguardar um pouco para o serviço inicializar
            time.sleep(10)
            
            # Verificar se o serviço está rodando
            if not self._is_service_running():
                self.logger.error("Serviço não está rodando após atualização")
                return False
            
            # Verificar logs por erros críticos
            if self._has_critical_errors_in_logs():
                self.logger.error("Erros críticos encontrados nos logs")
                return False
            
            self.logger.info("Validação da atualização bem-sucedida")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação da atualização: {e}")
            return False
    
    def rollback_update(self, backup_path: str) -> bool:
        """
        Faz rollback para a versão anterior
        
        Args:
            backup_path: Caminho do backup
            
        Returns:
            True se o rollback foi bem-sucedido
        """
        try:
            self.logger.warning("Iniciando rollback da atualização")
            
            # Parar o serviço
            self._stop_service()
            
            # Restaurar arquivos do backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(self.base_dir)
            
            # Tentar iniciar o serviço
            if self._start_service():
                self.logger.info("Rollback concluído com sucesso")
                return True
            else:
                self.logger.error("Falha ao iniciar serviço após rollback")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no rollback: {e}")
            return False
    
    def _stop_service(self) -> bool:
        """
        Para o serviço Windows
        
        Returns:
            True se parou com sucesso
        """
        try:
            result = subprocess.run(
                ['sc', 'stop', self.service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Aguardar o serviço parar
            time.sleep(5)
            
            return result.returncode == 0 or "service is not started" in result.stderr.lower()
            
        except Exception as e:
            self.logger.error(f"Erro ao parar serviço: {e}")
            return False
    
    def _start_service(self) -> bool:
        """
        Inicia o serviço Windows
        
        Returns:
            True se iniciou com sucesso
        """
        try:
            result = subprocess.run(
                ['sc', 'start', self.service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar serviço: {e}")
            return False
    
    def _is_service_running(self) -> bool:
        """
        Verifica se o serviço está rodando
        
        Returns:
            True se está rodando
        """
        try:
            result = subprocess.run(
                ['sc', 'query', self.service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return "RUNNING" in result.stdout
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do serviço: {e}")
            return False
    
    def _has_critical_errors_in_logs(self) -> bool:
        """
        Verifica se há erros críticos nos logs recentes
        
        Returns:
            True se há erros críticos
        """
        try:
            log_file = self.base_dir / "notebook_monitor.log"
            if not log_file.exists():
                return False
            
            # Tentar diferentes codificações para ler o arquivo de log
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            lines = []
            
            for encoding in encodings:
                try:
                    with open(log_file, 'r', encoding=encoding, errors='ignore') as f:
                        lines = f.readlines()[-50:]  # Últimas 50 linhas
                    break  # Se conseguiu ler, sair do loop
                except UnicodeDecodeError:
                    continue  # Tentar próxima codificação
            
            if not lines:
                # Se não conseguiu ler com nenhuma codificação, tentar modo binário
                try:
                    with open(log_file, 'rb') as f:
                        content = f.read()
                        # Decodificar ignorando erros
                        text_content = content.decode('utf-8', errors='ignore')
                        lines = text_content.split('\n')[-50:]
                except Exception:
                    self.logger.warning("Não foi possível ler o arquivo de log")
                    return False
            
            # Procurar por erros críticos
            critical_patterns = [
                'CRITICAL',
                'FATAL',
                'Exception',
                'Error',
                'Failed to start',
                'Connection failed'
            ]
            
            recent_time = datetime.now(SAO_PAULO_TZ) - timedelta(minutes=5)
            
            for line in lines:
                # Verificar se é uma linha recente (últimos 5 minutos)
                if any(pattern in line for pattern in critical_patterns):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar logs: {e}")
            return True  # Assumir erro se não conseguir verificar
    
    def _find_main_directory(self, extract_dir: Path) -> Optional[Path]:
        """
        Encontra o diretório principal na extração
        
        Args:
            extract_dir: Diretório de extração
            
        Returns:
            Caminho do diretório principal ou None
        """
        # Procurar por arquivo principal
        for root, dirs, files in os.walk(extract_dir):
            if 'notebook_monitor_service.py' in files:
                return Path(root)
        
        # Se não encontrou, usar o próprio diretório de extração
        return extract_dir
    
    def _cleanup_old_backups(self):
        """
        Remove backups antigos baseado na configuração de retenção
        """
        try:
            version_info = self.load_version_info()
            retention_days = version_info.get('backup_retention_days', 7)
            
            cutoff_date = datetime.now(SAO_PAULO_TZ) - timedelta(days=retention_days)
            
            for backup_file in self.backup_dir.glob('backup_*.zip'):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    self.logger.info(f"Backup antigo removido: {backup_file.name}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao limpar backups antigos: {e}")
    
    def cleanup_temp_files(self):
        """
        Remove arquivos temporários
        """
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.info("Arquivos temporários removidos")
        except Exception as e:
            self.logger.error(f"Erro ao remover arquivos temporários: {e}")
    
    def perform_update(self) -> bool:
        """
        Executa o processo completo de atualização
        
        Returns:
            True se a atualização foi bem-sucedida
        """
        backup_path = None
        update_file = None
        
        try:
            self.logger.info("=== Iniciando processo de atualização ===")
            
            # 1. Verificar se há atualizações
            update_info = self.check_for_updates()
            if not update_info:
                self.logger.info("Nenhuma atualização disponível")
                return True
            
            self.logger.info(f"Nova versão encontrada: {update_info['version']}")
            
            # 2. Criar backup
            backup_path = self.create_backup()
            if not backup_path:
                self.logger.error("Falha ao criar backup")
                return False
            
            # 3. Baixar atualização
            update_file = self.download_update(update_info)
            if not update_file:
                self.logger.error("Falha ao baixar atualização")
                return False
            
            # 4. Instalar atualização
            if not self.install_update(update_file, update_info):
                self.logger.error("Falha ao instalar atualização")
                return False
            
            # 5. Validar atualização
            if not self.validate_update():
                self.logger.error("Validação da atualização falhou")
                
                # 6. Fazer rollback se a validação falhou
                if backup_path and self.rollback_update(backup_path):
                    self.logger.info("Rollback realizado com sucesso")
                else:
                    self.logger.error("Falha no rollback - intervenção manual necessária")
                
                return False
            
            self.logger.info("=== Atualização concluída com sucesso ===")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro no processo de atualização: {e}")
            
            # Tentar rollback em caso de erro
            if backup_path:
                self.rollback_update(backup_path)
            
            return False
            
        finally:
            # Limpar arquivos temporários
            self.cleanup_temp_files()


def main():
    """
    Função principal para teste do sistema de atualização
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('auto_updater.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    updater = AutoUpdater()
    
    # Verificar atualizações
    update_info = updater.check_for_updates()
    if update_info:
        print(f"Nova versão disponível: {update_info['version']}")
        
        # Perguntar se deve atualizar (em produção seria automático)
        response = input("Deseja atualizar? (s/n): ")
        if response.lower() == 's':
            success = updater.perform_update()
            if success:
                print("Atualização concluída com sucesso!")
            else:
                print("Falha na atualização")
    else:
        print("Sistema está atualizado")


if __name__ == "__main__":
    main()