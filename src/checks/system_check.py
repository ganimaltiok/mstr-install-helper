"""
System Check Module
CPU, RAM, Disk, Swap ve ulimit kontrollerini yapar
"""

import os
import psutil
from typing import Dict, List, Tuple
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner


class SystemCheck:
    """Sistem kaynaklarını kontrol eder"""
    
    def __init__(self):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.requirements = self._load_requirements()
        self.results: Dict = {}
    
    def _load_requirements(self) -> Dict:
        """Gereksinimleri config'den yükle"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'dependencies.yaml'
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('system_requirements', {})
        except Exception as e:
            self.logger.warning(f"Could not load system requirements: {str(e)}")
            return {}
    
    def check_cpu(self) -> Tuple[bool, Dict]:
        """CPU kontrolü"""
        self.logger.subsection("CPU Kontrolü")
        
        cpu_count = psutil.cpu_count(logical=False)  # Physical cores
        cpu_count_logical = psutil.cpu_count(logical=True)  # Logical cores
        cpu_percent = psutil.cpu_percent(interval=1)
        
        min_required = self.requirements.get('min_cpu_cores', 4)
        recommended = self.requirements.get('recommended_cpu_cores', 8)
        
        result = {
            'physical_cores': cpu_count,
            'logical_cores': cpu_count_logical,
            'usage_percent': cpu_percent,
            'min_required': min_required,
            'recommended': recommended,
            'status': 'pass' if cpu_count >= min_required else 'fail'
        }
        
        if cpu_count >= recommended:
            self.logger.success(f"CPU: {cpu_count} fiziksel core (Önerilen: {recommended}+)")
        elif cpu_count >= min_required:
            self.logger.info(f"CPU: {cpu_count} fiziksel core (Minimum: {min_required}, Önerilen: {recommended})")
        else:
            self.logger.failure(f"CPU: {cpu_count} fiziksel core (Minimum gereksinim: {min_required})")
        
        self.results['cpu'] = result
        return result['status'] == 'pass', result
    
    def check_memory(self) -> Tuple[bool, Dict]:
        """RAM kontrolü"""
        self.logger.subsection("RAM Kontrolü")
        
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        available_gb = mem.available / (1024 ** 3)
        used_percent = mem.percent
        
        min_required = self.requirements.get('min_ram_gb', 8)
        recommended = self.requirements.get('recommended_ram_gb', 16)
        
        result = {
            'total_gb': round(total_gb, 2),
            'available_gb': round(available_gb, 2),
            'used_percent': used_percent,
            'min_required': min_required,
            'recommended': recommended,
            'status': 'pass' if total_gb >= min_required else 'fail'
        }
        
        if total_gb >= recommended:
            self.logger.success(f"RAM: {result['total_gb']} GB (Önerilen: {recommended}+ GB)")
        elif total_gb >= min_required:
            self.logger.info(f"RAM: {result['total_gb']} GB (Minimum: {min_required} GB, Önerilen: {recommended} GB)")
        else:
            self.logger.failure(f"RAM: {result['total_gb']} GB (Minimum gereksinim: {min_required} GB)")
        
        self.results['memory'] = result
        return result['status'] == 'pass', result
    
    def check_disk(self, paths: List[str] = None) -> Tuple[bool, Dict]:
        """Disk alanı kontrolü"""
        self.logger.subsection("Disk Alanı Kontrolü")
        
        if paths is None:
            paths = ['/', '/opt', '/var', '/tmp']
        
        min_required = self.requirements.get('min_disk_gb', 60)
        recommended = self.requirements.get('recommended_disk_gb', 100)
        
        disk_info = {}
        all_pass = True
        
        for path in paths:
            if not os.path.exists(path):
                continue
            
            try:
                usage = psutil.disk_usage(path)
                total_gb = usage.total / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                used_percent = usage.percent
                
                # Root için minimum kontrolü
                status = 'pass' if (path == '/' and free_gb >= min_required) or path != '/' else 'pass'
                if path == '/' and free_gb < min_required:
                    status = 'fail'
                    all_pass = False
                
                disk_info[path] = {
                    'total_gb': round(total_gb, 2),
                    'free_gb': round(free_gb, 2),
                    'used_percent': used_percent,
                    'status': status
                }
                
                if path == '/':
                    if free_gb >= recommended:
                        self.logger.success(f"Disk ({path}): {disk_info[path]['free_gb']} GB boş (Önerilen: {recommended}+ GB)")
                    elif free_gb >= min_required:
                        self.logger.info(f"Disk ({path}): {disk_info[path]['free_gb']} GB boş (Minimum: {min_required} GB)")
                    else:
                        self.logger.failure(f"Disk ({path}): {disk_info[path]['free_gb']} GB boş (Minimum: {min_required} GB)")
                else:
                    self.logger.info(f"Disk ({path}): {disk_info[path]['free_gb']} GB boş")
                    
            except Exception as e:
                self.logger.warning(f"Could not check disk usage for {path}: {str(e)}")
        
        result = {
            'disks': disk_info,
            'min_required': min_required,
            'recommended': recommended,
            'status': 'pass' if all_pass else 'fail'
        }
        
        self.results['disk'] = result
        return result['status'] == 'pass', result
    
    def check_swap(self) -> Tuple[bool, Dict]:
        """Swap alanı kontrolü"""
        self.logger.subsection("Swap Alanı Kontrolü")
        
        swap = psutil.swap_memory()
        total_gb = swap.total / (1024 ** 3)
        used_gb = swap.used / (1024 ** 3)
        free_gb = swap.free / (1024 ** 3)
        used_percent = swap.percent
        
        min_required = self.requirements.get('min_swap_gb', 8)
        recommended = self.requirements.get('recommended_swap_gb', 16)
        
        result = {
            'total_gb': round(total_gb, 2),
            'used_gb': round(used_gb, 2),
            'free_gb': round(free_gb, 2),
            'used_percent': used_percent,
            'min_required': min_required,
            'recommended': recommended,
            'status': 'pass' if total_gb >= min_required else 'warning'
        }
        
        if total_gb >= recommended:
            self.logger.success(f"Swap: {result['total_gb']} GB (Önerilen: {recommended}+ GB)")
        elif total_gb >= min_required:
            self.logger.info(f"Swap: {result['total_gb']} GB (Minimum: {min_required} GB, Önerilen: {recommended} GB)")
        elif total_gb > 0:
            self.logger.warning(f"Swap: {result['total_gb']} GB (Önerilen minimum: {min_required} GB)")
            self.logger.warning("⚠ Düşük swap performans sorunlarına neden olabilir")
            needed_gb = min_required - total_gb
            self.logger.info(f"Swap artırmak için: sudo dd if=/dev/zero of=/swapfile bs=1G count={int(needed_gb)+1}")
            self.logger.info("                      sudo chmod 600 /swapfile")
            self.logger.info("                      sudo mkswap /swapfile")
            self.logger.info("                      sudo swapon /swapfile")
            self.logger.info("                      echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")
        else:
            self.logger.warning("Swap alanı bulunamadı")
            self.logger.warning("⚠ Swap oluşturmak için yukarıdaki komutları kullanabilirsiniz")
        
        self.results['swap'] = result
        return result['status'] != 'fail', result
    
    def check_ulimits(self) -> Tuple[bool, Dict]:
        """ulimit kontrolü"""
        self.logger.subsection("System Limits Kontrolü")
        
        # Config'ten yükle, yoksa MicroStrategy önerilen değerleri kullan
        required_nofile = self.requirements.get('ulimits', {}).get('nofile', 65535)
        required_nproc = self.requirements.get('ulimits', {}).get('nproc', 8194)
        
        # Open files limit
        rc, nofile_soft, _ = self.runner.run("ulimit -Sn", shell=True)
        rc, nofile_hard, _ = self.runner.run("ulimit -Hn", shell=True)
        
        # Process limit
        rc, nproc_soft, _ = self.runner.run("ulimit -Su", shell=True)
        rc, nproc_hard, _ = self.runner.run("ulimit -Hu", shell=True)
        
        try:
            nofile_soft_val = int(nofile_soft) if nofile_soft and nofile_soft != 'unlimited' else 999999
            nofile_hard_val = int(nofile_hard) if nofile_hard and nofile_hard != 'unlimited' else 999999
            nproc_soft_val = int(nproc_soft) if nproc_soft and nproc_soft != 'unlimited' else 999999
            nproc_hard_val = int(nproc_hard) if nproc_hard and nproc_hard != 'unlimited' else 999999
        except ValueError:
            nofile_soft_val = nofile_hard_val = nproc_soft_val = nproc_hard_val = 0
        
        nofile_ok = nofile_soft_val >= required_nofile
        nproc_ok = nproc_soft_val >= required_nproc
        
        result = {
            'nofile': {
                'soft': nofile_soft,
                'hard': nofile_hard,
                'required': required_nofile,
                'status': 'pass' if nofile_ok else 'fail'
            },
            'nproc': {
                'soft': nproc_soft,
                'hard': nproc_hard,
                'required': required_nproc,
                'status': 'pass' if nproc_ok else 'fail'
            },
            'status': 'pass' if (nofile_ok and nproc_ok) else 'fail'
        }
        
        if nofile_ok:
            self.logger.success(f"Open files limit: {nofile_soft} (Gerekli: {required_nofile})")
        else:
            self.logger.failure(f"Open files limit: {nofile_soft} (Gerekli: {required_nofile})")
        
        if nproc_ok:
            self.logger.success(f"Process limit: {nproc_soft} (Gerekli: {required_nproc})")
        else:
            self.logger.failure(f"Process limit: {nproc_soft} (Gerekli: {required_nproc})")
        
        self.results['ulimits'] = result
        return result['status'] == 'pass', result
    
    def check_hostname(self) -> Tuple[bool, Dict]:
        """Hostname kontrolü"""
        self.logger.subsection("Hostname Kontrolü")
        
        rc, hostname, _ = self.runner.run("hostname")
        rc2, fqdn, _ = self.runner.run("hostname -f")
        
        result = {
            'hostname': hostname.strip() if hostname else '',
            'fqdn': fqdn.strip() if fqdn else '',
            'resolvable': fqdn and '.' in fqdn and fqdn != hostname,
            'status': 'pass' if fqdn and '.' in fqdn else 'warning',
            'needs_fix': not (fqdn and '.' in fqdn)
        }
        
        if result['resolvable']:
            self.logger.success(f"Hostname: {hostname.strip()} (FQDN: {fqdn.strip()})")
        else:
            self.logger.warning(f"Hostname: {hostname.strip()} (FQDN çözümlenemedi, DNS ayarlarını kontrol edin)")
        
        self.results['hostname'] = result
        return True, result  # Warning olsa da devam eder
    
    def fix_hostname_fqdn(self, fqdn: str = None) -> bool:
        """FQDN sorununu /etc/hosts dosyasını düzenleyerek çöz
        
        Args:
            fqdn: Kullanıcıdan alınan FQDN (örn: mstrserver.company.com)
                 None ise otomatik olarak hostname.localdomain kullanılır
        """
        hostname_data = self.results.get('hostname', {})
        
        if not hostname_data.get('needs_fix'):
            return True
        
        self.logger.subsection("FQDN Sorunu Düzeltiliyor")
        
        hostname = hostname_data.get('hostname', '').strip()
        if not hostname:
            self.logger.failure("Hostname alınamadı")
            return False
        
        # FQDN kullan veya oluştur
        if not fqdn:
            fqdn = f"{hostname}.localdomain"
            self.logger.info(f"FQDN otomatik oluşturuldu: {fqdn}")
        else:
            self.logger.info(f"Kullanıcı tarafından belirlenen FQDN: {fqdn}")
        
        # FQDN'yi results'a kaydet (cheatsheet için)
        self.results['hostname']['fqdn_configured'] = fqdn
        
        # IP adresi al
        rc, ip_output, _ = self.runner.run("hostname -I")
        ip_address = ip_output.strip().split()[0] if ip_output else "127.0.0.1"
        
        try:
            # /etc/hosts dosyasını oku
            hosts_file = "/etc/hosts"
            from ..utils.backup_manager import get_backup_manager
            backup = get_backup_manager()
            
            # Backup al
            if Path(hosts_file).exists():
                backup.backup_file(hosts_file, "System hosts file")
            
            rc, content, _ = self.runner.run(f"cat {hosts_file}")
            if rc != 0:
                self.logger.failure("hosts dosyası okunamadı")
                return False
            
            lines = content.split('\n') if content else []
            new_lines = []
            hostname_added = False
            
            # Mevcut hostname girdilerini temizle ve yeni ekle
            for line in lines:
                # Bu hostname'i içeren satırları atla
                if hostname in line and not line.strip().startswith('#'):
                    continue
                new_lines.append(line)
            
            # Yeni FQDN girdisini ekle (127.0.0.1'den önce)
            new_entry = f"{ip_address}  {fqdn} {hostname}"
            
            # 127.0.0.1 satırından önce ekle
            final_lines = []
            inserted = False
            for line in new_lines:
                if '127.0.0.1' in line and not inserted:
                    final_lines.append(new_entry)
                    inserted = True
                final_lines.append(line)
            
            if not inserted:
                final_lines.insert(0, new_entry)
            
            new_content = '\n'.join(final_lines)
            
            # Dosyayı güncelle
            temp_file = "/tmp/hosts_temp"
            with open(temp_file, 'w') as f:
                f.write(new_content)
            
            rc, _, stderr = self.runner.run_sudo(f"cp {temp_file} {hosts_file}")
            self.runner.run(f"rm -f {temp_file}", shell=True)
            
            if rc != 0:
                self.logger.failure(f"hosts dosyası güncellenemedi: {stderr}")
                return False
            
            backup.save_manifest()
            
            self.logger.success(f"FQDN düzeltildi: {hostname} → {fqdn}")
            self.logger.info(f"Eklenen satır: {new_entry}")
            self.logger.warning("Değişikliğin tam etkili olması için yeniden giriş yapın")
            
            return True
            
        except Exception as e:
            self.logger.failure(f"FQDN düzeltme hatası: {str(e)}")
            return False
    
    def fix_ulimits(self) -> bool:
        """Ulimits uyarısı - zaten limits_config.py tarafından yapılandırılıyor"""
        ulimits_data = self.results.get('ulimits', {})
        
        if ulimits_data.get('status') == 'fail':
            self.logger.warning("\nUlimits yapılandırması yapıldı ancak şu anki session'da görünmüyor.")
            self.logger.warning("Değişikliklerin geçerli olması için:")
            self.logger.info("  1. SSH oturumunu kapatıp tekrar açın (logout/login)")
            self.logger.info("  2. Veya sunucuyu yeniden başlatın (reboot)")
            return False
        
        return True
    
    def run_all_checks(self) -> Tuple[bool, Dict]:
        """Tüm sistem kontrollerini çalıştır"""
        self.logger.section("Sistem Gereksinimleri Kontrolü")
        
        checks = [
            self.check_cpu(),
            self.check_memory(),
            self.check_disk(),
            self.check_swap(),
            self.check_ulimits(),
            self.check_hostname()
        ]
        
        all_passed = all(check[0] for check in checks)
        
        if all_passed:
            self.logger.success("\nTüm sistem kontrolleri başarılı!")
        else:
            self.logger.failure("\nBazı sistem kontrolleri başarısız!")
        
        return all_passed, self.results
    
    def fix_issues(self, fqdn: str = None) -> bool:
        """Tespit edilen sorunları otomatik düzelt
        
        Args:
            fqdn: Kullanıcıdan alınan FQDN (hostname için)
        """
        self.logger.section("Sorunlar Düzeltiliyor")
        
        fixed_count = 0
        total_issues = 0
        
        # Hostname/FQDN sorunu
        if self.results.get('hostname', {}).get('needs_fix'):
            total_issues += 1
            if self.fix_hostname_fqdn(fqdn=fqdn):
                fixed_count += 1
        
        # Ulimits uyarısı
        if self.results.get('ulimits', {}).get('status') == 'fail':
            total_issues += 1
            self.fix_ulimits()  # Bu sadece uyarı verir
        
        if total_issues > 0:
            self.logger.info(f"\n{fixed_count}/{total_issues} sorun düzeltildi")
            return fixed_count > 0
        
        return True


if __name__ == '__main__':
    # Test
    checker = SystemCheck()
    passed, results = checker.run_all_checks()
    print(f"\nAll checks passed: {passed}")
