import psycopg2
import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Configurações do banco
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monitoramento_notebooks'),
    'user': os.getenv('DB_USER', 'monitor_user'),
    'password': os.getenv('DB_PASSWORD', 'uma_senha_segura'),
    'sslmode': os.getenv('DB_SSL_MODE', 'disable')
}

print("Configurações do banco:")
for key, value in db_config.items():
    if key == 'password':
        print(f"{key}: {'*' * len(str(value))}")
    else:
        print(f"{key}: {value}")

try:
    print("\nTentando conectar ao PostgreSQL...")
    conn = psycopg2.connect(**db_config)
    print("✅ Conexão bem-sucedida!")
    
    # Testar se a tabela existe
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM monitoring_data;")
    count = cursor.fetchone()[0]
    print(f"✅ Tabela monitoring_data encontrada com {count} registros")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro na conexão: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O usuário 'monitor_user' existe")
    print("3. A senha está correta")
    print("4. O banco 'monitoramento_notebooks' existe")