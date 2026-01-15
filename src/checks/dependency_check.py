"""
Dependency Check Module
Linux paket bağımlılıklarını kontrol eder ve yükler
"""

from typing import Dict, List, Tuple
from pathlib import Path
import yaml

from ..utils.logger import get_logger
from ..utils.command_runner import get_command_runner
from ..utils.distro_detector import DistroDetector


class DependencyCheck:
    """Paket bağımlılıklarını kontrol eder ve yükler"""
    
    def __init__(self, deployment_role: str = 'Combined', db_type: str = 'PostgreSQL'):
        self.logger = get_logger()
        self.runner = get_command_runner()
        self.distro = DistroDetector()
        self.deployment_role = deployment_role
        self.db_type = db_type
        self.config = self._load_config()
        self.results: Dict = {}
    
    def _load_config(self) -> Dict:
        """Dependency config'ini yükle"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'dependencies.yaml'
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Could not load dependencies config: {str(e)}")
            return {}
    
    def _get_required_packages(self) -> List[str]:
        """Gerekli paketlerin listesini döndür"""
        distro_name = self.distro.get_name()
        
        if distro_name not in self.config.get('distributions', {}):
            self.logger.warning(f"No package configuration for: {distro_name}")
            return []
        
        distro_config = self.config['distributions'][distro_name]
        packages = distro_config.get('base_packages', []).copy()
        
        # Database driver'ları ekle
        db_drivers = distro_config.get('database_drivers', {}).get(self.db_type, [])
        packages.extend(db_drivers)
        
        return packages
    
    def check_package_installed(self, package: str) -> bool:
        """Paketin kurulu olup olmadığını kontrol et"""
        pkg_manager = self.distro.get_package_manager()
        
        if pkg_manager in ['yum', 'dnf']:
            rc, _, _ = self.runner.run(f"rpm -q {package}")
            return rc == 0
        
        elif pkg_manager == 'apt':
            rc, output, _ = self.runner.run(f"dpkg -l {package}")
            return rc == 0 and 'ii' in output
        
        elif pkg_manager == 'zypper':
            rc, _, _ = self.runner.run(f"rpm -q {package}")
            return rc == 0
        
        return False
    
    def install_package(self, package: str) -> Tuple[bool, str]:
        """
        Paketi yükle
        
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        pkg_manager = self.distro.get_package_manager()
        
        self.logger.info(f"Kuruluyor: {package}")
        
        if pkg_manager in ['yum', 'dnf']:
            rc, stdout, stderr = self.runner.run_sudo(f"{pkg_manager} install -y {package}", timeout=600)
        
        elif pkg_manager == 'apt':
            # apt update önce
            self.runner.run_sudo("apt-get update", timeout=300)
            rc, stdout, stderr = self.runner.run_sudo(f"apt-get install -y {package}", timeout=600)
        
        elif pkg_manager == 'zypper':
            rc, stdout, stderr = self.runner.run_sudo(f"zypper install -y {package}", timeout=600)
        
        else:
            return False, f"Unsupported package manager: {pkg_manager}"
        
        if rc == 0:
            self.logger.success(f"✓ {package} kuruldu")
            return True, ""
        else:
            error = stderr if stderr else stdout
            self.logger.error(f"✗ {package} kurulamadı: {error}")
            return False, error
    
    def check_and_install_packages(self) -> Tuple[bool, Dict]:
        """Tüm paketleri kontrol et ve gerekirse yükle"""
        self.logger.subsection("Paket Bağımlılıkları")
        
        required_packages = self._get_required_packages()
        
        if not required_packages:
            self.logger.warning("Paket listesi bulunamadı")
            return True, {}
        
        self.logger.info(f"Kontrol edilecek paket sayısı: {len(required_packages)}")
        
        installed = []
        missing = []
        failed = []
        
        # Kontrol et
        for package in required_packages:
            if self.check_package_installed(package):
                installed.append(package)
            else:
                missing.append(package)
        
        self.logger.info(f"Kurulu: {len(installed)}, Eksik: {len(missing)}")
        
        # Eksik paketleri yükle
        if missing:
            self.logger.info(f"\n{len(missing)} paket yüklenecek...")
            
            for package in missing:
                success, error = self.install_package(package)
                if not success:
                    failed.append({'package': package, 'error': error})
        
        result = {
            'total_required': len(required_packages),
            'already_installed': len(installed),
            'newly_installed': len(missing) - len(failed),
            'failed': failed,
            'status': 'pass' if not failed else 'fail'
        }
        
        self.results['packages'] = result
        
        if not failed:
            self.logger.success(f"\nTüm paketler kurulu ({len(required_packages)} paket)")
        else:
            self.logger.failure(f"\n{len(failed)} paket kurulamadı!")
        
        return not failed, result
    
    def check_java(self) -> Tuple[bool, Dict]:
        """Java kontrolü"""
        self.logger.subsection("Java Kontrolü")
        
        # Java var mı? (alternatif yolları kontrol et)
        java_found = False
        for java_cmd in ['java', '/usr/bin/java', '/usr/lib/jvm/jre-11-openjdk/bin/java']:
            rc, _, _ = self.runner.run(f"command -v {java_cmd} || which {java_cmd} || test -x {java_cmd}", shell=True)
            if rc == 0:
                java_found = True
                break
        
        if not java_found:
            self.logger.failure("Java bulunamadı")
            return False, {'installed': False, 'status': 'fail'}
        
        # Version
        rc, output, _ = self.runner.run("java -version", shell=True)
        
        # java -version stderr'e yazar
        rc2, output2, stderr2 = self.runner.run("java -version 2>&1", shell=True)
        version_output = output2 if output2 else stderr2
        
        # Version parse
        java_version = "unknown"
        if version_output:
            lines = version_output.split('\n')
            if lines:
                # "openjdk version "11.0.12" 2021-07-20"
                first_line = lines[0]
                if 'version' in first_line:
                    parts = first_line.split('"')
                    if len(parts) >= 2:
                        java_version = parts[1]
        
        # JAVA_HOME
        rc, java_home, _ = self.runner.run("echo $JAVA_HOME", shell=True)
        
        result = {
            'installed': True,
            'version': java_version,
            'java_home': java_home if java_home else 'Not set',
            'status': 'pass'
        }
        
        self.logger.success(f"Java kurulu: {java_version}")
        if java_home:
            self.logger.info(f"JAVA_HOME: {java_home}")
        else:
            self.logger.warning("JAVA_HOME ayarlanmamış")
        
        self.results['java'] = result
        return True, result
    
    def check_python(self) -> Tuple[bool, Dict]:
        """Python kontrolü (bu script zaten Python'la çalışıyor ama yine de)"""
        self.logger.subsection("Python Kontrolü")
        
        rc, output, _ = self.runner.run("python3 --version")
        
        result = {
            'installed': rc == 0,
            'version': output,
            'status': 'pass' if rc == 0 else 'fail'
        }
        
        if rc == 0:
            self.logger.success(f"Python3 kurulu: {output}")
        else:
            self.logger.failure("Python3 bulunamadı")
        
        self.results['python'] = result
        return rc == 0, result
    
    def install_sql_server_driver(self) -> Tuple[bool, Dict]:
        """SQL Server ODBC driver'ı kur (özel kurulum gerekli)"""
        self.logger.subsection("SQL Server ODBC Driver")
        
        if self.db_type != 'SQL Server':
            return True, {'status': 'skip'}
        
        # Driver zaten kurulu mu?
        rc, output, _ = self.runner.run("odbcinst -q -d -n 'ODBC Driver 17 for SQL Server'", shell=True)
        if rc == 0:
            self.logger.success("SQL Server ODBC Driver 17 kurulu")
            return True, {'installed': True, 'status': 'pass'}
        
        self.logger.info("SQL Server ODBC Driver 17 kuruluyor...")
        
        if self.distro.is_rhel_based():
            # Microsoft repo ekle
            commands = [
                "curl https://packages.microsoft.com/config/rhel/8/prod.repo | sudo tee /etc/yum.repos.d/mssql-release.repo",
                "ACCEPT_EULA=Y sudo yum install -y msodbcsql17",
                "ACCEPT_EULA=Y sudo yum install -y mssql-tools"
            ]
            
            for cmd in commands:
                rc, _, _ = self.runner.run(cmd, shell=True, timeout=300)
                if rc != 0:
                    self.logger.failure("SQL Server ODBC Driver kurulamadı")
                    return False, {'installed': False, 'status': 'fail'}
        
        elif self.distro.is_debian_based():
            # Microsoft repo ekle
            commands = [
                "curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -",
                "curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list",
                "sudo apt-get update",
                "ACCEPT_EULA=Y sudo apt-get install -y msodbcsql17",
                "ACCEPT_EULA=Y sudo apt-get install -y mssql-tools"
            ]
            
            for cmd in commands:
                rc, _, _ = self.runner.run(cmd, shell=True, timeout=300)
                if rc != 0:
                    self.logger.failure("SQL Server ODBC Driver kurulamadı")
                    return False, {'installed': False, 'status': 'fail'}
        
        self.logger.success("SQL Server ODBC Driver 17 kuruldu")
        return True, {'installed': True, 'status': 'pass'}
    
    def run_all_checks(self) -> Tuple[bool, Dict]:
        """Tüm dependency kontrollerini çalıştır"""
        self.logger.section("Dependency Kontrolü")
        
        self.logger.info(f"Linux: {self.distro.get_friendly_name()}")
        self.logger.info(f"Paket Yöneticisi: {self.distro.get_package_manager()}")
        self.logger.info(f"Deployment: {self.deployment_role}")
        self.logger.info(f"Database: {self.db_type}\n")
        
        checks = [
            self.check_python(),
            self.check_java(),
            self.check_and_install_packages()
        ]
        
        # SQL Server için özel driver
        if self.db_type == 'SQL Server':
            checks.append(self.install_sql_server_driver())
        
        all_passed = all(check[0] for check in checks)
        
        if all_passed:
            self.logger.success("\nTüm bağımlılıklar hazır!")
        else:
            self.logger.failure("\nBazı bağımlılıklar kurulamadı!")
        
        return all_passed, self.results


if __name__ == '__main__':
    # Test
    checker = DependencyCheck(deployment_role='Combined', db_type='PostgreSQL')
    passed, results = checker.run_all_checks()
    print(f"\nAll checks passed: {passed}")
