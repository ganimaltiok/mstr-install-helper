"""
Post-Installation Verification Module
Kurulum sonrası servis kontrollerini yapar
"""

import socket
from typing import Dict, Tuple, List
from pathlib import Path
import yaml
import requests

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner


class PostInstall:
    """Post-installation verification"""
    
    def __init__(self):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.deployment_config = self._load_deployment_config()
        self.results = {}
    
    def _load_deployment_config(self) -> Dict:
        """Kaydedilmiş deployment config'i yükle"""
        config_file = Path('/opt/mstr-helper/config/deployment.yaml')
        
        if not config_file.exists():
            self.logger.warning("Deployment config bulunamadı")
            return {}
        
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Config yüklenemedi: {str(e)}")
            return {}
    
    def check_port_listening(self, port: int, description: str = "") -> Tuple[bool, Dict]:
        """Portun dinlenip dinlenmediğini kontrol et"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            listening = (result == 0)
            
            result_dict = {
                'port': port,
                'description': description,
                'listening': listening,
                'status': 'pass' if listening else 'fail'
            }
            
            if listening:
                self.logger.success(f"✓ Port {port} dinleniyor ({description})")
            else:
                self.logger.failure(f"✗ Port {port} dinlenmiyor ({description})")
            
            return listening, result_dict
            
        except Exception as e:
            self.logger.error(f"Port kontrol hatası: {str(e)}")
            return False, {'port': port, 'error': str(e), 'status': 'fail'}
    
    def check_intelligence_server(self) -> Tuple[bool, Dict]:
        """Intelligence Server kontrolü"""
        self.logger.subsection("Intelligence Server Kontrolü")
        
        ports = [
            (34952, "Main Intelligence Server"),
            (34962, "Metadata Repository"),
            (34972, "Statistics Server")
        ]
        
        results = []
        all_ok = True
        
        for port, desc in ports:
            ok, result = self.check_port_listening(port, desc)
            results.append(result)
            if not ok:
                all_ok = False
        
        # Optional ports
        optional_ports = [
            (39321, "Collaboration Server"),
            (41080, "Library Server")
        ]
        
        for port, desc in optional_ports:
            ok, result = self.check_port_listening(port, desc)
            result['required'] = False
            results.append(result)
        
        return all_ok, {'ports': results, 'status': 'pass' if all_ok else 'fail'}
    
    def check_web_server(self) -> Tuple[bool, Dict]:
        """Web Server kontrolü"""
        self.logger.subsection("Web Server Kontrolü")
        
        # Port kontrolü
        ports_ok = True
        port_results = []
        
        for port, desc in [(8080, "Tomcat HTTP"), (8443, "Tomcat HTTPS")]:
            ok, result = self.check_port_listening(port, desc)
            port_results.append(result)
            if not ok:
                ports_ok = False
        
        # HTTP health check (opsiyonel)
        http_ok = False
        http_result = {}
        
        try:
            self.logger.info("HTTP health check yapılıyor...")
            response = requests.get("http://localhost:8080/MicroStrategy/servlet/mstrWeb", timeout=10)
            http_ok = (response.status_code == 200)
            
            http_result = {
                'url': "http://localhost:8080/MicroStrategy/servlet/mstrWeb",
                'status_code': response.status_code,
                'accessible': http_ok
            }
            
            if http_ok:
                self.logger.success("✓ MicroStrategy Web erişilebilir")
            else:
                self.logger.warning(f"⚠ MicroStrategy Web yanıt verdi ama status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.logger.warning("⚠ MicroStrategy Web henüz başlatılmamış olabilir")
            http_result = {'accessible': False, 'error': 'Connection refused'}
        except Exception as e:
            self.logger.warning(f"⚠ HTTP check başarısız: {str(e)}")
            http_result = {'accessible': False, 'error': str(e)}
        
        return ports_ok, {
            'ports': port_results,
            'http_check': http_result,
            'status': 'pass' if ports_ok else 'fail'
        }
    
    def check_services(self) -> Tuple[bool, Dict]:
        """Systemd servislerini kontrol et"""
        self.logger.subsection("Servis Durumu Kontrolü")
        
        # MicroStrategy servislerini bul
        rc, output, _ = self.runner.run("systemctl list-units --type=service | grep -i mstr", shell=True)
        
        if rc != 0 or not output:
            self.logger.warning("MicroStrategy servisleri bulunamadı")
            return True, {'services': [], 'status': 'warning'}
        
        services = []
        for line in output.split('\n'):
            if 'mstr' in line.lower():
                parts = line.split()
                if parts:
                    service_name = parts[0]
                    
                    # Servis durumu
                    rc, status, _ = self.runner.run(f"systemctl is-active {service_name}", shell=True)
                    is_active = (status.strip() == 'active')
                    
                    services.append({
                        'name': service_name,
                        'active': is_active
                    })
                    
                    if is_active:
                        self.logger.success(f"✓ {service_name}: active")
                    else:
                        self.logger.warning(f"⚠ {service_name}: {status.strip()}")
        
        return True, {'services': services, 'status': 'pass'}
    
    def verify(self) -> Tuple[bool, Dict]:
        """Tüm verification'ları çalıştır"""
        self.logger.section("Post-Installation Verification")
        
        if not self.deployment_config:
            self.logger.error("Deployment config bulunamadı!")
            self.logger.info("Lütfen önce: sudo mstr-helper prepare")
            return False, {}
        
        deployment_role = self.deployment_config.get('deployment', {}).get('role', 'Unknown')
        self.logger.info(f"Deployment Role: {deployment_role}\n")
        
        results = {}
        all_ok = True
        
        # Intelligence Server kontrolü
        if deployment_role in ['Combined', 'IS-Only']:
            ok, result = self.check_intelligence_server()
            results['intelligence_server'] = result
            if not ok:
                all_ok = False
        
        # Web Server kontrolü
        if deployment_role in ['Combined', 'Web-Only']:
            ok, result = self.check_web_server()
            results['web_server'] = result
            if not ok:
                all_ok = False
        
        # Servis kontrolü
        ok, result = self.check_services()
        results['services'] = result
        
        self.results = results
        
        # Özet
        self.logger.section("Verification Özeti")
        
        if all_ok:
            self.logger.success("✓ TÜM SERVİSLER ÇALIŞIYOR!")
            self.logger.success("MicroStrategy kurulumu başarılı.\n")
            
            # Erişim bilgileri
            if deployment_role in ['Combined', 'Web-Only']:
                self.logger.info("Web Erişim:")
                self.logger.info("  HTTP:  http://localhost:8080/MicroStrategy/servlet/mstrWeb")
                self.logger.info("  HTTPS: https://localhost:8443/MicroStrategy/servlet/mstrWeb\n")
            
            if deployment_role in ['Combined', 'IS-Only']:
                self.logger.info("Intelligence Server:")
                self.logger.info("  Host: localhost")
                self.logger.info("  Port: 34952\n")
        else:
            self.logger.failure("✗ BAZI SERVİSLER ÇALIŞMIYOR!")
            self.logger.info("\nKontrol edilecekler:")
            self.logger.info("  1. MicroStrategy servisleri başlatıldı mı?")
            self.logger.info("  2. Logları kontrol edin: /opt/MicroStrategy/install/")
            self.logger.info("  3. Servisleri manuel başlatın: systemctl start <service>\n")
        
        return all_ok, results


if __name__ == '__main__':
    # Test
    verifier = PostInstall()
    success, results = verifier.verify()
    print(f"\nVerification successful: {success}")
