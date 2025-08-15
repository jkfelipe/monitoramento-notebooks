import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
import pytz

class NotebookDataQuery:
    """Classe para consultar dados de monitoramento dos notebooks no PostgreSQL"""
    
    def __init__(self):
        # Carrega variáveis de ambiente
        load_dotenv()
        
        # Configurações do banco de dados
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'monitoramento_notebooks'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'sslmode': os.getenv('DB_SSL_MODE', 'prefer')
        }
        
        # Timezone do Brasil
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
    def get_db_connection(self):
        """Obtém conexão com o banco de dados"""
        return psycopg2.connect(**self.db_config)
            
    def get_latest_data(self, hostname=None, limit=10):
        """Obtém os dados mais recentes"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if hostname:
            cursor.execute("""
                SELECT * FROM monitoring_data 
                WHERE hostname = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (hostname, limit))
        else:
            cursor.execute("""
                SELECT * FROM monitoring_data 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (limit,))
            
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return self._format_results(results)
        
    def get_data_by_date_range(self, start_date, end_date, hostname=None):
        """Obtém dados por período"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if hostname:
            cursor.execute("""
                SELECT * FROM monitoring_data 
                WHERE hostname = %s AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp DESC
            """, (hostname, start_date, end_date))
        else:
            cursor.execute("""
                SELECT * FROM monitoring_data 
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp DESC
            """, (start_date, end_date))
            
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return self._format_results(results)
        
    def get_unique_hostnames(self):
        """Obtém lista de hostnames únicos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT hostname FROM monitoring_data ORDER BY hostname')
        results = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        return results
        
    def get_location_history(self, hostname, days=7):
        """Obtém histórico de localização"""
        start_date = datetime.now(self.timezone) - timedelta(days=days)
        
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT timestamp, latitude, longitude, connected_wifi, external_ip
            FROM monitoring_data 
            WHERE hostname = %s AND timestamp >= %s AND latitude IS NOT NULL
            ORDER BY timestamp DESC
        """, (hostname, start_date))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [{
            'timestamp': row['timestamp'],
            'latitude': float(row['latitude']) if row['latitude'] else None,
            'longitude': float(row['longitude']) if row['longitude'] else None,
            'wifi': row['connected_wifi'],
            'external_ip': str(row['external_ip']) if row['external_ip'] else None
        } for row in results]
        
    def get_network_analysis(self, hostname=None, days=30):
        """Análise de redes WiFi utilizadas"""
        start_date = datetime.now(self.timezone) - timedelta(days=days)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if hostname:
            cursor.execute("""
                SELECT connected_wifi, COUNT(*) as frequency,
                       MIN(timestamp) as first_seen,
                       MAX(timestamp) as last_seen
                FROM monitoring_data 
                WHERE hostname = %s AND timestamp >= %s 
                      AND connected_wifi IS NOT NULL
                GROUP BY connected_wifi
                ORDER BY frequency DESC
            """, (hostname, start_date))
        else:
            cursor.execute("""
                SELECT hostname, connected_wifi, COUNT(*) as frequency,
                       MIN(timestamp) as first_seen,
                       MAX(timestamp) as last_seen
                FROM monitoring_data 
                WHERE timestamp >= %s AND connected_wifi IS NOT NULL
                GROUP BY hostname, connected_wifi
                ORDER BY hostname, frequency DESC
            """, (start_date,))
            
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return results
        
    def _format_results(self, results):
        """Formata resultados da consulta"""
        formatted_results = []
        for row in results:
            result_dict = dict(row)
            
            # Parse JSON fields
            if result_dict.get('available_networks'):
                try:
                    if isinstance(result_dict['available_networks'], str):
                        result_dict['available_networks'] = json.loads(result_dict['available_networks'])
                except:
                    result_dict['available_networks'] = []
                    
            # Format uptime
            if result_dict.get('uptime_seconds'):
                hours = result_dict['uptime_seconds'] // 3600
                minutes = (result_dict['uptime_seconds'] % 3600) // 60
                result_dict['uptime_formatted'] = f"{hours}h {minutes}m"
                
            # Convert IP to string if needed
            if result_dict.get('external_ip'):
                result_dict['external_ip'] = str(result_dict['external_ip'])
                
            formatted_results.append(result_dict)
            
        return formatted_results
        
    def print_summary(self):
        """Imprime resumo dos dados"""
        try:
            hostnames = self.get_unique_hostnames()
            
            print("=== Resumo do Monitoramento de Notebooks (PostgreSQL) ===")
            print(f"Total de dispositivos monitorados: {len(hostnames)}")
            print()
            
            for hostname in hostnames:
                latest = self.get_latest_data(hostname, 1)
                if latest:
                    data = latest[0]
                    print(f"Dispositivo: {hostname}")
                    print(f"  Usuário: {data['username']}")
                    print(f"  Última atualização: {data['timestamp']}")
                    print(f"  IP Externo: {data['external_ip']}")
                    print(f"  WiFi Conectado: {data['connected_wifi'] or 'Não conectado'}")
                    if data['latitude']:
                        print(f"  Localização: {data['latitude']}, {data['longitude']}")
                    else:
                        print("  Localização: Não disponível")
                    print(f"  Tempo ativo: {data.get('uptime_formatted', 'N/A')}")
                    print()
                    
        except Exception as e:
            print(f"Erro ao conectar com o banco de dados: {e}")
            print("Verifique se o arquivo .env está configurado corretamente.")

