"""
CLI Interface Module
Kullanıcı etkileşimi ve input toplama
"""

import sys
import os
from typing import Dict, Optional
from colorama import Fore, Style
import yaml
from pathlib import Path

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
        self.saved_config = self._load_saved_config()
    
    def _load_saved_config(self) -> Optional[Dict]:
        """Kaydedilmiş konfigürasyonu yükle"""
        config_file = Path("/opt/mstr-helper/config/deployment.yaml")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                self.logger.warning(f"Kaydedilmiş konfigürasyon yüklenemedi: {e}")
        return None
    
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
    
    def get_remote_server_ip(self, role: str) -> Dict[str, str]:
        """Distributed deployment için remote sunucu IP'si al"""
        if role == "Combined":
            return {"ip": None, "role": None, "skip_check": False}
        
        # Saved config'den default değerleri al
        default_ip = ""
        if self.saved_config and self.saved_config.get('network'):
            default_ip = self.saved_config['network'].get('remote_server_ip', '')
        
        print(f"{Fore.YELLOW}Karşı Sunucu Bilgileri{Style.RESET_ALL}")
        print("-" * 50)
        
        if role == "IS-Only":
            print("IS sunucusu Web sunucusuna bağlanabilmeli.")
            remote_role = "Web-Only"
            
            # Web sunucusu kurulu mu?
            web_installed = self.confirm("Web sunucusu şu anda kurulu mu?", False)
            
            if not web_installed:
                print(f"\n{Fore.YELLOW}⚠ Web sunucusu henüz kurulu değil.{Style.RESET_ALL}")
                print(f"Port kontrolleri atlanacak, kurulumdan sonra doğrulayın.\n")
                return {"ip": None, "role": remote_role, "skip_check": True}
            
            remote_ip = self.get_input("Web Sunucu IP Adresi", default_ip)
        else:  # Web-Only
            print("Web sunucusu Intelligence Server'a bağlanabilmeli.")
            remote_role = "IS-Only"
            
            # IS sunucusu kurulu mu?
            is_installed = self.confirm("Intelligence Server şu anda kurulu mu?", False)
            
            if not is_installed:
                print(f"\n{Fore.YELLOW}⚠ Intelligence Server henüz kurulu değil.{Style.RESET_ALL}")
                print(f"Port kontrolleri atlanacak, kurulumdan sonra doğrulayın.\n")
                return {"ip": None, "role": remote_role, "skip_check": True}
            
            remote_ip = self.get_input("Intelligence Server IP Adresi", default_ip)
        
        if remote_ip:
            print(f"\n{Fore.GREEN}✓ Karşı sunucu: {remote_ip} ({remote_role}){Style.RESET_ALL}\n")
        else:
            print(f"\n{Fore.YELLOW}⚠ Remote sunucu IP'si belirtilmedi, port kontrolleri atlanacak{Style.RESET_ALL}\n")
        
        return {"ip": remote_ip if remote_ip else None, "role": remote_role, "skip_check": False}
    
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
        
        # Saved config'den default değerleri al
        saved_db = self.saved_config.get('database', {}) if self.saved_config else {}
        
        # Database tipi
        db_type = self.select_database_type()
        
        # Default port
        _, default_port = [(v[0], v[1]) for v in self.DATABASE_TYPES.values() if v[0] == db_type][0]
        
        # Host
        default_host = saved_db.get('host', 'localhost') if saved_db.get('type') == db_type else 'localhost'
        host = self.get_input("Database Host", default_host)
        
        # Port
        default_port_saved = saved_db.get('port', default_port) if saved_db.get('type') == db_type else default_port
        port_str = self.get_input(f"Database Port", str(default_port_saved))
        try:
            port = int(port_str)
        except ValueError:
            print(f"{Fore.RED}Geçersiz port, default kullanılıyor: {default_port_saved}{Style.RESET_ALL}")
            port = default_port_saved
        
        # Database name
        default_db = saved_db.get('database', 'metadata') if saved_db.get('type') == db_type else 'metadata'
        database = self.get_input("Database Adı", default_db)
        
        # Username
        default_user = saved_db.get('username', 'mstr_admin') if saved_db.get('type') == db_type else 'mstr_admin'
        username = self.get_input("Kullanıcı Adı", default_user)
        
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
    
    def confirm_configuration(self, deployment_role: str, db_config: Dict, remote_server: Dict[str, str] = None) -> bool:
        """Konfigürasyonu onaylatma"""
        print(f"\n{Fore.YELLOW}Konfigürasyon Özeti{Style.RESET_ALL}")
        print("=" * 50)
        print(f"Deployment: {Fore.CYAN}{deployment_role}{Style.RESET_ALL}")
        if remote_server and remote_server.get('ip'):
            print(f"Remote:     {Fore.CYAN}{remote_server['role']} @ {remote_server['ip']}{Style.RESET_ALL}")
        print(f"Database:   {Fore.CYAN}{db_config['type']}{Style.RESET_ALL}")
        print(f"Host:       {db_config['host']}")
        print(f"Port:       {db_config['port']}")
        print(f"Database:   {db_config['database']}")
        print(f"Username:   {db_config['username']}")
        print("=" * 50)
        print()
        
        return self.confirm("Bu ayarlarla devam edilsin mi?", True)
    
    def show_completion(self, success: bool, results: Dict = None):
        """Tamamlanma mesajı ve özet"""
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
        
        # Özet göster
        if results:
            self.show_summary(results)
    
    def show_summary(self, results: Dict):
        """İşlem özeti göster"""
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'  ÖZET':^60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        
        checks = results.get('checks', {})
        configs = results.get('configurations', {})
        
        passed_items = []
        failed_items = []
        skipped_items = []
        
        # Checks
        for check_name, check_data in checks.items():
            if isinstance(check_data, dict):
                if check_data.get('passed'):
                    passed_items.append(f"✓ {check_name.replace('_', ' ').title()}")
                elif check_data.get('skipped'):
                    skipped_items.append(f"○ {check_name.replace('_', ' ').title()} (atlandı)")
                else:
                    failed_items.append(f"✗ {check_name.replace('_', ' ').title()}")
        
        # Configurations
        for config_name, config_data in configs.items():
            if isinstance(config_data, dict):
                if config_data.get('success'):
                    passed_items.append(f"✓ {config_name.replace('_', ' ').title()}")
                else:
                    failed_items.append(f"✗ {config_name.replace('_', ' ').title()}")
        
        # Başarılı
        if passed_items:
            print(f"{Fore.GREEN}Başarılı ({len(passed_items)}):{Style.RESET_ALL}")
            for item in passed_items:
                print(f"  {Fore.GREEN}{item}{Style.RESET_ALL}")
            print()
        
        # Başarısız
        if failed_items:
            print(f"{Fore.RED}Başarısız ({len(failed_items)}):{Style.RESET_ALL}")
            for item in failed_items:
                print(f"  {Fore.RED}{item}{Style.RESET_ALL}")
            print()
        
        # Atlanan
        if skipped_items:
            print(f"{Fore.YELLOW}Atlanan ({len(skipped_items)}):{Style.RESET_ALL}")
            for item in skipped_items:
                print(f"  {Fore.YELLOW}{item}{Style.RESET_ALL}")
            print()
        
        # Toplam
        total = len(passed_items) + len(failed_items) + len(skipped_items)
        print(f"{Fore.CYAN}Toplam: {total} işlem ({len(passed_items)} başarılı, {len(failed_items)} başarısız, {len(skipped_items)} atlanan){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
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
