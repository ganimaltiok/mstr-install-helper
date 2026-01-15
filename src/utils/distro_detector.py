"""
Linux Distribution Detector
RHEL, CentOS, Ubuntu, Oracle Linux ve SLES dağıtımlarını tespit eder
"""

import platform
import os
import re
from typing import Dict, Optional


class DistroDetector:
    """Linux dağıtımını ve versiyonunu tespit eder"""
    
    def __init__(self):
        self.distro_info = self._detect_distro()
    
    def _detect_distro(self) -> Dict[str, str]:
        """
        Sistem dağıtımını tespit eder
        
        Returns:
            Dict: {
                'name': 'rhel'|'centos'|'ubuntu'|'oracle_linux'|'sles'|'unknown',
                'version': '8.5',
                'major_version': '8',
                'package_manager': 'yum'|'dnf'|'apt'|'zypper',
                'friendly_name': 'Red Hat Enterprise Linux 8.5'
            }
        """
        result = {
            'name': 'unknown',
            'version': 'unknown',
            'major_version': 'unknown',
            'package_manager': 'unknown',
            'friendly_name': 'Unknown Linux'
        }
        
        # /etc/os-release dosyasından bilgi al (modern sistemler)
        if os.path.exists('/etc/os-release'):
            os_release = self._parse_os_release()
            if os_release:
                result.update(self._interpret_os_release(os_release))
        
        # Fallback: legacy dosyalar
        elif os.path.exists('/etc/redhat-release'):
            result.update(self._parse_redhat_release())
        elif os.path.exists('/etc/lsb-release'):
            result.update(self._parse_lsb_release())
        
        return result
    
    def _parse_os_release(self) -> Dict[str, str]:
        """Parse /etc/os-release file"""
        os_release = {}
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes
                        value = value.strip('"').strip("'")
                        os_release[key] = value
        except Exception:
            pass
        return os_release
    
    def _interpret_os_release(self, os_release: Dict[str, str]) -> Dict[str, str]:
        """os-release bilgisini yorumla"""
        result = {}
        
        id_value = os_release.get('ID', '').lower()
        id_like = os_release.get('ID_LIKE', '').lower()
        version = os_release.get('VERSION_ID', 'unknown')
        pretty_name = os_release.get('PRETTY_NAME', 'Unknown Linux')
        
        result['version'] = version
        result['friendly_name'] = pretty_name
        
        # Major version
        if version != 'unknown':
            result['major_version'] = version.split('.')[0]
        
        # Distribution name
        if 'rhel' in id_value or 'rhel' in id_like:
            result['name'] = 'rhel'
            result['package_manager'] = 'dnf' if int(result.get('major_version', '0')) >= 8 else 'yum'
        elif 'centos' in id_value:
            result['name'] = 'centos'
            result['package_manager'] = 'dnf' if int(result.get('major_version', '0')) >= 8 else 'yum'
        elif 'ubuntu' in id_value:
            result['name'] = 'ubuntu'
            result['package_manager'] = 'apt'
        elif 'ol' in id_value or 'oracle' in id_value or 'oracle' in id_like:
            result['name'] = 'oracle_linux'
            result['package_manager'] = 'dnf' if int(result.get('major_version', '0')) >= 8 else 'yum'
        elif 'sles' in id_value or 'suse' in id_value:
            result['name'] = 'sles'
            result['package_manager'] = 'zypper'
        
        return result
    
    def _parse_redhat_release(self) -> Dict[str, str]:
        """Parse /etc/redhat-release for RHEL/CentOS"""
        result = {}
        try:
            with open('/etc/redhat-release', 'r') as f:
                content = f.read().strip()
                result['friendly_name'] = content
                
                # Extract version
                version_match = re.search(r'(\d+)\.(\d+)', content)
                if version_match:
                    result['version'] = f"{version_match.group(1)}.{version_match.group(2)}"
                    result['major_version'] = version_match.group(1)
                
                # Detect distro
                content_lower = content.lower()
                if 'red hat' in content_lower:
                    result['name'] = 'rhel'
                elif 'centos' in content_lower:
                    result['name'] = 'centos'
                elif 'oracle' in content_lower:
                    result['name'] = 'oracle_linux'
                
                result['package_manager'] = 'dnf' if int(result.get('major_version', '0')) >= 8 else 'yum'
        except Exception:
            pass
        return result
    
    def _parse_lsb_release(self) -> Dict[str, str]:
        """Parse /etc/lsb-release for Ubuntu/Debian"""
        result = {}
        try:
            with open('/etc/lsb-release', 'r') as f:
                for line in f:
                    if 'DISTRIB_ID' in line:
                        distro = line.split('=')[1].strip().lower()
                        if 'ubuntu' in distro:
                            result['name'] = 'ubuntu'
                            result['package_manager'] = 'apt'
                    elif 'DISTRIB_RELEASE' in line:
                        result['version'] = line.split('=')[1].strip()
                        result['major_version'] = result['version'].split('.')[0]
                    elif 'DISTRIB_DESCRIPTION' in line:
                        result['friendly_name'] = line.split('=')[1].strip().strip('"')
        except Exception:
            pass
        return result
    
    def get_name(self) -> str:
        """Dağıtım adını döndür"""
        return self.distro_info['name']
    
    def get_version(self) -> str:
        """Versiyon numarasını döndür"""
        return self.distro_info['version']
    
    def get_major_version(self) -> str:
        """Major version döndür"""
        return self.distro_info['major_version']
    
    def get_package_manager(self) -> str:
        """Paket yöneticisi adını döndür"""
        return self.distro_info['package_manager']
    
    def get_friendly_name(self) -> str:
        """Kullanıcı dostu sistem adını döndür"""
        return self.distro_info['friendly_name']
    
    def is_rhel_based(self) -> bool:
        """RHEL tabanlı mı (RHEL, CentOS, Oracle Linux)"""
        return self.distro_info['name'] in ['rhel', 'centos', 'oracle_linux']
    
    def is_debian_based(self) -> bool:
        """Debian tabanlı mı (Ubuntu)"""
        return self.distro_info['name'] == 'ubuntu'
    
    def is_supported(self) -> bool:
        """Desteklenen bir dağıtım mı"""
        return self.distro_info['name'] in ['rhel', 'centos', 'ubuntu', 'oracle_linux', 'sles']
    
    def get_all_info(self) -> Dict[str, str]:
        """Tüm bilgileri döndür"""
        return self.distro_info.copy()


if __name__ == '__main__':
    # Test
    detector = DistroDetector()
    print("Linux Distribution Information:")
    print(f"  Name: {detector.get_name()}")
    print(f"  Version: {detector.get_version()}")
    print(f"  Friendly Name: {detector.get_friendly_name()}")
    print(f"  Package Manager: {detector.get_package_manager()}")
    print(f"  RHEL-based: {detector.is_rhel_based()}")
    print(f"  Supported: {detector.is_supported()}")
