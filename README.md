# Sistema de Monitoramento de Notebooks - PostgreSQL

Sistema para monitoramento automático de notebooks da empresa, coletando informações de localização, rede, IP externo, tempo de atividade e usuário logado. **Versão atualizada com PostgreSQL e totalmente funcional.**

## ✅ Status do Projeto

**🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!**

- ✅ Serviço Windows instalado e rodando
- ✅ PostgreSQL conectado e armazenando dados
- ✅ Coleta automática a cada 5 minutos
- ✅ Logs funcionando corretamente
- ✅ Todas as dependências resolvidas

## Funcionalidades

- **Execução como Serviço Windows**: Inicia automaticamente com o sistema
- **Banco PostgreSQL**: Dados centralizados e seguros (local ou remoto)
- **Coleta Periódica**: Dados coletados a cada 5 minutos (configurável)
- **Timezone Brasil**: Timestamps com fuso horário America/Sao_Paulo
- **Logging Completo**: Sistema de logs detalhado para monitoramento
- **Configuração via .env**: Fácil configuração sem alterar código
- **Scripts de Instalação**: Instalação automatizada com verificações

### 📊 Informações Coletadas

- **🌍 Localização**: Latitude/longitude aproximada via IP
- **📶 Rede WiFi**: Nome da rede conectada e redes disponíveis
- **🌐 IP Externo**: Endereço IP público atual
- **💻 Sistema**: Hostname, usuário, tempo de atividade, versão do OS
- **⏰ Timestamps**: Com timezone America/Sao_Paulo
- **🔄 Histórico**: Dados históricos para análise de padrões

## Pré-requisitos

- **Python 3.7 a 3.11** (recomendado: Python 3.10 ou 3.11)
- Windows 10/11
- Privilégios de administrador
- **PostgreSQL** (local ou remoto)
- Conectividade com o servidor PostgreSQL

### ⚠️ Importante sobre Versões do Python

- **Python 3.13**: ❌ Não recomendado (problemas de compatibilidade com pywin32)
- **Python 3.12**: ⚠️ Compatibilidade limitada
- **Python 3.10/3.11**: ✅ **Versões recomendadas** para melhor estabilidade
- **Python 3.7-3.9**: ✅ Compatíveis e testadas

## Instalação Rápida (Sistema Funcionando)

### 1. Configurar PostgreSQL

**Criar usuário e banco:**
```sql
CREATE USER monitor_user WITH PASSWORD 'uma_senha_segura';
CREATE DATABASE monitoramento_notebooks OWNER monitor_user;
GRANT ALL PRIVILEGES ON DATABASE monitoramento_notebooks TO monitor_user;
```

**Executar schema:**
```bash
psql -U monitor_user -d monitoramento_notebooks -h localhost -f database_schema.sql
```

### 2. Configurar arquivo .env

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monitoramento_notebooks
DB_USER=monitor_user
DB_PASSWORD=uma_senha_segura
DB_SSL_MODE=disable
MONITOR_INTERVAL=300
LOG_LEVEL=INFO
```

### 3. Instalar e Iniciar (Como Administrador)

```bash
# Instalar dependências
python setup_dependencies.py

# Instalar serviço (usar versão corrigida)
python install_service_fixed.py

# Verificar status
sc query NotebookMonitorService
```

## Gerenciamento do Serviço

### Comandos Básicos

```bash
# Verificar status
sc query NotebookMonitorService

# Parar serviço
sc stop NotebookMonitorService

# Iniciar serviço
sc start NotebookMonitorService

# Reiniciar serviço
sc stop NotebookMonitorService && sc start NotebookMonitorService

# Desinstalar serviço
sc stop NotebookMonitorService && sc delete NotebookMonitorService
```

### Verificar Funcionamento

```bash
# Testar conexão com banco
python test_connection_manual.py

# Consultar dados coletados
python query_data.py

# Verificar logs
type notebook_monitor.log
```

## Consultar Dados Coletados

### Scripts Disponíveis

```bash
# Consulta básica dos dados
python query_data.py

# Teste de conexão manual
python test_connection_manual.py

# Verificar logs do sistema
type notebook_monitor.log
```

### Consultas SQL Diretas

```sql
-- Últimos 10 registros
SELECT * FROM monitoring_data ORDER BY timestamp DESC LIMIT 10;

-- Dispositivos ativos hoje
SELECT DISTINCT hostname, MAX(timestamp) as last_seen
FROM monitoring_data 
WHERE DATE(timestamp) = CURRENT_DATE
GROUP BY hostname;

