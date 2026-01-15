"""
Firewall Configuration Module
Firewall kurallarını deployment role'e göre yapılandırır
"""

from typing import Dict, List, Tuple
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner
from ..utils.distro_detector import DistroDetector


class FirewallConfig:
    """Firewall yapılandırması"""
    
    def __init__(self, deployment_role: str = 'Combined'):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.distro = DistroDetector()
        self.deployment_role = deployment_role
        self.port_config = self._load_port_config()
        self.firewall_type = self._detect_firewall()
    
    def _load_port_config(self) -> Dict:
        """Port config yükle"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'port_requirements.yaml'
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load port config: {str(e)}")
            return {}
    
    def _detect_firewall(self) -> str:
        """Hangi firewall kullanılıyor?"""
        if self.runner.is_command_available('firewall-cmd'):
            # firewalld durumu
            rc, output, _ = self.runner.run("systemctl is-active firewalld", shell=True)
            if rc == 0 and output.strip() == 'active':
                return 'firewalld'
        
        if self.runner.is_command_available('ufw'):
            # ufw durumu
            rc, output, _ = self.runner.run("ufw status", shell=True)
            if 'active' in output.lower():
                return 'ufw'
        
        if self.runner.is_command_available('iptables'):
            # iptables var mı?
            rc, output, _ = self.runner.run("iptables -L", shell=True)
            if rc == 0:
                return 'iptables'
        
        return 'none'
    
    def _get_required_ports(self) -> List[Dict]:
        """Deployment role'e göre portlar"""
        required_ports = []
        
        role_config = self.port_config.get('deployment_roles', {}).get(self.deployment_role, {})
        port_groups = role_config.get('ports', [])
        
        for group in port_groups:
            ports = self.port_config.get('ports', {}).get(group, [])
            required_ports.extend(ports)
        
        return required_ports
    
    def configure_firewalld(self, ports: List[Dict]) -> Tuple[bool, List[str]]:
        """firewalld ile portları aç"""
        self.logger.info("firewalld kullanılarak portlar açılıyor...")
        
        added_rules = []
        failed = []
        
        for port_info in ports:
            if not port_info['required']:
                continue
            
            port = port_info['port']
            protocol = port_info['protocol']
            
            # Port ekle
            cmd = f"firewall-cmd --permanent --add-port={port}/{protocol}"
            rc, _, stderr = self.runner.run_sudo(cmd)
            
            if rc == 0:
                added_rules.append(f"{port}/{protocol}")
                self.logger.success(f"✓ Port eklendi: {port}/{protocol}")
            else:
                failed.append(f"{port}/{protocol}: {stderr}")
                self.logger.failure(f"✗ Port eklenemedi: {port}/{protocol}")
        
        # Reload firewall
        if added_rules:
            self.runner.run_sudo("firewall-cmd --reload")
            self.logger.info("Firewall kuralları yüklendi")
        
        return len(failed) == 0, added_rules
    
    def configure_ufw(self, ports: List[Dict]) -> Tuple[bool, List[str]]:
        """ufw ile portları aç"""
        self.logger.info("ufw kullanılarak portlar açılıyor...")
        
        added_rules = []
        failed = []
        
        for port_info in ports:
            if not port_info['required']:
                continue
            
            port = port_info['port']
            protocol = port_info['protocol']
            
            # Port ekle
            cmd = f"ufw allow {port}/{protocol}"
            rc, _, stderr = self.runner.run_sudo(cmd)
            
            if rc == 0:
                added_rules.append(f"{port}/{protocol}")
                self.logger.success(f"✓ Port eklendi: {port}/{protocol}")
            else:
                failed.append(f"{port}/{protocol}: {stderr}")
                self.logger.failure(f"✗ Port eklenemedi: {port}/{protocol}")
        
        # ufw durumunu kontrol et - eğer inactive ise enable et
        rc, status, _ = self.runner.run("ufw status", shell=True)
        if 'inactive' in status.lower():
            self.logger.info("ufw aktif değil, aktif ediliyor...")
            self.runner.run_sudo("ufw --force enable")
        
        return len(failed) == 0, added_rules
    
    def configure_iptables(self, ports: List[Dict]) -> Tuple[bool, List[str]]:
        """iptables ile portları aç"""
        self.logger.info("iptables kullanılarak portlar açılıyor...")
        
        added_rules = []
        failed = []
        
        for port_info in ports:
            if not port_info['required']:
                continue
            
            port = port_info['port']
            protocol = port_info['protocol']
            
            # Kural ekle
            cmd = f"iptables -A INPUT -p {protocol} --dport {port} -j ACCEPT"
            rc, _, stderr = self.runner.run_sudo(cmd)
            
            if rc == 0:
                added_rules.append(f"{port}/{protocol}")
                self.logger.success(f"✓ Port eklendi: {port}/{protocol}")
            else:
                failed.append(f"{port}/{protocol}: {stderr}")
                self.logger.failure(f"✗ Port eklenemedi: {port}/{protocol}")
        
        # Kuralları kaydet
        if added_rules:
            if self.distro.is_rhel_based():
                self.runner.run_sudo("service iptables save")
            elif self.distro.is_debian_based():
                self.runner.run_sudo("iptables-save > /etc/iptables/rules.v4", shell=True)
        
        return len(failed) == 0, added_rules
    
    def configure(self) -> Tuple[bool, Dict]:
        """Firewall yapılandır"""
        self.logger.section("Firewall Yapılandırması")
        
        self.logger.info(f"Deployment Role: {self.deployment_role}")
        self.logger.info(f"Firewall Type: {self.firewall_type}")
        
        if self.firewall_type == 'none':
            self.logger.warning("Firewall bulunamadı veya aktif değil")
            return True, {'firewall_type': 'none', 'status': 'skip'}
        
        required_ports = self._get_required_ports()
        
        if not required_ports:
            self.logger.warning("Port listesi bulunamadı")
            return True, {'status': 'skip'}
        
        self.logger.info(f"Açılacak port sayısı: {len([p for p in required_ports if p['required']])}\n")
        
        # Firewall tipine göre yapılandır
        if self.firewall_type == 'firewalld':
            success, added_rules = self.configure_firewalld(required_ports)
        elif self.firewall_type == 'ufw':
            success, added_rules = self.configure_ufw(required_ports)
        elif self.firewall_type == 'iptables':
            success, added_rules = self.configure_iptables(required_ports)
        else:
            return False, {'error': f'Unsupported firewall: {self.firewall_type}'}
        
        result = {
            'firewall_type': self.firewall_type,
            'added_rules': added_rules,
            'rule_count': len(added_rules),
            'status': 'pass' if success else 'fail'
        }
        
        if success:
            self.logger.success(f"\n✓ Firewall yapılandırıldı ({len(added_rules)} kural)")
        else:
            self.logger.failure("\n✗ Firewall yapılandırma başarısız!")
        
        return success, result


if __name__ == '__main__':
    # Test
    config = FirewallConfig(deployment_role='Combined')
    success, result = config.configure()
    print(f"\nConfiguration successful: {success}")
