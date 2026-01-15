"""
Pre-Installation Module
Tüm hazırlık adımlarını orkestre eder
"""

from typing import Dict, Tuple
from datetime import datetime
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..checks.system_check import SystemCheck
from ..checks.network_check import NetworkCheck
from ..checks.dependency_check import DependencyCheck
from ..checks.database_check import DatabaseCheck
from ..config.xdisplay_config import XDisplayConfig
from ..config.firewall_config import FirewallConfig
from ..config.selinux_config import SELinuxConfig
from ..config.limits_config import LimitsConfig


class PreInstall:
    """Pre-installation hazırlıkları orkestre eder"""
    
    def __init__(self, deployment_role: str, db_config: Dict):
        self.logger = get_logger()
        self.deployment_role = deployment_role
        self.db_config = db_config
        self.results = {
            'deployment_role': deployment_role,
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'configurations': {}
        }
    
    def run_system_checks(self) -> bool:
        """Sistem kontrollerini çalıştır"""
        self.logger.section("ADIM 1: Sistem Kontrolleri")
        
        checker = SystemCheck()
        passed, results = checker.run_all_checks()
        
        self.results['checks']['system'] = {
            'passed': passed,
            'results': results
        }
        
        return passed
    
    def run_network_checks(self) -> bool:
        """Network kontrollerini çalıştır"""
        self.logger.section("ADIM 2: Network Kontrolleri")
        
        checker = NetworkCheck(deployment_role=self.deployment_role)
        passed, results = checker.run_all_checks()
        
        self.results['checks']['network'] = {
            'passed': passed,
            'results': results
        }
        
        return passed
    
    def run_database_checks(self) -> bool:
        """Database kontrollerini çalıştır"""
        self.logger.section("ADIM 3: Database Kontrolleri")
        
        checker = DatabaseCheck(
            db_type=self.db_config['type'],
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            username=self.db_config['username'],
            password=self.db_config['password']
        )
        
        passed, results = checker.run_all_checks()
        
        self.results['checks']['database'] = {
            'passed': passed,
            'results': results
        }
        
        return passed
    
    def install_dependencies(self) -> bool:
        """Bağımlılıkları yükle"""
        self.logger.section("ADIM 4: Paket Bağımlılıkları")
        
        checker = DependencyCheck(
            deployment_role=self.deployment_role,
            db_type=self.db_config['type']
        )
        
        passed, results = checker.run_all_checks()
        
        self.results['checks']['dependencies'] = {
            'passed': passed,
            'results': results
        }
        
        return passed
    
    def configure_xdisplay(self) -> bool:
        """X Display yapılandır"""
        self.logger.section("ADIM 5: X Display Yapılandırması")
        
        config = XDisplayConfig()
        success, results = config.configure()
        
        self.results['configurations']['xdisplay'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_firewall(self) -> bool:
        """Firewall yapılandır"""
        self.logger.section("ADIM 6: Firewall Yapılandırması")
        
        config = FirewallConfig(deployment_role=self.deployment_role)
        success, results = config.configure()
        
        self.results['configurations']['firewall'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_selinux(self) -> bool:
        """SELinux yapılandır"""
        self.logger.section("ADIM 7: SELinux Yapılandırması")
        
        config = SELinuxConfig()
        success, results = config.configure()
        
        self.results['configurations']['selinux'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_limits(self) -> bool:
        """System limits yapılandır"""
        self.logger.section("ADIM 8: System Limits Yapılandırması")
        
        config = LimitsConfig()
        success, results = config.configure()
        
        self.results['configurations']['limits'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def save_configuration(self) -> bool:
        """Deployment konfigürasyonunu kaydet"""
        self.logger.subsection("Konfigürasyon Kaydediliyor")
        
        config_dir = Path('/opt/mstr-helper/config')
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'deployment.yaml'
        
        try:
            # Hostname al
            from ..utils.command_runner import get_command_runner
            runner = get_command_runner()
            rc, hostname, _ = runner.run("hostname")
            
            config_data = {
                'deployment': {
                    'role': self.deployment_role,
                    'timestamp': datetime.now().isoformat(),
                    'hostname': hostname.strip()
                },
                'database': {
                    'type': self.db_config['type'],
                    'host': self.db_config['host'],
                    'port': self.db_config['port'],
                    'database': self.db_config['database'],
                    'username': self.db_config['username']
                    # password kaydedilmez
                },
                'installation': {
                    'status': 'prepared',
                    'installation_date': None
                },
                'checks': {
                    'system': self.results['checks'].get('system', {}).get('passed', False),
                    'network': self.results['checks'].get('network', {}).get('passed', False),
                    'database': self.results['checks'].get('database', {}).get('passed', False),
                    'dependencies': self.results['checks'].get('dependencies', {}).get('passed', False),
                    'firewall': self.results['configurations'].get('firewall', {}).get('success', False),
                    'selinux': self.results['configurations'].get('selinux', {}).get('success', False)
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            self.logger.success(f"Konfigürasyon kaydedildi: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Konfigürasyon kaydedilemedi: {str(e)}")
            return False
    
    def show_installation_instructions(self):
        """Kurulum talimatlarını göster"""
        self.logger.section("MicroStrategy Kurulum Talimatları")
        
        self.logger.info("Sunucu hazır! Şimdi MicroStrategy kurulumunu yapabilirsiniz.\n")
        
        if self.deployment_role == 'Combined':
            self.logger.info("=== COMBINED DEPLOYMENT ===")
            self.logger.info("Hem Intelligence Server hem Web Server aynı sunucuya kurulacak.\n")
            
            self.logger.info("Kurulum adımları:")
            self.logger.info("1. MicroStrategy installer'ı çalıştırın:")
            self.logger.info("   chmod +x MicroStrategy-11.*.sh")
            self.logger.info("   sudo ./MicroStrategy-11.*.sh\n")
            
            self.logger.info("2. Kurulum sırasında seçenekler:")
            self.logger.info("   ✓ Intelligence Server seçin")
            self.logger.info("   ✓ Web Server seçin")
            self.logger.info("   ✓ Platform Analytics (opsiyonel)")
            self.logger.info("   ✓ Library Server (opsiyonel)\n")
            
            self.logger.info("3. Database bağlantısı:")
            self.logger.info(f"   Type: {self.db_config['type']}")
            self.logger.info(f"   Host: {self.db_config['host']}")
            self.logger.info(f"   Port: {self.db_config['port']}")
            self.logger.info(f"   Database: {self.db_config['database']}")
            self.logger.info(f"   Username: {self.db_config['username']}\n")
        
        elif self.deployment_role == 'Web-Only':
            self.logger.info("=== WEB SERVER ONLY ===")
            self.logger.info("Sadece Web Server kurulacak.\n")
            
            self.logger.info("Kurulum adımları:")
            self.logger.info("1. MicroStrategy installer'ı çalıştırın:")
            self.logger.info("   chmod +x MicroStrategy-11.*.sh")
            self.logger.info("   sudo ./MicroStrategy-11.*.sh\n")
            
            self.logger.info("2. Kurulum sırasında seçenekler:")
            self.logger.info("   ✓ Sadece Web Server seçin")
            self.logger.info("   ✗ Intelligence Server seçmeyin\n")
            
            self.logger.info("3. Intelligence Server bağlantısı:")
            self.logger.info("   Kurulum sonrası MicroStrategy Web'de Intelligence Server")
            self.logger.info("   IP adresini ve portunu (34952) yapılandırın.\n")
        
        elif self.deployment_role == 'IS-Only':
            self.logger.info("=== INTELLIGENCE SERVER ONLY ===")
            self.logger.info("Sadece Intelligence Server kurulacak.\n")
            
            self.logger.info("Kurulum adımları:")
            self.logger.info("1. MicroStrategy installer'ı çalıştırın:")
            self.logger.info("   chmod +x MicroStrategy-11.*.sh")
            self.logger.info("   sudo ./MicroStrategy-11.*.sh\n")
            
            self.logger.info("2. Kurulum sırasında seçenekler:")
            self.logger.info("   ✓ Intelligence Server seçin")
            self.logger.info("   ✗ Web Server seçmeyin")
            self.logger.info("   ✓ Platform Analytics (opsiyonel)")
            self.logger.info("   ✓ Library Server (opsiyonel)\n")
            
            self.logger.info("3. Database bağlantısı:")
            self.logger.info(f"   Type: {self.db_config['type']}")
            self.logger.info(f"   Host: {self.db_config['host']}")
            self.logger.info(f"   Port: {self.db_config['port']}")
            self.logger.info(f"   Database: {self.db_config['database']}")
            self.logger.info(f"   Username: {self.db_config['username']}\n")
        
        self.logger.info("4. Kurulum tamamlandıktan sonra:")
        self.logger.info("   sudo mstr-helper verify\n")
        
        self.logger.info("Portlar:")
        if self.deployment_role in ['Combined', 'IS-Only']:
            self.logger.info("   Intelligence Server: 34952")
            self.logger.info("   Metadata: 34962")
            self.logger.info("   Statistics: 34972")
            self.logger.info("   Collaboration: 39321")
            self.logger.info("   Library: 41080")
        if self.deployment_role in ['Combined', 'Web-Only']:
            self.logger.info("   Web HTTP: 8080")
            self.logger.info("   Web HTTPS: 8443")
    
    def run(self) -> Tuple[bool, Dict]:
        """Tüm hazırlık adımlarını çalıştır"""
        self.logger.section("MicroStrategy Kurulum Hazırlığı Başlıyor")
        self.logger.info(f"Deployment Role: {self.deployment_role}")
        self.logger.info(f"Database: {self.db_config['type']}\n")
        
        steps = [
            ("Sistem Kontrolleri", self.run_system_checks),
            ("Network Kontrolleri", self.run_network_checks),
            ("Database Kontrolleri", self.run_database_checks),
            ("Paket Bağımlılıkları", self.install_dependencies),
            ("X Display Yapılandırması", self.configure_xdisplay),
            ("Firewall Yapılandırması", self.configure_firewall),
            ("SELinux Yapılandırması", self.configure_selinux),
            ("System Limits Yapılandırması", self.configure_limits)
        ]
        
        failed_steps = []
        
        for step_name, step_func in steps:
            try:
                success = step_func()
                if not success:
                    failed_steps.append(step_name)
                    self.logger.failure(f"✗ {step_name} BAŞARISIZ")
            except Exception as e:
                failed_steps.append(step_name)
                self.logger.error(f"✗ {step_name} HATA: {str(e)}")
        
        # Konfigürasyonu kaydet
        self.save_configuration()
        
        # Sonuç
        self.logger.section("Hazırlık Özeti")
        
        if not failed_steps:
            self.logger.success("✓ TÜM HAZIRLIKLAR TAMAMLANDI!")
            self.logger.success("Sunucu MicroStrategy kurulumu için hazır.\n")
            self.show_installation_instructions()
            return True, self.results
        else:
            self.logger.failure("✗ BAZI HAZIRLIKLAR BAŞARISIZ!")
            self.logger.failure(f"Başarısız adımlar: {', '.join(failed_steps)}\n")
            self.logger.info("Lütfen hataları düzeltin ve tekrar çalıştırın.")
            return False, self.results


if __name__ == '__main__':
    # Test
    print("PreInstall module - use through main.py")
