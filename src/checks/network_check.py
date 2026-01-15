"""
Network Check Module
Port kullanılabilirliği ve ağ bağlantısı kontrollerini yapar
"""

import socket
from typing import Dict, List, Tuple
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner


class NetworkCheck:
    """Network ve port kontrollerini yapar"""
    
    def __init__(self, deployment_role: str = 'Combined'):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.deployment_role = deployment_role
        self.port_config = self._load_port_config()
        self.results: Dict = {}
    
    def _load_port_config(self) -> Dict:
        """Port gereksinimlerini config'den yükle"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'port_requirements.yaml'
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load port requirements: {str(e)}")
            return {}
    
    def _get_required_ports(self) -> List[Dict]:
        """Deployment role'e göre gerekli portları döndür"""
        required_ports = []
        
        role_config = self.port_config.get('deployment_roles', {}).get(self.deployment_role, {})
        port_groups = role_config.get('ports', [])
        
        for group in port_groups:
            ports = self.port_config.get('ports', {}).get(group, [])
            required_ports.extend(ports)
        
        return required_ports
    
    def is_port_in_use(self, port: int, protocol: str = 'tcp') -> bool:
        """
        Portun kullanımda olup olmadığını kontrol et
        
        Args:
            port: Port numarası
            protocol: 'tcp' veya 'udp'
        
        Returns:
            bool: Port kullanımdaysa True
        """
        try:
            if protocol == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            # 0 = bağlantı başarılı (port kullanımda)
            # 111 = connection refused (port dinlemiyor, kullanılabilir)
            return result == 0
            
        except Exception as e:
            self.logger.debug(f"Error checking port {port}: {str(e)}")
            return False
    
    def check_port_availability(self, port: int, description: str = "", 
                                protocol: str = 'tcp', required: bool = True) -> Tuple[bool, Dict]:
        """
        Port kullanılabilirliğini kontrol et
        
        Returns:
            Tuple[bool, Dict]: (port_available, result_dict)
        """
        in_use = self.is_port_in_use(port, protocol)
        
        result = {
            'port': port,
            'protocol': protocol,
            'description': description,
            'in_use': in_use,
            'required': required,
            'status': 'fail' if in_use else 'pass'
        }
        
        if in_use:
            # Port kullanımda - hangi process kullanıyor?
            rc, output, _ = self.runner.run(f"lsof -i :{port} -t", shell=True)
            if output:
                result['pid'] = output.split('\n')[0]
                rc2, process, _ = self.runner.run(f"ps -p {result['pid']} -o comm=", shell=True)
                result['process'] = process.strip() if process else "unknown"
            
            self.logger.failure(f"Port {port}/{protocol} KULLANIMDA ({description})")
            if 'process' in result:
                self.logger.info(f"  -> Process: {result['process']} (PID: {result['pid']})")
        else:
            self.logger.success(f"Port {port}/{protocol} kullanılabilir ({description})")
        
        return not in_use, result
    
    def check_all_ports(self) -> Tuple[bool, Dict]:
        """Tüm gerekli portları kontrol et"""
        self.logger.subsection(f"Port Kontrolü ({self.deployment_role})")
        
        required_ports = self._get_required_ports()
        if not required_ports:
            self.logger.warning(f"No port configuration found for role: {self.deployment_role}")
            return True, {}
        
        port_results = []
        all_available = True
        
        for port_info in required_ports:
            available, result = self.check_port_availability(
                port=port_info['port'],
                description=port_info['description'],
                protocol=port_info['protocol'],
                required=port_info['required']
            )
            port_results.append(result)
            
            # Required portlar kullanımdaysa fail
            if not available and port_info['required']:
                all_available = False
        
        self.results['ports'] = {
            'deployment_role': self.deployment_role,
            'checked_ports': port_results,
            'all_available': all_available,
            'status': 'pass' if all_available else 'fail'
        }
        
        return all_available, self.results['ports']
    
    def check_dns_resolution(self) -> Tuple[bool, Dict]:
        """DNS çözümleme kontrolü"""
        self.logger.subsection("DNS Çözümleme Kontrolü")
        
        # Hostname
        rc, hostname, _ = self.runner.run("hostname")
        
        # DNS ile çözümleyebiliyor muyuz?
        try:
            ip = socket.gethostbyname(hostname)
            dns_works = True
            self.logger.success(f"DNS çözümleme çalışıyor: {hostname} -> {ip}")
        except socket.gaierror:
            dns_works = False
            ip = None
            self.logger.warning(f"DNS çözümleme başarısız: {hostname}")
        
        result = {
            'hostname': hostname,
            'resolved_ip': ip,
            'dns_works': dns_works,
            'status': 'pass' if dns_works else 'warning'
        }
        
        self.results['dns'] = result
        return True, result  # Warning olsa da devam eder
    
    def check_network_interfaces(self) -> Tuple[bool, Dict]:
        """Network interface kontrolü"""
        self.logger.subsection("Network Interface Kontrolü")
        
        rc, output, _ = self.runner.run("ip -o -4 addr show", shell=True)
        
        interfaces = []
        if output:
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        interfaces.append({
                            'name': parts[1],
                            'ip': parts[3].split('/')[0]
                        })
        
        result = {
            'interfaces': interfaces,
            'count': len(interfaces),
            'status': 'pass' if interfaces else 'fail'
        }
        
        if interfaces:
            self.logger.success(f"Network interface bulundu: {len(interfaces)} adet")
            for iface in interfaces:
                self.logger.info(f"  - {iface['name']}: {iface['ip']}")
        else:
            self.logger.failure("Network interface bulunamadı!")
        
        self.results['interfaces'] = result
        return len(interfaces) > 0, result
    
    def test_connectivity(self, host: str, port: int = 80, timeout: int = 5) -> Tuple[bool, Dict]:
        """
        Remote host bağlantısını test et
        
        Args:
            host: Hedef host (IP veya hostname)
            port: Port numarası
            timeout: Timeout (saniye)
        
        Returns:
            Tuple[bool, Dict]: (connected, result_dict)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result_code = sock.connect_ex((host, port))
            sock.close()
            
            connected = (result_code == 0)
            
            result = {
                'host': host,
                'port': port,
                'connected': connected,
                'status': 'pass' if connected else 'fail'
            }
            
            if connected:
                self.logger.success(f"Bağlantı başarılı: {host}:{port}")
            else:
                self.logger.failure(f"Bağlantı başarısız: {host}:{port}")
            
            return connected, result
            
        except socket.gaierror:
            self.logger.failure(f"Host çözümlenemedi: {host}")
            return False, {'host': host, 'port': port, 'connected': False, 'error': 'DNS resolution failed'}
        except Exception as e:
            self.logger.failure(f"Bağlantı hatası: {str(e)}")
            return False, {'host': host, 'port': port, 'connected': False, 'error': str(e)}
    
    def run_all_checks(self, remote_server: Dict[str, str] = None) -> Tuple[bool, Dict]:
        """Tüm network kontrollerini çalıştır
        
        Args:
            remote_server: Remote sunucu bilgisi {'ip': '...', 'role': '...'}
        """
        self.logger.section("Network Kontrolü")
        
        checks = [
            self.check_network_interfaces(),
            self.check_dns_resolution(),
            self.check_all_ports()
        ]
        
        # Remote sunucu kontrolü (distributed deployment için)
        if remote_server and remote_server.get('ip'):
            self.logger.subsection(f"Remote Sunucu Bağlantı Kontrolü ({remote_server['role']})")
            remote_checks = self.check_remote_server_connectivity(
                remote_server['ip'], 
                remote_server['role']
            )
            checks.append((remote_checks[0], remote_checks[1]))
        
        all_passed = all(check[0] for check in checks)
        
        if all_passed:
            self.logger.success("\nTüm network kontrolleri başarılı!")
        else:
            self.logger.failure("\nBazı network kontrolleri başarısız!")
        
        return all_passed, self.results
    
    def check_remote_server_connectivity(self, remote_ip: str, remote_role: str) -> Tuple[bool, Dict]:
        """Remote sunucuya gerekli portlardan erişim kontrolü
        
        Args:
            remote_ip: Remote sunucunun IP adresi
            remote_role: Remote sunucunun rolü (IS-Only veya Web-Only)
        
        Returns:
            Tuple[bool, Dict]: (all_connected, results)
        """
        # Remote sunucuda olması gereken portları belirle
        remote_ports = self._get_ports_for_role(remote_role)
        
        if not remote_ports:
            self.logger.warning(f"Remote role için port bulunamadı: {remote_role}")
            return True, {}
        
        results = []
        all_connected = True
        
        self.logger.info(f"\nRemote sunucu: {remote_ip}")
        self.logger.info(f"Kontrol edilecek port sayısı: {len(remote_ports)}\n")
        
        for port_info in remote_ports:
            if port_info['required']:  # Sadece gerekli portları kontrol et
                connected, result = self.test_connectivity(
                    remote_ip, 
                    port_info['port'], 
                    timeout=5
                )
                result['description'] = port_info['description']
                results.append(result)
                
                if not connected:
                    all_connected = False
                    self.logger.failure(f"✗ {port_info['description']} ({port_info['port']}/tcp) erişilemez")
                else:
                    self.logger.success(f"✓ {port_info['description']} ({port_info['port']}/tcp) erişilebilir")
        
        self.results['remote_server'] = {
            'ip': remote_ip,
            'role': remote_role,
            'connectivity': results,
            'all_connected': all_connected,
            'status': 'pass' if all_connected else 'fail'
        }
        
        return all_connected, self.results['remote_server']
    
    def _get_ports_for_role(self, role: str) -> list:
        """Belirli bir rol için gerekli portları getir
        
        Args:
            role: Deployment rolü (Combined, IS-Only, Web-Only)
        
        Returns:
            list: Port bilgileri listesi
        """
        if role == "Combined":
            # Combined için hem IS hem Web portları
            is_ports = self.port_config.get('ports', {}).get('intelligence_server', [])
            web_ports = self.port_config.get('ports', {}).get('web_server', [])
            return is_ports + web_ports
        elif role == "IS-Only":
            return self.port_config.get('ports', {}).get('intelligence_server', [])
        elif role == "Web-Only":
            return self.port_config.get('ports', {}).get('web_server', [])
        else:
            return []


if __name__ == '__main__':
    # Test
    checker = NetworkCheck(deployment_role='Combined')
    passed, results = checker.run_all_checks()
    print(f"\nAll checks passed: {passed}")