-- Redes WiFi utilizadas
SELECT connected_wifi, COUNT(*) as frequencia
FROM monitoring_data 
WHERE connected_wifi IS NOT NULL
GROUP BY connected_wifi
ORDER BY frequencia DESC;
```

## Estrutura do Banco PostgreSQL

### Tabela Principal
```sql
CREATE TABLE monitoring_data (
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
```

### Índices para Performance
- `idx_monitoring_hostname`: Por hostname
- `idx_monitoring_timestamp`: Por timestamp
- `idx_monitoring_hostname_timestamp`: Consultas combinadas
- `idx_monitoring_external_ip`: Por IP externo
- `idx_monitoring_location`: Por coordenadas geográficas

## Configurações (.env)

| Variável | Descrição | Valor Padrão | Exemplo |
|----------|-----------|--------------|----------|
| `DB_HOST` | Servidor PostgreSQL | localhost | localhost |
| `DB_PORT` | Porta do PostgreSQL | 5432 | 5432 |
| `DB_NAME` | Nome do banco | monitoramento_notebooks | monitoramento_notebooks |
| `DB_USER` | Usuário do banco | postgres | monitor_user |
| `DB_PASSWORD` | Senha do banco | (obrigatório) | uma_senha_segura |
| `DB_SSL_MODE` | Modo SSL | prefer | disable (local) |
| `MONITOR_INTERVAL` | Intervalo em segundos | 300 | 300 (5 min) |
| `LOG_LEVEL` | Nível de log | INFO | INFO |

## Arquivos do Projeto

### Scripts Principais
- `notebook_monitor_service.py` - Serviço Windows principal
- `install_service_fixed.py` - **Script de instalação corrigido (usar este)**
- `setup_dependencies.py` - Instalador de dependências
- `query_data.py` - Consulta de dados coletados
- `test_connection_manual.py` - Teste de conexão com PostgreSQL

### Arquivos de Configuração
- `.env` - Configurações do sistema
- `database_schema.sql` - Estrutura do banco de dados
- `requirements.txt` - Dependências Python

### Logs e Cache
- `notebook_monitor.log` - Log de atividades do serviço
- `__pycache__/` - Cache Python (gerado automaticamente)

## Solução de Problemas Resolvidos

### ✅ Problema: "No module named pywin32_postinstall"
**Solução implementada:** Script `setup_dependencies.py` com instalação alternativa do pywin32

### ✅ Problema: "fe_sendauth: no password supplied"
**Solução implementada:** Correção do carregamento do arquivo .env com caminho absoluto

### ✅ Problema: "_svc_reg_class_ not found"
**Solução implementada:** Script `install_service_fixed.py` com método de instalação robusto

### ✅ Problema: Serviço não carrega configurações
**Solução implementada:** Carregamento do .env com caminho absoluto no serviço

## Monitoramento e Manutenção

### Verificações Regulares

```bash
# Status do serviço (deve mostrar RUNNING)
sc query NotebookMonitorService

# Últimas linhas do log
type notebook_monitor.log | findstr /C:"ERROR" /C:"INFO"

# Verificar se dados estão sendo coletados
python test_connection_manual.py
```

### Backup do Banco

```bash
# Backup completo
pg_dump -h localhost -U monitor_user -d monitoramento_notebooks > backup_$(date +%Y%m%d).sql

# Backup apenas dados
pg_dump -h localhost -U monitor_user -d monitoramento_notebooks --data-only > dados_backup.sql
```

## Segurança e Privacidade

- **🔒 Credenciais**: Armazenadas localmente no arquivo .env
- **🌐 SSL**: Suporte a conexões criptografadas (configurável)
- **📍 Localização**: Aproximada via IP (não GPS)
- **👤 Privacidade**: Não coleta informações pessoais sensíveis
- **🔐 Acesso**: Serviço roda com credenciais do sistema

## Próximos Passos Recomendados

1. **📊 Monitoramento**: Deixar o sistema coletar dados por alguns dias
2. **📈 Análise**: Usar `query_data.py` para analisar padrões
3. **🔄 Backup**: Configurar backup automático do PostgreSQL
4. **📋 Documentação**: Manter registro das configurações
5. **🔧 Manutenção**: Monitorar logs regularmente

## Suporte Técnico

### Para Problemas:
1. **Verificar logs**: `type notebook_monitor.log`
2. **Testar conexão**: `python test_connection_manual.py`
3. **Verificar serviço**: `sc query NotebookMonitorService`
4. **Reinstalar se necessário**: `python install_service_fixed.py`

### Contatos de Suporte
- **Logs do Sistema**: `notebook_monitor.log`
- **Teste de Conexão**: `test_connection_manual.py`
- **Configurações**: Arquivo `.env`

---

**🎉 Sistema Totalmente Funcional e Coletando Dados Automaticamente!**

*Última atualização: Sistema instalado e funcionando perfeitamente*