def main():
    parser = argparse.ArgumentParser(description='Consultar dados de monitoramento de notebooks (PostgreSQL)')
    parser.add_argument('--hostname', help='Filtrar por hostname específico')
    parser.add_argument('--days', type=int, default=7, help='Número de dias para consulta (padrão: 7)')
    parser.add_argument('--limit', type=int, default=10, help='Limite de registros (padrão: 10)')
    parser.add_argument('--summary', action='store_true', help='Mostrar resumo de todos os dispositivos')
    parser.add_argument('--location', action='store_true', help='Mostrar histórico de localização')
    parser.add_argument('--networks', action='store_true', help='Análise de redes WiFi utilizadas')
    
    args = parser.parse_args()
    
    try:
        query = NotebookDataQuery()
        
        if args.summary:
            query.print_summary()
        elif args.location and args.hostname:
            locations = query.get_location_history(args.hostname, args.days)
            print(f"=== Histórico de Localização - {args.hostname} ===")
            for loc in locations:
                print(f"{loc['timestamp']}: {loc['latitude']}, {loc['longitude']} (WiFi: {loc['wifi']}, IP: {loc['external_ip']})")
        elif args.networks:
            networks = query.get_network_analysis(args.hostname, args.days)
            if args.hostname:
                print(f"=== Análise de Redes WiFi - {args.hostname} ===")
                for net in networks:
                    print(f"WiFi: {net[0]} - Frequência: {net[1]} - Primeiro uso: {net[2]} - Último uso: {net[3]}")
            else:
                print("=== Análise de Redes WiFi - Todos os dispositivos ===")
                for net in networks:
                    print(f"Dispositivo: {net[0]} - WiFi: {net[1]} - Frequência: {net[2]}")
        else:
            if args.hostname:
                print(f"=== Dados do dispositivo: {args.hostname} ===")
            else:
                print("=== Últimos dados coletados ===")
                
            data = query.get_latest_data(args.hostname, args.limit)
            
            for record in data:
                print(f"Timestamp: {record['timestamp']}")
                print(f"Dispositivo: {record['hostname']} (Usuário: {record['username']})")
                print(f"IP Externo: {record['external_ip']}")
                print(f"WiFi: {record['connected_wifi'] or 'Não conectado'}")
                if record['latitude']:
                    print(f"Localização: {record['latitude']}, {record['longitude']}")
                print(f"Tempo ativo: {record.get('uptime_formatted', 'N/A')}")
                print(f"SO: {record['os_version']}")
                print("-" * 50)
                
    except Exception as e:
        print(f"Erro: {e}")
        print("Verifique se o arquivo .env está configurado corretamente e se o PostgreSQL está acessível.")

if __name__ == '__main__':
    main()