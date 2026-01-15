"""
Main Entry Point
mstr-helper komutunun ana giriş noktası
"""

import sys
import argparse
from pathlib import Path

from .utils.logger import get_logger
from .utils.distro_detector import DistroDetector
from .cli.interface import CLIInterface
from .install.pre_install import PreInstall
from .install.post_install import PostInstall
from .install.rollback import Rollback
from .utils.report_generator import ReportGenerator


def check_root():
    """Root kontrolü"""
    import os
    if os.geteuid() != 0:
        print("Bu program root olarak çalıştırılmalıdır!")
        print("Lütfen: sudo mstr-helper <komut>")
        sys.exit(1)


def command_prepare():
    """Prepare komutu"""
    check_root()
    
    logger = get_logger()
    cli = CLIInterface()
    
    # Banner
    cli.print_banner()
    
    # Distro kontrolü
    distro = DistroDetector()
    if not distro.is_supported():
        logger.error(f"Desteklenmeyen Linux dağıtımı: {distro.get_friendly_name()}")
        logger.error("Desteklenen: RHEL, CentOS, Oracle Linux, Ubuntu")
        sys.exit(1)
    
    logger.info(f"Linux Dağıtımı: {distro.get_friendly_name()}")
    logger.info(f"Paket Yöneticisi: {distro.get_package_manager()}\n")
    
    # Deployment role seçimi
    deployment_role = cli.select_deployment_role()
    
    # Database bilgileri
    db_config = cli.get_database_config()
    
    # Onay
    if not cli.confirm_configuration(deployment_role, db_config):
        logger.info("İşlem iptal edildi.")
        sys.exit(0)
    
    # Pre-installation
    pre_install = PreInstall(deployment_role, db_config)
    success, results = pre_install.run()
    
    # Rapor oluştur
    generator = ReportGenerator()
    
    # Hostname ekle
    from .utils.command_runner import get_command_runner
    runner = get_command_runner()
    rc, hostname, _ = runner.run("hostname")
    results['hostname'] = hostname.strip()
    
    json_report = generator.generate_json_report(results)
    html_report = generator.generate_html_report(results)
    
    logger.info(f"\nRaporlar:")
    logger.info(f"  JSON: {json_report}")
    logger.info(f"  HTML: {html_report}")
    
    # Completion mesajı
    cli.show_completion(success)
    
    sys.exit(0 if success else 1)


def command_verify():
    """Verify komutu"""
    check_root()
    
    logger = get_logger()
    cli = CLIInterface()
    
    cli.print_banner()
    
    # Post-installation verification
    post_install = PostInstall()
    success, results = post_install.verify()
    
    # Completion mesajı
    cli.show_verification_complete(success)
    
    sys.exit(0 if success else 1)


def command_rollback():
    """Rollback komutu"""
    check_root()
    
    logger = get_logger()
    cli = CLIInterface()
    
    cli.print_banner()
    
    # Onay
    if not cli.confirm("Yapılan tüm değişiklikler geri alınacak. Devam edilsin mi?", False):
        logger.info("İşlem iptal edildi.")
        sys.exit(0)
    
    # Rollback
    rollback = Rollback()
    success, results = rollback.rollback()
    
    # Completion mesajı
    cli.show_rollback_complete(success)
    
    sys.exit(0 if success else 1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MicroStrategy Linux Installation Helper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Komutlar:
  prepare   - Sunucuyu MicroStrategy kurulumu için hazırla
  verify    - Kurulum sonrası servis kontrolü
  rollback  - Yapılan değişiklikleri geri al

Örnekler:
  sudo mstr-helper prepare
  sudo mstr-helper verify
  sudo mstr-helper rollback
"""
    )
    
    parser.add_argument(
        'command',
        choices=['prepare', 'verify', 'rollback'],
        help='Çalıştırılacak komut'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='MicroStrategy Helper 1.0.0'
    )
    
    # Parse arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Route to command
    if args.command == 'prepare':
        command_prepare()
    elif args.command == 'verify':
        command_verify()
    elif args.command == 'rollback':
        command_rollback()


if __name__ == '__main__':
    main()
