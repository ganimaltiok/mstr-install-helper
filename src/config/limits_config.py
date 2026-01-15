"""
System Limits Configuration Module
ulimit ayarlarını yapılandırır
"""

from typing import Dict, Tuple
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner
from ..utils.backup_manager import BackupManager


class LimitsConfig:
    """System limits yapılandırması"""
    
    LIMITS_FILE = "/etc/security/limits.conf"
    
    def __init__(self):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.backup = BackupManager()
        self.required_limits = self._load_required_limits()
    
    def _load_required_limits(self) -> Dict:
        """Gerekli limit değerlerini yükle"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'dependencies.yaml'
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('ulimits', {})
        except Exception as e:
            self.logger.warning(f"Could not load ulimits config: {str(e)}")
            return {'nofile': 65536, 'nproc': 4096}
    
    def configure_limits(self) -> Tuple[bool, Dict]:
        """limits.conf dosyasını yapılandır"""
        self.logger.section("System Limits Yapılandırması")
        
        if not Path(self.LIMITS_FILE).exists():
            self.logger.failure(f"limits.conf bulunamadı: {self.LIMITS_FILE}")
            return False, {'error': 'limits.conf not found'}
        
        # Backup
        self.backup.backup_file(self.LIMITS_FILE, "System limits configuration")
        
        try:
            # Mevcut içeriği oku
            rc, content, _ = self.runner.run(f"cat {self.LIMITS_FILE}")
            if rc != 0:
                return False, {'error': 'Failed to read limits.conf'}
            
            lines = content.split('\n')
            
            # MicroStrategy için gerekli limitler
            nofile = self.required_limits.get('nofile', 65536)
            nproc = self.required_limits.get('nproc', 4096)
            
            mstr_limits = [
                "",
                "# MicroStrategy Installation Requirements",
                "# Added by mstr-helper",
                f"*    soft    nofile    {nofile}",
                f"*    hard    nofile    {nofile}",
                f"*    soft    nproc     {nproc}",
                f"*    hard    nproc     {nproc}",
                ""
            ]
            
            # Eski MicroStrategy ayarlarını temizle
            new_lines = []
            skip_section = False
            
            for line in lines:
                if "MicroStrategy Installation Requirements" in line or "Added by mstr-helper" in line:
                    skip_section = True
                    continue
                
                if skip_section:
                    # Boş satır görene kadar atla
                    if line.strip() == "":
                        skip_section = False
                    continue
                
                new_lines.append(line)
            
            # Yeni limitleri ekle
            new_lines.extend(mstr_limits)
            new_content = '\n'.join(new_lines)
            
            # Dosyayı güncelle
            rc, _, stderr = self.runner.run(f"echo '{new_content}' | sudo tee {self.LIMITS_FILE} > /dev/null", shell=True)
            
            if rc != 0:
                self.logger.failure(f"limits.conf güncellenemedi: {stderr}")
                return False, {'error': stderr}
            
            self.logger.success("System limits yapılandırıldı")
            self.logger.info(f"  nofile (open files): {nofile}")
            self.logger.info(f"  nproc (processes): {nproc}")
            self.logger.warning("Not: Yeni oturumlar için geçerli olacak")
            
            # Backup manifest kaydet
            self.backup.save_manifest()
            
            result = {
                'nofile': nofile,
                'nproc': nproc,
                'status': 'pass'
            }
            
            return True, result
            
        except Exception as e:
            self.logger.failure(f"Limits yapılandırma hatası: {str(e)}")
            return False, {'error': str(e)}
    
    def configure_sysctl(self) -> Tuple[bool, Dict]:
        """Kernel parametrelerini yapılandır (opsiyonel)"""
        self.logger.subsection("Kernel Parameters (sysctl)")
        
        sysctl_file = "/etc/sysctl.conf"
        
        if not Path(sysctl_file).exists():
            self.logger.warning("sysctl.conf bulunamadı, atlanıyor")
            return True, {'status': 'skip'}
        
        # Backup
        self.backup.backup_file(sysctl_file, "Kernel parameters")
        
        try:
            # Önerilen kernel parametreleri
            kernel_params = [
                "",
                "# MicroStrategy Installation Requirements",
                "# Added by mstr-helper",
                "fs.file-max = 2097152",
                "kernel.pid_max = 65536",
                ""
            ]
            
            # Mevcut içeriği oku
            rc, content, _ = self.runner.run(f"cat {sysctl_file}")
            if rc != 0:
                return True, {'status': 'skip'}
            
            lines = content.split('\n')
            
            # Eski ayarları temizle
            new_lines = []
            skip_section = False
            
            for line in lines:
                if "MicroStrategy Installation Requirements" in line or "Added by mstr-helper" in line:
                    skip_section = True
                    continue
                
                if skip_section:
                    if line.strip() == "":
                        skip_section = False
                    continue
                
                new_lines.append(line)
            
            # Yeni parametreleri ekle
            new_lines.extend(kernel_params)
            new_content = '\n'.join(new_lines)
            
            # Dosyayı güncelle
            rc, _, _ = self.runner.run(f"echo '{new_content}' | sudo tee {sysctl_file} > /dev/null", shell=True)
            
            if rc == 0:
                # sysctl'i yeniden yükle
                self.runner.run_sudo("sysctl -p")
                self.logger.success("Kernel parametreleri güncellendi")
                return True, {'status': 'pass'}
            else:
                self.logger.warning("Kernel parametreleri güncellenemedi")
                return True, {'status': 'warning'}
                
        except Exception as e:
            self.logger.warning(f"sysctl yapılandırma hatası: {str(e)}")
            return True, {'status': 'warning'}
    
    def configure(self) -> Tuple[bool, Dict]:
        """Tüm system limits yapılandırmalarını yap"""
        results = {}
        
        # limits.conf
        success_limits, result_limits = self.configure_limits()
        results['limits'] = result_limits
        
        # sysctl (opsiyonel)
        success_sysctl, result_sysctl = self.configure_sysctl()
        results['sysctl'] = result_sysctl
        
        # limits.conf kritik
        if success_limits:
            self.logger.success("\n✓ System limits yapılandırıldı")
        else:
            self.logger.failure("\n✗ System limits yapılandırma başarısız!")
        
        return success_limits, results


if __name__ == '__main__':
    # Test
    config = LimitsConfig()
    success, results = config.configure()
    print(f"\nConfiguration successful: {success}")
