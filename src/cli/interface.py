"""
CLI Interface Module
Kullanıcı etkileşimi ve input toplama
"""

import sys
from typing import Dict, Optional
from colorama import Fore, Style

from ..utils.logger import get_logger
from ..checks.database_check import DatabaseCheck


class CLIInterface:
    """Command-line interface for user interaction"""
    
    DEPLOYMENT_ROLES = {
        '1': ('Combined', 'Intelligence Server + Web Server (aynı sunucu)'),
        '2': ('Web-Only', 'Sadece Web Server'),
        '3': ('IS-Only', 'Sadece Intelligence Server')
    }
    
    DATABASE_TYPES = {
        '1': ('PostgreSQL', 5432),
        '2': ('Oracle', 1521),
        '3': ('SQL Server', 1433),
        '4': ('MySQL', 3306)
    }
    
    def __init__(self):
        self.logger = get_logger()
    
    def print_banner(self):
        """Uygulama başlığı"""
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'  MicroStrategy Linux Installation Helper':^60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    def print_menu(self, title: str, options: Dict):
        """Menü göster"""
        print(f"{Fore.YELLOW}{title}{Style.RESET_ALL}")
        print("-" * 50)
        for key, value in options.items():
            if isinstance(value, tuple):
                name, desc = value
                print(f"  {Fore.GREEN}{key}{Style.RESET_ALL}. {name} - {desc}")
            else:
                print(f"  {Fore.GREEN}{key}{Style.RESET_ALL}. {value}")
        print()
    
    def get_input(self, prompt: str, default: str = None) -> str:
        """Kullanıcı input al"""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        value = input(full_prompt).strip()
        
        if not value and default:
            return default
        
        return value
    
    def get_choice(self, prompt: str, valid_choices: list) -> str:
        """Seçenek al"""
        while True:
            choice = self.get_input(prompt)
            if choice in valid_choices:
                return choice
            print(f"{Fore.RED}Geçersiz seçim! Lütfen {', '.join(valid_choices)} seçeneklerinden birini girin.{Style.RESET_ALL}\n")
    
    def confirm(self, prompt: str, default: bool = True) -> bool:
        """Onay al"""
        default_str = "E/h" if default else "e/H"
        choice = self.get_input(f"{prompt} ({default_str})", "E" if default else "H").upper()
        
        if not choice:
            return default
        
        return choice in ['E', 'Y', 'YES', 'EVET']
    
    def select_deployment_role(self) -> str:
        """Deployment role seçimi"""
        self.print_menu("Deployment Tipi Seçin:", self.DEPLOYMENT_ROLES)
        
        choice = self.get_choice("Seçiminiz", list(self.DEPLOYMENT_ROLES.keys()))
        role, desc = self.DEPLOYMENT_ROLES[choice]
        
        print(f"\n{Fore.GREEN}✓ Seçildi: {role}{Style.RESET_ALL}")
        print(f"  {desc}\n")
        
        return role
    
    def select_database_type(self) -> str:
        """Database tipi seçimi"""
        self.print_menu("Veritabanı Tipi Seçin:", self.DATABASE_TYPES)
        
        choice = self.get_choice("Seçiminiz", list(self.DATABASE_TYPES.keys()))
        db_type, default_port = self.DATABASE_TYPES[choice]
        
        print(f"\n{Fore.GREEN}✓ Seçildi: {db_type}{Style.RESET_ALL}\n")
        
        return db_type
    
    def get_database_config(self) -> Dict:
        """Database bağlantı bilgilerini al"""
        print(f"{Fore.YELLOW}Veritabanı Bağlantı Bilgileri{Style.RESET_ALL}")
        print("-" * 50)
        
        # Database tipi
        db_type = self.select_database_type()
        
        # Default port
        _, default_port = [(v[0], v[1]) for v in self.DATABASE_TYPES.values() if v[0] == db_type][0]
        
        # Host
        host = self.get_input("Database Host", "localhost")
        
        # Port
        port_str = self.get_input(f"Database Port", str(default_port))
        try:
            port = int(port_str)
        except ValueError:
            print(f"{Fore.RED}Geçersiz port, default kullanılıyor: {default_port}{Style.RESET_ALL}")
            port = default_port
        
        # Database name
        database = self.get_input("Database Adı", "metadata")
        
        # Username
        username = self.get_input("Kullanıcı Adı", "mstr_admin")
        
        # Password
        import getpass
        password = getpass.getpass("Şifre: ")
        
        config = {
            'type': db_type,
            'host': host,
            'port': port,
            'database': database,
            'username': username,
            'password': password
        }
        
        print(f"\n{Fore.GREEN}✓ Database bilgileri alındı{Style.RESET_ALL}\n")
        
        return config
    
    def confirm_configuration(self, deployment_role: str, db_config: Dict) -> bool:
        """Konfigürasyonu onaylat"""
        print(f"{Fore.YELLOW}Konfigürasyon Özeti{Style.RESET_ALL}")
        print("=" * 50)
        print(f"Deployment: {Fore.CYAN}{deployment_role}{Style.RESET_ALL}")
        print(f"Database:   {Fore.CYAN}{db_config['type']}{Style.RESET_ALL}")
        print(f"Host:       {db_config['host']}")
        print(f"Port:       {db_config['port']}")
        print(f"Database:   {db_config['database']}")
        print(f"Username:   {db_config['username']}")
        print("=" * 50)
        print()
        
        return self.confirm("Bu ayarlarla devam edilsin mi?", True)
    
    def show_completion(self, success: bool):
        """Tamamlanma mesajı"""
        if success:
            print(f"\n{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'  HAZIRLIK TAMAMLANDI!':^60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}\n")
            print(f"{Fore.YELLOW}Sıradaki adım:{Style.RESET_ALL}")
            print(f"  1. MicroStrategy installer'ı çalıştırın")
            print(f"  2. Kurulum tamamlandığında: {Fore.CYAN}sudo mstr-helper verify{Style.RESET_ALL}\n")
        else:
            print(f"\n{Fore.RED}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.RED}{'  HAZIRLIK TAMAMLANAMADI':^60}{Style.RESET_ALL}")
            print(f"{Fore.RED}{'=' * 60}{Style.RESET_ALL}\n")
            print(f"Lütfen hata mesajlarını kontrol edin ve düzeltin.\n")
    
    def show_verification_complete(self, success: bool):
        """Verification tamamlanma mesajı"""
        if success:
            print(f"\n{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'  DOĞRULAMA BAŞARILI!':^60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}\n")
            print(f"MicroStrategy başarıyla kuruldu ve çalışıyor.\n")
        else:
            print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'  BAZI SERVİSLER ÇALIŞMIYOR':^60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}\n")
            print(f"Lütfen servis durumlarını kontrol edin.\n")
    
    def show_rollback_complete(self, success: bool):
        """Rollback tamamlanma mesajı"""
        if success:
            print(f"\n{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'  ROLLBACK TAMAMLANDI':^60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}\n")
            print(f"Sistem eski haline döndürüldü.\n")
        else:
            print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'  ROLLBACK KISMİ BAŞARILI':^60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}\n")


if __name__ == '__main__':
    # Test
    cli = CLIInterface()
    cli.print_banner()
    role = cli.select_deployment_role()
    db_config = cli.get_database_config()
    
    if cli.confirm_configuration(role, db_config):
        print("Confirmed!")
    else:
        print("Cancelled!")
