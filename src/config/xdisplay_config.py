"""
X Display Configuration Module
Xvfb kurulumu ve DISPLAY ayarları
"""

from typing import Dict, Tuple
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner
from ..utils.backup_manager import BackupManager


class XDisplayConfig:
    """X Display ve Xvfb yapılandırması"""
    
    XVFB_DISPLAY = ":99"
    XVFB_RESOLUTION = "1920x1080x24"
    
    def __init__(self):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.backup = BackupManager()
    
    def check_xvfb_installed(self) -> bool:
        """Xvfb kurulu mu kontrol et"""
        return self.runner.is_command_available('Xvfb')
    
    def install_xvfb(self) -> Tuple[bool, str]:
        """Xvfb'yi kur"""
        self.logger.subsection("Xvfb Kurulumu")
        
        if self.check_xvfb_installed():
            self.logger.success("Xvfb zaten kurulu")
            return True, "Already installed"
        
        self.logger.info("Xvfb kuruluyor...")
        
        # Distro detection
        from ..utils.distro_detector import DistroDetector
        distro = DistroDetector()
        pkg_manager = distro.get_package_manager()
        
        if pkg_manager in ['yum', 'dnf']:
            package = "xorg-x11-server-Xvfb"
        elif pkg_manager == 'apt':
            package = "xvfb"
        elif pkg_manager == 'zypper':
            package = "xorg-x11-server-Xvfb"
        else:
            self.logger.failure(f"Desteklenmeyen paket yöneticisi: {pkg_manager}")
            return False, "Unsupported package manager"
        
        rc, _, stderr = self.runner.run_sudo(f"{pkg_manager} install -y {package}", timeout=300)
        
        if rc == 0:
            self.logger.success("Xvfb kuruldu")
            return True, "Installed successfully"
        else:
            self.logger.failure(f"Xvfb kurulamadı: {stderr}")
            return False, stderr
    
    def create_xvfb_service(self) -> Tuple[bool, str]:
        """Systemd service dosyası oluştur"""
        self.logger.subsection("Xvfb Systemd Service")
        
        service_content = f"""[Unit]
Description=X Virtual Frame Buffer Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/Xvfb {self.XVFB_DISPLAY} -screen 0 {self.XVFB_RESOLUTION} -ac +extension GLX +render -noreset
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
        
        service_file = "/etc/systemd/system/xvfb.service"
        
        # Backup if exists
        if Path(service_file).exists():
            self.backup.backup_file(service_file, "Xvfb systemd service")
        
        try:
            # Write service file
            self.runner.run(f"sudo tee {service_file} > /dev/null", shell=True)
            rc, _, _ = self.runner.run(f"echo '{service_content}' | sudo tee {service_file}", shell=True)
            
            if rc != 0:
                self.logger.failure("Service dosyası oluşturulamadı")
                return False, "Failed to create service file"
            
            # Reload systemd
            self.runner.run_sudo("systemctl daemon-reload")
            
            # Enable service
            self.runner.run_sudo("systemctl enable xvfb.service")
            
            # Start service
            rc, _, stderr = self.runner.run_sudo("systemctl start xvfb.service")
            
            if rc == 0:
                self.logger.success("Xvfb service başlatıldı")
                return True, "Service created and started"
            else:
                self.logger.failure(f"Xvfb service başlatılamadı: {stderr}")
                return False, stderr
                
        except Exception as e:
            self.logger.failure(f"Service oluşturma hatası: {str(e)}")
            return False, str(e)
    
    def configure_display_env(self) -> Tuple[bool, str]:
        """DISPLAY environment variable ayarla"""
        self.logger.subsection("DISPLAY Environment Variable")
        
        # /etc/environment dosyasına ekle
        env_file = "/etc/environment"
        display_line = f"DISPLAY={self.XVFB_DISPLAY}"
        
        # Backup
        if Path(env_file).exists():
            self.backup.backup_file(env_file, "System environment variables")
        
        try:
            # Mevcut içeriği oku
            rc, content, _ = self.runner.run(f"cat {env_file}", shell=True)
            
            # DISPLAY zaten var mı?
            if "DISPLAY=" in content:
                self.logger.info("DISPLAY zaten ayarlanmış, güncelleniyor...")
                # DISPLAY satırını değiştir
                lines = content.split('\n')
                new_lines = [line if not line.startswith('DISPLAY=') else display_line for line in lines]
                new_content = '\n'.join(new_lines)
            else:
                # DISPLAY ekle
                new_content = content + f"\n{display_line}\n"
            
            # Dosyayı güncelle
            rc, _, _ = self.runner.run(f"echo '{new_content}' | sudo tee {env_file} > /dev/null", shell=True)
            
            if rc == 0:
                self.logger.success(f"DISPLAY ayarlandı: {self.XVFB_DISPLAY}")
                
                # Şu anki oturum için de ayarla
                self.runner.run(f"export DISPLAY={self.XVFB_DISPLAY}", shell=True)
                
                return True, "DISPLAY configured"
            else:
                self.logger.failure("DISPLAY ayarlanamadı")
                return False, "Failed to update environment file"
                
        except Exception as e:
            self.logger.failure(f"DISPLAY ayarlama hatası: {str(e)}")
            return False, str(e)
    
    def verify_xvfb(self) -> Tuple[bool, Dict]:
        """Xvfb'nin çalıştığını doğrula"""
        self.logger.subsection("Xvfb Doğrulama")
        
        # Service durumu
        rc, output, _ = self.runner.run("systemctl is-active xvfb.service", shell=True)
        service_active = (rc == 0 and output.strip() == 'active')
        
        # Process kontrolü
        rc, output, _ = self.runner.run("ps aux | grep Xvfb | grep -v grep", shell=True)
        process_running = (rc == 0 and 'Xvfb' in output)
        
        # DISPLAY değişkeni
        rc, display_value, _ = self.runner.run("echo $DISPLAY", shell=True)
        display_set = (display_value.strip() == self.XVFB_DISPLAY)
        
        result = {
            'service_active': service_active,
            'process_running': process_running,
            'display_set': display_set,
            'status': 'pass' if (service_active and process_running) else 'fail'
        }
        
        if service_active:
            self.logger.success("✓ Xvfb service aktif")
        else:
            self.logger.failure("✗ Xvfb service aktif değil")
        
        if process_running:
            self.logger.success("✓ Xvfb process çalışıyor")
        else:
            self.logger.failure("✗ Xvfb process çalışmıyor")
        
        if display_set:
            self.logger.success(f"✓ DISPLAY ayarlanmış: {self.XVFB_DISPLAY}")
        else:
            self.logger.warning(f"⚠ DISPLAY ayarlanmamış (şu anki değer: {display_value.strip()})")
        
        return result['status'] == 'pass', result
    
    def configure(self) -> Tuple[bool, Dict]:
        """Tam X Display yapılandırması"""
        self.logger.section("X Display Yapılandırması")
        
        results = {}
        
        # 1. Xvfb kur
        success, msg = self.install_xvfb()
        results['install'] = {'success': success, 'message': msg}
        if not success:
            return False, results
        
        # 2. Systemd service oluştur
        success, msg = self.create_xvfb_service()
        results['service'] = {'success': success, 'message': msg}
        if not success:
            return False, results
        
        # 3. DISPLAY environment variable
        success, msg = self.configure_display_env()
        results['environment'] = {'success': success, 'message': msg}
        
        # 4. Doğrula
        success, verify_result = self.verify_xvfb()
        results['verification'] = verify_result
        
        # Backup manifest kaydet
        self.backup.save_manifest()
        
        all_success = all(r.get('success', False) or r.get('status') == 'pass' 
                         for r in results.values() if isinstance(r, dict))
        
        if all_success:
            self.logger.success("\n✓ X Display yapılandırması tamamlandı!")
        else:
            self.logger.failure("\n✗ X Display yapılandırması başarısız!")
        
        return all_success, results


if __name__ == '__main__':
    # Test
    config = XDisplayConfig()
    success, results = config.configure()
    print(f"\nConfiguration successful: {success}")
