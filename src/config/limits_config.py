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
    
    def configure_limits(self, username: str = None) -> Tuple[bool, Dict]:
        """
        limits.conf dosyasını yapılandır
        
        Args:
            username: Specific user için limits (None = global/wildcard *)
        """
        self.logger.section("System Limits Yapılandırması")
        
        if username:
            self.logger.info(f"Kullanıcı-specific limits: {username}")
        else:
            self.logger.info("Global limits (tüm kullanıcılar)")
        
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
            nofile = self.required_limits.get('nofile', 65535)
            nproc = self.required_limits.get('nproc', 8194)
            stack = self.required_limits.get('stack', 8388608)  # 8 MB in bytes
            
            # User prefix (username veya wildcard *)
            user_prefix = username if username else "*"
            
            mstr_limits = [
                "",
                f"# MicroStrategy Installation Requirements ({user_prefix})",
                "# Based on: https://www2.microstrategy.com/producthelp/current/installconfig/en-us/Content/Recommended_system_settings_for_UNIX_and_Linux.htm",
                "# Added by mstr-helper",
                f"{user_prefix}    soft    nofile    {nofile}",
                f"{user_prefix}    hard    nofile    {nofile}",
                f"{user_prefix}    soft    nproc     {nproc}",
                f"{user_prefix}    hard    nproc     {nproc}",
                f"{user_prefix}    soft    stack     {stack}",
                f"{user_prefix}    hard    stack     {stack}",
                "# Recommended unlimited settings:",
                f"{user_prefix}    soft    cpu       unlimited",
                f"{user_prefix}    hard    cpu       unlimited",
                f"{user_prefix}    soft    fsize     unlimited",
                f"{user_prefix}    hard    fsize     unlimited",
                f"{user_prefix}    soft    data      unlimited",
                f"{user_prefix}    hard    data      unlimited",
                f"{user_prefix}    soft    memlock   unlimited",
                f"{user_prefix}    hard    memlock   unlimited",
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
            
            self.logger.success(f"System limits yapılandırıldı ({user_prefix})")
            self.logger.info(f"  nofile (open files): {nofile}")
            self.logger.info(f"  nproc (processes): {nproc}")
            self.logger.info(f"  stack (stack size): {stack // 1024 // 1024} MB")
            self.logger.info(f"  cpu, fsize, data, memlock: unlimited")
            if username:
                self.logger.info(f"  → Sadece '{username}' kullanıcısı için geçerli")
            self.logger.warning("Not: Yeni oturumlar için geçerli olacak")
            
            # Backup manifest kaydet
            self.backup.save_manifest()
            
            result = {
                'nofile': nofile,
                'nproc': nproc,
                'username': username,
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
                "# Required for Platform Analytics (Strategy One)",
                "vm.max_map_count = 5242880",
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
    
    def configure(self, username: str = None) -> Tuple[bool, Dict]:
        """Tüm system limits yapılandırmalarını yap"""
        results = {}
        
        # limits.conf
        success_limits, result_limits = self.configure_limits(username=username)
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
