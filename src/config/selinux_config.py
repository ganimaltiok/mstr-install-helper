"""
SELinux Configuration Module
SELinux'u permissive moda alır
"""

from typing import Dict, Tuple
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner
from ..utils.backup_manager import BackupManager


class SELinuxConfig:
    """SELinux yapılandırması"""
    
    def __init__(self):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.backup = BackupManager()
    
    def check_selinux_exists(self) -> bool:
        """SELinux var mı?"""
        return self.runner.is_command_available('getenforce')
    
    def get_selinux_status(self) -> str:
        """SELinux durumunu döndür"""
        if not self.check_selinux_exists():
            return 'not_installed'
        
        rc, output, _ = self.runner.run("getenforce")
        if rc == 0:
            return output.strip().lower()
        
        return 'unknown'
    
    def set_selinux_permissive_runtime(self) -> Tuple[bool, str]:
        """SELinux'u runtime'da permissive yap"""
        self.logger.info("SELinux permissive moda alınıyor (runtime)...")
        
        rc, _, stderr = self.runner.run_sudo("setenforce 0")
        
        if rc == 0:
            self.logger.success("SELinux permissive moda alındı")
            return True, "Set to permissive"
        else:
            self.logger.failure(f"SELinux permissive yapılamadı: {stderr}")
            return False, stderr
    
    def set_selinux_permissive_persistent(self) -> Tuple[bool, str]:
        """SELinux'u kalıcı olarak permissive yap"""
        self.logger.info("SELinux permissive moda alınıyor (kalıcı)...")
        
        config_file = "/etc/selinux/config"
        
        if not Path(config_file).exists():
            self.logger.warning(f"SELinux config bulunamadı: {config_file}")
            return False, "Config file not found"
        
        # Backup
        self.backup.backup_file(config_file, "SELinux configuration")
        
        try:
            # Mevcut içeriği oku
            rc, content, _ = self.runner.run(f"cat {config_file}")
            if rc != 0:
                return False, "Failed to read config file"
            
            # SELINUX= satırını değiştir
            lines = content.split('\n')
            new_lines = []
            found = False
            
            for line in lines:
                if line.strip().startswith('SELINUX=') and not line.strip().startswith('#'):
                    new_lines.append('SELINUX=permissive')
                    found = True
                else:
                    new_lines.append(line)
            
            # SELINUX= satırı yoksa ekle
            if not found:
                new_lines.append('SELINUX=permissive')
            
            new_content = '\n'.join(new_lines)
            
            # Dosyayı güncelle
            rc, _, stderr = self.runner.run(f"echo '{new_content}' | sudo tee {config_file} > /dev/null", shell=True)
            
            if rc == 0:
                self.logger.success("SELinux config güncellendi (reboot sonrası geçerli)")
                return True, "Config updated"
            else:
                self.logger.failure(f"SELinux config güncellenemedi: {stderr}")
                return False, stderr
                
        except Exception as e:
            self.logger.failure(f"SELinux config güncelleme hatası: {str(e)}")
            return False, str(e)
    
    def configure(self) -> Tuple[bool, Dict]:
        """SELinux yapılandır"""
        self.logger.section("SELinux Yapılandırması")
        
        # SELinux var mı?
        if not self.check_selinux_exists():
            self.logger.info("SELinux yüklü değil, atlaniyor")
            return True, {'selinux_exists': False, 'status': 'skip'}
        
        # Mevcut durum
        current_status = self.get_selinux_status()
        self.logger.info(f"Mevcut SELinux durumu: {current_status}")
        
        if current_status == 'permissive':
            self.logger.success("SELinux zaten permissive modda")
            return True, {'selinux_status': current_status, 'status': 'pass'}
        
        if current_status == 'disabled':
            self.logger.info("SELinux disabled, yapılandırma gerekmiyor")
            return True, {'selinux_status': current_status, 'status': 'skip'}
        
        results = {}
        
        # Runtime değişiklik
        success_runtime, msg_runtime = self.set_selinux_permissive_runtime()
        results['runtime'] = {'success': success_runtime, 'message': msg_runtime}
        
        # Kalıcı değişiklik
        success_persistent, msg_persistent = self.set_selinux_permissive_persistent()
        results['persistent'] = {'success': success_persistent, 'message': msg_persistent}
        
        # Yeni durumu kontrol et
        new_status = self.get_selinux_status()
        results['new_status'] = new_status
        
        # Backup manifest kaydet
        self.backup.save_manifest()
        
        all_success = success_runtime and success_persistent
        results['status'] = 'pass' if all_success else 'fail'
        
        if all_success:
            self.logger.success("\n✓ SELinux permissive moda alındı")
            self.logger.warning("Not: Kalıcı değişiklik için reboot gerekebilir")
        else:
            self.logger.failure("\n✗ SELinux yapılandırma başarısız!")
        
        return all_success, results


if __name__ == '__main__':
    # Test
    config = SELinuxConfig()
    success, results = config.configure()
    print(f"\nConfiguration successful: {success}")
