"""
Rollback Module
Yapılan değişiklikleri geri alır
"""

from typing import Dict, Tuple
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.backup_manager import BackupManager
from ..utils.command_runner import get_command_runner


class Rollback:
    """Yapılandırma değişikliklerini geri alır"""
    
    def __init__(self):
        self.logger = get_logger()
        self.backup = BackupManager()
        self.runner = get_command_runner()
        self.results = {}
    
    def list_available_backups(self) -> list:
        """Mevcut backup'ları listele"""
        return self.backup.list_backups()
    
    def rollback_firewall(self) -> Tuple[bool, str]:
        """Firewall kurallarını geri al"""
        self.logger.subsection("Firewall Rollback")
        
        # Firewall tipini tespit et
        from ..utils.distro_detector import DistroDetector
        distro = DistroDetector()
        
        firewall_type = None
        if self.runner.is_command_available('firewall-cmd'):
            rc, output, _ = self.runner.run("systemctl is-active firewalld", shell=True)
            if rc == 0 and output.strip() == 'active':
                firewall_type = 'firewalld'
        elif self.runner.is_command_available('ufw'):
            firewall_type = 'ufw'
        elif self.runner.is_command_available('iptables'):
            firewall_type = 'iptables'
        
        if not firewall_type:
            self.logger.warning("Firewall bulunamadı, rollback atlanıyor")
            return True, "No firewall found"
        
        self.logger.info(f"Firewall type: {firewall_type}")
        self.logger.warning("Firewall kuralları manuel temizlenmelidir")
        self.logger.info("MicroStrategy portlarını manuel kapatmak için:")
        
        if firewall_type == 'firewalld':
            self.logger.info("  firewall-cmd --permanent --remove-port=34952/tcp")
            self.logger.info("  firewall-cmd --permanent --remove-port=8080/tcp")
            self.logger.info("  firewall-cmd --reload")
        elif firewall_type == 'ufw':
            self.logger.info("  ufw delete allow 34952/tcp")
            self.logger.info("  ufw delete allow 8080/tcp")
        
        return True, "Manual cleanup required"
    
    def rollback_selinux(self) -> Tuple[bool, str]:
        """SELinux ayarlarını geri al"""
        self.logger.subsection("SELinux Rollback")
        
        config_file = "/etc/selinux/config"
        
        if not Path(config_file).exists():
            self.logger.info("SELinux config bulunamadı, atlanıyor")
            return True, "No SELinux config"
        
        # Backup'tan geri yükle
        success = self.backup.restore_file(config_file)
        
        if success:
            self.logger.success("SELinux config geri yüklendi")
            self.logger.warning("Değişikliklerin geçerli olması için reboot gerekli")
            return True, "Restored from backup"
        else:
            self.logger.failure("SELinux config geri yüklenemedi")
            return False, "Restore failed"
    
    def rollback_limits(self) -> Tuple[bool, str]:
        """System limits'i geri al"""
        self.logger.subsection("System Limits Rollback")
        
        limits_file = "/etc/security/limits.conf"
        
        if not Path(limits_file).exists():
            self.logger.info("limits.conf bulunamadı, atlanıyor")
            return True, "No limits.conf"
        
        # Backup'tan geri yükle
        success = self.backup.restore_file(limits_file)
        
        if success:
            self.logger.success("limits.conf geri yüklendi")
            self.logger.warning("Yeni oturumlar için geçerli olacak")
            return True, "Restored from backup"
        else:
            self.logger.failure("limits.conf geri yüklenemedi")
            return False, "Restore failed"
    
    def rollback_xvfb(self) -> Tuple[bool, str]:
        """Xvfb servisini durdur ve kaldır"""
        self.logger.subsection("Xvfb Rollback")
        
        # Servisi durdur
        rc, _, _ = self.runner.run_sudo("systemctl stop xvfb.service")
        if rc == 0:
            self.logger.success("Xvfb servisi durduruldu")
        
        # Servisi disable et
        self.runner.run_sudo("systemctl disable xvfb.service")
        
        # Service dosyasını sil
        service_file = "/etc/systemd/system/xvfb.service"
        if Path(service_file).exists():
            self.runner.run_sudo(f"rm {service_file}")
            self.runner.run_sudo("systemctl daemon-reload")
            self.logger.success("Xvfb service dosyası kaldırıldı")
        
        # /etc/environment'tan DISPLAY'i temizle
        env_file = "/etc/environment"
        if Path(env_file).exists():
            success = self.backup.restore_file(env_file)
            if success:
                self.logger.success("/etc/environment geri yüklendi")
            else:
                self.logger.warning("/etc/environment geri yüklenemedi")
        
        return True, "Xvfb removed"
    
    def rollback(self, backup_id: str = None) -> Tuple[bool, Dict]:
        """Tüm değişiklikleri geri al"""
        self.logger.section("Rollback İşlemi")
        
        # Mevcut backup'ları listele
        backups = self.list_available_backups()
        
        if not backups:
            self.logger.warning("Hiç backup bulunamadı!")
            return False, {'error': 'No backups found'}
        
        # Backup ID belirtilmemişse en son backup'ı kullan
        if backup_id is None:
            backup_id = backups[0]['backup_id']
            self.logger.info(f"En son backup kullanılıyor: {backup_id}")
        
        self.logger.info(f"Backup: {backup_id}\n")
        
        # Rollback işlemleri
        results = {}
        
        # 1. Xvfb
        success, msg = self.rollback_xvfb()
        results['xvfb'] = {'success': success, 'message': msg}
        
        # 2. Firewall
        success, msg = self.rollback_firewall()
        results['firewall'] = {'success': success, 'message': msg}
        
        # 3. SELinux
        success, msg = self.rollback_selinux()
        results['selinux'] = {'success': success, 'message': msg}
        
        # 4. System Limits
        success, msg = self.rollback_limits()
        results['limits'] = {'success': success, 'message': msg}
        
        self.results = results
        
        # Özet
        self.logger.section("Rollback Özeti")
        
        failed = [k for k, v in results.items() if not v['success']]
        
        if not failed:
            self.logger.success("✓ ROLLBACK TAMAMLANDI")
            self.logger.info("\nNot: Bazı değişiklikler için reboot gerekebilir")
        else:
            self.logger.warning(f"⚠ Bazı rollback işlemleri başarısız: {', '.join(failed)}")
        
        return len(failed) == 0, results


if __name__ == '__main__':
    # Test
    rollback = Rollback()
    success, results = rollback.rollback()
    print(f"\nRollback successful: {success}")
