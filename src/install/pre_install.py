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
from ..config.user_config import UserConfig


class PreInstall:
    """Pre-installation hazırlıkları orkestre eder"""
    
    def __init__(self, deployment_role: str, db_config: Dict, remote_server: Dict[str, str] = None, user_config: Dict = None):
        self.logger = get_logger()
        self.deployment_role = deployment_role
        self.db_config = db_config
        self.remote_server = remote_server  # {'ip': '...', 'role': '...'}
        self.user_config = user_config  # {'create_user': bool, 'username': str}
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
        
        # Başarısız kontroller varsa otomatik düzeltme dene
        if not passed:
            self.logger.info("\n⚠ Bazı sistem kontrolleri başarısız, otomatik düzeltme deneniyor...")
            checker.fix_issues()
            
            # Tekrar kontrol et
            self.logger.info("\nSistem kontrolleri tekrar yapılıyor...")
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
        passed, results = checker.run_all_checks(remote_server=self.remote_server)
        
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
    
    def configure_user(self) -> bool:
        """MicroStrategy kullanıcısını yapılandır (opsiyonel)"""
        if not self.user_config or not self.user_config.get('create_user'):
            self.logger.info("MicroStrategy kullanıcısı oluşturulmayacak (atlandı)")
            return True
        
        self.logger.section("ADIM 5: MicroStrategy Kullanıcı Konfigürasyonu")
        
        username = self.user_config.get('username', 'mstr')
        
        config = UserConfig()
        results = config.configure_user(username=username, enable_sudo=True)
        
        self.results['configurations']['user'] = {
            'success': results['success'],
            'results': results
        }
        
        return results['success']
    
    def configure_xdisplay(self) -> bool:
        """X Display yapılandır"""
        step_num = 6 if self.user_config and self.user_config.get('create_user') else 5
        self.logger.section(f"ADIM {step_num}: X Display Yapılandırması")
        
        config = XDisplayConfig()
        success, results = config.configure()
        
        self.results['configurations']['xdisplay'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_firewall(self) -> bool:
        """Firewall yapılandır"""
        step_num = 7 if self.user_config and self.user_config.get('create_user') else 6
        self.logger.section(f"ADIM {step_num}: Firewall Yapılandırması")
        
        config = FirewallConfig(deployment_role=self.deployment_role)
        success, results = config.configure()
        
        self.results['configurations']['firewall'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_selinux(self) -> bool:
        """SELinux yapılandır"""
        step_num = 8 if self.user_config and self.user_config.get('create_user') else 7
        self.logger.section(f"ADIM {step_num}: SELinux Yapılandırması")
        
        config = SELinuxConfig()
        success, results = config.configure()
        
        self.results['configurations']['selinux'] = {
            'success': success,
            'results': results
        }
        
        return success
    
    def configure_limits(self) -> bool:
        """System limits yapılandır"""
        step_num = 9 if self.user_config and self.user_config.get('create_user') else 8
        self.logger.section(f"ADIM {step_num}: System Limits Yapılandırması")
        
        # User-specific veya global limits
        username = None
        if self.user_config and self.user_config.get('create_user'):
            username = self.user_config.get('username', 'mstr')
        
        config = LimitsConfig()
        success, results = config.configure_limits(username=username)
        
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
                'network': {
                    'remote_server_ip': self.remote_server.get('ip') if self.remote_server else None,
                    'remote_server_role': self.remote_server.get('role') if self.remote_server else None
                },
                'user': {
                    'create_user': self.user_config.get('create_user', False) if self.user_config else False,
                    'username': self.user_config.get('username') if self.user_config else None
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
        self.logger.info(f"Database: {self.db_config['type']}")
        if self.user_config and self.user_config.get('create_user'):
            self.logger.info(f"MicroStrategy User: {self.user_config.get('username', 'mstr')}")
        self.logger.info("")
        
        steps = [
            ("Sistem Kontrolleri", self.run_system_checks),
            ("Network Kontrolleri", self.run_network_checks),
            ("Database Kontrolleri", self.run_database_checks),
            ("Paket Bağımlılıkları", self.install_dependencies),
        ]
        
        # User configuration adımını conditional ekle
        if self.user_config and self.user_config.get('create_user'):
            steps.append(("MicroStrategy Kullanıcı Konfigürasyonu", self.configure_user))
        
        steps.extend([
            ("X Display Yapılandırması", self.configure_xdisplay),
            ("Firewall Yapılandırması", self.configure_firewall),
            ("SELinux Yapılandırması", self.configure_selinux),
            ("System Limits Yapılandırması", self.configure_limits)
        ])
        
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
