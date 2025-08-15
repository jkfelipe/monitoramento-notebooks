-- Criação do banco de dados (execute como superusuário)
-- CREATE DATABASE monitoramento_notebooks;
-- CREATE USER monitor_user WITH PASSWORD 'sua_senha_segura';
-- GRANT ALL PRIVILEGES ON DATABASE monitoramento_notebooks TO monitor_user;

-- Conecte ao banco monitoramento_notebooks e execute:

-- Extensão para UUID (opcional)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela principal de monitoramento
CREATE TABLE IF NOT EXISTS monitoring_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    external_ip INET,
    connected_wifi VARCHAR(255),
    available_networks JSONB,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_accuracy DECIMAL(10, 2),
    uptime_seconds BIGINT,
    os_version VARCHAR(500),
    last_boot_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_monitoring_hostname ON monitoring_data(hostname);
CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp ON monitoring_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_monitoring_hostname_timestamp ON monitoring_data(hostname, timestamp);
CREATE INDEX IF NOT EXISTS idx_monitoring_external_ip ON monitoring_data(external_ip);
CREATE INDEX IF NOT EXISTS idx_monitoring_location ON monitoring_data(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para atualizar updated_at
CREATE TRIGGER update_monitoring_data_updated_at 
    BEFORE UPDATE ON monitoring_data 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Tabela para log de eventos (opcional)
CREATE TABLE IF NOT EXISTS monitoring_events (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_hostname ON monitoring_events(hostname);
CREATE INDEX IF NOT EXISTS idx_events_type ON monitoring_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON monitoring_events(timestamp);

-- View para últimos dados por hostname
CREATE OR REPLACE VIEW latest_monitoring_data AS
SELECT DISTINCT ON (hostname) 
    id, timestamp, hostname, username, external_ip, 
    connected_wifi, available_networks, latitude, longitude,
    location_accuracy, uptime_seconds, os_version, last_boot_time
FROM monitoring_data 
ORDER BY hostname, timestamp DESC;

-- Permissões para o usuário monitor_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO monitor_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO monitor_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO monitor_user;