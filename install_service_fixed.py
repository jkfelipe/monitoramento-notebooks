import os
import sys
import subprocess
import win32serviceutil
from dotenv import load_dotenv
import psycopg2

def check_env_file():
    """Verifica se o arquivo .env existe e está configurado"""
    env_path = '.env'
    if not os.path.exists(env_path):
        print("ERRO: Arquivo .env não encontrado!")
        return False
        
    load_dotenv()
    
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            
    if missing_vars:
        print(f"ERRO: Variáveis obrigatórias não configuradas no .env: {', '.join(missing_vars)}")
        return False
        
    return True

def test_database_connection():
    """Testa a conexão com o PostgreSQL"""
    print("Testando conexão com PostgreSQL...")
    try:
        load_dotenv()
        
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'disable')
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'monitoring_data'
            )
        """)
        
        table_exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if table_exists:
            print("✅ Conexão com PostgreSQL estabelecida e tabela encontrada!")
        else:
            print("⚠️ AVISO: Conexão estabelecida, mas tabela 'monitoring_data' não encontrada.")
            print("Execute o script database_schema.sql no PostgreSQL antes de continuar.")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {e}")
        print("Verifique as configurações no arquivo .env")
        return False

def install_service():
    """Instala o serviço usando linha de comando"""
    print("Instalando serviço Windows...")
    try:
        # Instala o serviço usando linha de comando
        cmd = [sys.executable, 'notebook_monitor_service.py', 'install']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Serviço instalado com sucesso!")
            
            # Inicia o serviço
            start_cmd = [sys.executable, 'notebook_monitor_service.py', 'start']
            start_result = subprocess.run(start_cmd, capture_output=True, text=True)
            
            if start_result.returncode == 0:
                print("✅ Serviço iniciado com sucesso!")
            else:
                print(f"⚠️ Serviço instalado, mas erro ao iniciar: {start_result.stderr}")
                print("Tente iniciar manualmente: net start NotebookMonitorService")
        else:
            print(f"❌ Erro ao instalar serviço: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao instalar serviço: {e}")
        return False
    return True

def main():
    """Função principal de instalação"""
    print("=== Instalador do Serviço de Monitoramento de Notebooks (PostgreSQL) ===")
    print()
    
    # Verifica se está executando como administrador
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("❌ ERRO: Este script deve ser executado como Administrador!")
            print("Clique com o botão direito no Prompt de Comando e selecione 'Executar como administrador'")
            input("Pressione Enter para sair...")
            return
    except:
        pass
    
    # Verifica arquivo .env
    if not check_env_file():
        input("Pressione Enter para sair...")
        return
    
    # Testa conexão com banco
    if not test_database_connection():
        input("Pressione Enter para sair...")
        return
    
    print()
    
    # Instala serviço
    if not install_service():
        input("Pressione Enter para sair...")
        return
    
    print()
    print("🎉 === Instalação Concluída ===")
    print("O serviço está agora instalado e em execução com PostgreSQL.")
    print(f"Intervalo de coleta: {os.getenv('MONITOR_INTERVAL', 300)} segundos")
    print()
    print("📋 Para gerenciar o serviço:")
    print("- Parar: net stop NotebookMonitorService")
    print("- Iniciar: net start NotebookMonitorService")
    print("- Desinstalar: python notebook_monitor_service.py remove")
    print()
    print("📊 Para consultar dados:")
    print("- Resumo: python query_data.py --summary")
    print("- Por dispositivo: python query_data.py --hostname NOME_PC")
    print("- Análise de redes: python query_data.py --networks")
    print()
    input("Pressione Enter para sair...")

if __name__ == '__main__':
    main()