import subprocess
import sys
import importlib
import os

def check_admin_rights():
    """Verifica se está executando como administrador"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_package(package):
    """Instala um pacote Python"""
    try:
        print(f"Instalando {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"✓ {package} instalado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao instalar {package}: {e}")
        return False

def configure_pywin32():
    """Configura o pywin32 após instalação"""
    try:
        print("Configurando pywin32...")
        subprocess.check_call([sys.executable, '-m', 'pywin32_postinstall', '-install'])
        print("✓ pywin32 configurado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao configurar pywin32: {e}")
        return False

def test_import(module_name):
    """Testa se um módulo pode ser importado"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name} importado com sucesso")
        return True
    except ImportError:
        print(f"✗ Erro ao importar {module_name}")
        return False

def main():
    print("=== Configurador de Dependências - Monitoramento de Notebooks ===")
    print()
    
    # Verifica privilégios de administrador
    if not check_admin_rights():
        print("AVISO: Recomenda-se executar como Administrador para evitar problemas de permissão.")
        print()
    
    # Lista de pacotes para instalar
    packages = [
        'pywin32==306',
        'requests==2.31.0', 
        'psycopg2-binary==2.9.9',
        'python-dotenv==1.0.0',
        'sqlalchemy==2.0.23',
        'pytz==2023.3'
    ]
    
    print("Instalando dependências...")
    print()
    
    failed_packages = []
    
    # Instala cada pacote
    for package in packages:
        if not install_package(package):
            failed_packages.append(package)
    
    print()
    
    # Configura pywin32 se foi instalado com sucesso
    if 'pywin32==306' not in failed_packages:
        configure_pywin32()
        print()
    
    # Testa importações críticas
    print("Testando importações...")
    critical_modules = [
        'win32serviceutil',
        'psycopg2',
        'requests',
        'dotenv',
        'pytz'
    ]
    
    failed_imports = []
    for module in critical_modules:
        if not test_import(module):
            failed_imports.append(module)
    
    print()
    
    # Relatório final
    if failed_packages or failed_imports:
        print("❌ INSTALAÇÃO INCOMPLETA")
        if failed_packages:
            print(f"Pacotes que falharam: {', '.join(failed_packages)}")
        if failed_imports:
            print(f"Módulos que não puderam ser importados: {', '.join(failed_imports)}")
        print()
        print("Soluções:")
        print("1. Execute como Administrador")
        print("2. Atualize o pip: python -m pip install --upgrade pip")
        print("3. Instale manualmente: pip install <nome_do_pacote>")
    else:
        print("✅ TODAS AS DEPENDÊNCIAS INSTALADAS COM SUCESSO!")
        print()
        print("Próximos passos:")
        print("1. Configure o arquivo .env com as credenciais do PostgreSQL")
        print("2. Execute o script database_schema.sql no PostgreSQL")
        print("3. Execute: python install_service.py")
    
    print()
    input("Pressione Enter para sair...")

if __name__ == '__main__':
    main()