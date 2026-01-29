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
            
            # FQDN sorunu varsa kullanıcıdan domain al
            fqdn = None
            if checker.results.get('hostname', {}).get('needs_fix'):
                from ..cli.interface import CLIInterface
                cli = CLIInterface()
                hostname = checker.results.get('hostname', {}).get('hostname', 'unknown')
                fqdn = cli.get_fqdn_domain(hostname)
            
            # Düzeltmeleri yap
            fixed = checker.fix_issues(fqdn=fqdn)
            
            if fixed:
                # Düzeltmeler yapıldı - session'da görünmese de kuruluma devam edilebilir
                self.logger.success("\n✓ Otomatik düzeltmeler tamamlandı!")
                self.logger.info("  • FQDN /etc/hosts'a eklendi")
                self.logger.info("  • Ulimits /etc/security/limits.conf'a eklendi")
                self.logger.warning("\n⚠ NOT: Bu düzeltmeler yeni SSH oturumunda geçerli olacak")
                self.logger.info("  Ancak MicroStrategy kurulumu için bu düzeltmeler yeterli.")
                self.logger.info("  Kuruluma güvenle devam edebilirsiniz.\n")
                
                # Düzeltilen sorunları results'ta PASS olarak işaretle
                if checker.results.get('hostname', {}).get('needs_fix'):
                    checker.results['hostname']['status'] = 'pass'
                    checker.results['hostname']['needs_fix'] = False
                    checker.results['hostname']['auto_fixed'] = True
                
                if checker.results.get('ulimits', {}).get('status') == 'fail':
                    checker.results['ulimits']['status'] = 'pass'
                    checker.results['ulimits']['auto_fixed'] = True
                
                # Genel durumu güncelle - ÖNEMLİ: results değişkenini de güncelle!
                passed = True
                results = checker.results  # Bu satır kritik!
        
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
        password = self.user_config.get('password', 'mstr')
        
        config = UserConfig()
        results = config.configure_user(username=username, password=password, enable_sudo=True)
        
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
        # Configure both limits.conf and sysctl.conf
        success, results = config.configure(username=username)
        
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
    
    def save_installation_cheatsheet(self):
        """Kurulum sırasında kullanılacak bilgileri dosyaya kaydet"""
        try:
            from pathlib import Path
            cheatsheet_dir = Path('/var/log/mstr-helper')
            cheatsheet_dir.mkdir(parents=True, exist_ok=True)
            cheatsheet_file = cheatsheet_dir / 'installation-cheatsheet.txt'
            
            # Get hostname and IP
            from ..utils.command_runner import get_command_runner
            runner = get_command_runner()
            rc, hostname, _ = runner.run("hostname")
            rc, ip_output, _ = runner.run("hostname -I | awk '{print $1}'")
            rc2, fqdn_output, _ = runner.run("hostname -f")
            
            hostname = hostname.strip()
            ip_addr = ip_output.strip() if ip_output else "N/A"
            
            # FQDN - system check sonuçlarından veya hostname -f'den al
            fqdn = None
            if self.results.get('checks', {}).get('system', {}).get('results', {}).get('hostname', {}).get('fqdn_configured'):
                fqdn = self.results['checks']['system']['results']['hostname']['fqdn_configured']
            elif fqdn_output and '.' in fqdn_output:
                fqdn = fqdn_output.strip()
            else:
                fqdn = f"{hostname}.localdomain"
            
            content = []
            content.append("=" * 80)
            content.append("MICROSTRATEGY KURULUM KOPYA KAĞIDI")
            content.append("MicroStrategy Installer Ekranlarında Kullanılacak Bilgiler")
            content.append("=" * 80)
            content.append("")
            content.append(f"Sunucu: {hostname}")
            content.append(f"IP Adresi: {ip_addr}")
            content.append(f"FQDN: {fqdn}")
            content.append(f"Deployment: {self.deployment_role}")
            content.append(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("")
            
            # FQDN bilgisi özel vurgu
            content.append("=" * 80)
            content.append("ÖNEMLİ: HOSTNAME VE FQDN")
            content.append("=" * 80)
            content.append(f"Hostname: {hostname}")
            content.append(f"FQDN: {fqdn}")
            content.append(f"IP Address: {ip_addr}")
            content.append("")
            content.append("NOT: MicroStrategy installer FQDN çözebilmeli.")
            content.append("     /etc/hosts dosyası otomatik yapılandırıldı.")
            content.append(f"     Test için: ping {fqdn}")
            content.append("")
            
            # User bilgisi
            if self.user_config and self.user_config.get('create_user'):
                username = self.user_config.get('username', 'mstr')
                content.append("=" * 80)
                content.append("KULLANICI BİLGİSİ VE GUI KURULUM")
                content.append("=" * 80)
                content.append(f"MicroStrategy User: {username}")
                content.append("")
                content.append("X11 FORWARDING İLE GUI KURULUM:")
                content.append(f"1. SSH ile bağlan: ssh -X {username}@{hostname}")
                content.append(f"2. MobaXterm: X11-Forwarding seçeneği aktif olmalı")
                content.append(f"3. DISPLAY otomatik ayarlanır (localhost:10.0)")
                content.append(f"4. Installer'ı çalıştır: cd installers && ./setup.sh")
                content.append("")
                content.append("NOT: .Xauthority dosyası otomatik oluşturuldu")
                content.append("     X11 forwarding sorunsuz çalışacaktır")
                content.append("")
            
            # Deployment seçimi
            content.append("=" * 80)
            content.append("1. DEPLOYMENT TİPİ SEÇİMİ (Installer Ekranı)")
            content.append("=" * 80)
            
            if self.deployment_role == 'Combined':
                content.append("✓ Intelligence Server     → SEÇİN")
                content.append("✓ Web Server             → SEÇİN")
                content.append("○ Platform Analytics     → OPSİYONEL")
                content.append("○ Library Server         → OPSİYONEL")
            elif self.deployment_role == 'IS-Only':
                content.append("✓ Intelligence Server     → SEÇİN")
                content.append("✗ Web Server             → SEÇMEYİN")
                content.append("○ Platform Analytics     → OPSİYONEL")
                content.append("○ Library Server         → OPSİYONEL")
            elif self.deployment_role == 'Web-Only':
                content.append("✗ Intelligence Server     → SEÇMEYİN")
                content.append("✓ Web Server             → SEÇİN")
                content.append("✗ Platform Analytics     → SEÇMEYİN")
                content.append("✗ Library Server         → SEÇMEYİN")
            
            content.append("")
            
            # Database bilgileri (IS içeren deploymentlar için)
            if self.deployment_role in ['Combined', 'IS-Only']:
                content.append("=" * 80)
                content.append("2. METADATA DATABASE BAĞLANTISI (Installer Ekranı)")
                content.append("=" * 80)
                content.append(f"Database Type:    {self.db_config['type']}")
                content.append(f"Host/Server:      {self.db_config['host']}")
                content.append(f"Port:             {self.db_config['port']}")
                content.append(f"Database Name:    {self.db_config['database']}")
                content.append(f"Username:         {self.db_config['username']}")
                content.append(f"Password:         [Hazırlık sırasında test ettiğiniz şifre]")
                content.append("")
                content.append("KOPYALA-YAPIŞTIR İÇİN:")
                content.append(f"  Host:     {self.db_config['host']}")
                content.append(f"  Port:     {self.db_config['port']}")
                content.append(f"  Database: {self.db_config['database']}")
                content.append(f"  Username: {self.db_config['username']}")
                content.append("")
            
            # Remote server bilgisi (distributed deployment)
            if self.remote_server and self.remote_server.get('ip'):
                content.append("=" * 80)
                content.append("3. REMOTE SERVER BAĞLANTISI")
                content.append("=" * 80)
                if self.deployment_role == 'Web-Only':
                    content.append("Intelligence Server bağlantısı (Web yapılandırmasında):")
                    content.append(f"  IS Server IP:   {self.remote_server['ip']}")
                    content.append(f"  IS Server Port: 34952")
                elif self.deployment_role == 'IS-Only':
                    content.append("Web Server bilgisi (referans için):")
                    content.append(f"  Web Server IP:  {self.remote_server['ip']}")
                    content.append(f"  Web HTTP Port:  8080")
                    content.append(f"  Web HTTPS Port: 8443")
                content.append("")
            
            # Port bilgileri
            content.append("=" * 80)
            content.append("4. PORT BİLGİLERİ (Referans)")
            content.append("=" * 80)
            
            if self.deployment_role in ['Combined', 'IS-Only']:
                content.append("Intelligence Server Portları:")
                content.append("  34952  → Intelligence Server (ana port)")
                content.append("  9500   → Modeling Service")
                content.append("  8300-8302 → Topology Services")
                content.append("  34962  → REST API Server")
                content.append("  3000   → Collaboration Server")
                content.append("")
            
            if self.deployment_role in ['Combined', 'Web-Only']:
                content.append("Web Server Portları:")
                content.append("  8080   → Tomcat HTTP")
                content.append("  8443   → Tomcat HTTPS")
                content.append("  20100  → Strategy Export Service")
                content.append("")
            
            # Installation path
            content.append("=" * 80)
            content.append("5. KURULUM YOLU ÖNERİSİ")
            content.append("=" * 80)
            content.append("Installation Path: /opt/MicroStrategy")
            content.append("  (Default yolu kullanabilirsiniz)")
            content.append("")
            
            # Admin credentials
            content.append("=" * 80)
            content.append("6. ADMİNİSTRATÖR BİLGİLERİ")
            content.append("=" * 80)
            content.append("MicroStrategy Administrator hesabı oluşturulacak:")
            content.append("  Username: administrator (default)")
            content.append("  Password: [Güçlü bir şifre belirleyin]")
            content.append("  ÖNERİ: En az 12 karakter, büyük/küçük harf, rakam, özel karakter")
            content.append("")
            
            # Post-installation
            content.append("=" * 80)
            content.append("7. KURULUM SONRASI")
            content.append("=" * 80)
            content.append("Kurulum tamamlandığında:")
            content.append("  1. Servislerin çalıştığını kontrol edin:")
            content.append("     sudo mstr-helper verify")
            content.append("")
            content.append("  2. Web arayüzüne erişin:")
            if self.deployment_role in ['Combined', 'Web-Only']:
                content.append(f"     http://{hostname}:8080/MicroStrategy/servlet/mstrWeb")
                content.append(f"     https://{hostname}:8443/MicroStrategy/servlet/mstrWeb")
            content.append("")
            
            # Troubleshooting
            content.append("=" * 80)
            content.append("8. SORUN GİDERME")
            content.append("=" * 80)
            content.append("Loglar:")
            content.append("  /opt/MicroStrategy/install.log")
            content.append("  /var/log/mstr-helper/")
            content.append("")
            content.append("Servis kontrolleri:")
            if self.deployment_role in ['Combined', 'IS-Only']:
                content.append("  sudo systemctl status MicroStrategyIntelligenceServer")
            if self.deployment_role in ['Combined', 'Web-Only']:
                content.append("  sudo systemctl status tomcat")
            content.append("")
            content.append("Port kontrolleri:")
            content.append("  sudo netstat -tuln | grep -E '34952|8080|8443'")
            content.append("  sudo ss -tuln | grep -E '34952|8080|8443'")
            content.append("")
            
            content.append("=" * 80)
            content.append("NOT: Bu dosya otomatik oluşturulmuştur")
            content.append(f"Kayıt: {cheatsheet_file}")
            content.append("=" * 80)
            
            # Dosyayı yaz
            with open(cheatsheet_file, 'w') as f:
                f.write('\n'.join(content))
            
            self.logger.success(f"Kurulum kopya kağıdı oluşturuldu: {cheatsheet_file}")
            
            # Terminal'e de göster
            self.logger.info("")
            self.logger.section("KURULUM KOPYA KAĞIDI")
            self.logger.info(f"Detaylı bilgiler: {cheatsheet_file}")
            self.logger.info("")
            
            # Özet göster
            for line in content[0:50]:  # İlk önemli kısımları göster
                if line.startswith("="):
                    self.logger.info(line)
                elif line.startswith("✓") or line.startswith("✗") or line.startswith("○"):
                    self.logger.info(f"  {line}")
                elif ":" in line and not line.startswith(" "):
                    self.logger.info(line)
            
            self.logger.info("")
            self.logger.info(f"Tüm detaylar için: cat {cheatsheet_file}")
            self.logger.info("")
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Kurulum kopya kağıdı oluşturulamadı: {str(e)}")
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
            
            # Kurulum kopya kağıdı oluştur ve göster
            self.save_installation_cheatsheet()
            self.show_installation_instructions()
            return True, self.results
        else:
            self.logger.failure("✗ BAZI HAZIRLIKLAR BAŞARISIZ!")
            self.logger.failure(f"Başarısız adımlar: {', '.join(failed_steps)}\n")
            self.logger.info("Lütfen hataları düzeltin ve tekrar çalıştırın.")
            
            # Hata olsa bile kurulum yardımını göster (partial success durumu için)
            self.logger.info("")
            self.save_installation_cheatsheet()
            return False, self.results


if __name__ == '__main__':
    # Test
    print("PreInstall module - use through main.py")
