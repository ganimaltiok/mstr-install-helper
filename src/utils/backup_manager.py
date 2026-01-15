"""
Backup Manager
Yapılandırma dosyalarını yedekler ve geri yükler
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
from .logger import get_logger


class BackupManager:
    """Sistem yapılandırma dosyalarını yedekler"""
    
    BACKUP_DIR = Path('/var/lib/mstr-helper/backups')
    BACKUP_MANIFEST = 'backup_manifest.json'
    
    def __init__(self):
        self.logger = get_logger()
        self.backup_dir = self.BACKUP_DIR
        self._ensure_backup_dir()
        self.current_backup_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.manifest: Dict = {
            'backup_id': self.current_backup_id,
            'timestamp': datetime.now().isoformat(),
            'files': []
        }
    
    def _ensure_backup_dir(self):
        """Backup dizinini oluştur"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Backup directory: {self.backup_dir}")
        except PermissionError:
            # Root erişimi yoksa /tmp kullan
            self.backup_dir = Path('/tmp/mstr-helper/backups')
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.warning(f"Using temporary backup directory: {self.backup_dir}")
    
    def backup_file(self, file_path: str, description: str = "") -> bool:
        """
        Dosyayı yedekle
        
        Args:
            file_path: Yedeklenecek dosyanın tam yolu
            description: Dosya açıklaması
        
        Returns:
            bool: Başarılı ise True
        """
        source = Path(file_path)
        
        if not source.exists():
            self.logger.warning(f"File not found for backup: {file_path}")
            return False
        
        try:
            # Backup dosya adı: timestamp_originalname
            backup_name = f"{self.current_backup_id}_{source.name}"
            dest = self.backup_dir / backup_name
            
            # Dosyayı kopyala
            shutil.copy2(source, dest)
            
            # Manifest'e ekle
            self.manifest['files'].append({
                'original_path': str(source),
                'backup_path': str(dest),
                'description': description,
                'backup_time': datetime.now().isoformat()
            })
            
            self.logger.info(f"Backed up: {file_path} -> {backup_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup {file_path}: {str(e)}")
            return False
    
    def backup_files(self, file_paths: List[str]) -> int:
        """
        Birden fazla dosyayı yedekle
        
        Args:
            file_paths: Yedeklenecek dosyaların listesi
        
        Returns:
            int: Başarıyla yedeklenen dosya sayısı
        """
        success_count = 0
        for file_path in file_paths:
            if self.backup_file(file_path):
                success_count += 1
        return success_count
    
    def save_manifest(self) -> bool:
        """Backup manifest'i kaydet"""
        try:
            manifest_path = self.backup_dir / f"{self.current_backup_id}_{self.BACKUP_MANIFEST}"
            with open(manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)
            self.logger.info(f"Backup manifest saved: {manifest_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save manifest: {str(e)}")
            return False
    
    def restore_file(self, original_path: str, backup_id: Optional[str] = None) -> bool:
        """
        Dosyayı geri yükle
        
        Args:
            original_path: Geri yüklenecek dosyanın orijinal yolu
            backup_id: Hangi backup'tan geri yüklenecek (None ise en son)
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            if backup_id is None:
                backup_id = self.current_backup_id
            
            # Manifest'i bul
            manifest_path = self.backup_dir / f"{backup_id}_{self.BACKUP_MANIFEST}"
            if not manifest_path.exists():
                self.logger.error(f"Backup manifest not found: {manifest_path}")
                return False
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Dosyayı manifest'te bul
            file_entry = None
            for entry in manifest['files']:
                if entry['original_path'] == original_path:
                    file_entry = entry
                    break
            
            if file_entry is None:
                self.logger.error(f"File not found in backup: {original_path}")
                return False
            
            backup_path = Path(file_entry['backup_path'])
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Dosyayı geri yükle
            shutil.copy2(backup_path, original_path)
            self.logger.info(f"Restored: {backup_path} -> {original_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore {original_path}: {str(e)}")
            return False
    
    def restore_all(self, backup_id: Optional[str] = None) -> int:
        """
        Tüm dosyaları geri yükle
        
        Args:
            backup_id: Hangi backup'tan geri yüklenecek (None ise en son)
        
        Returns:
            int: Başarıyla geri yüklenen dosya sayısı
        """
        try:
            if backup_id is None:
                backup_id = self.current_backup_id
            
            manifest_path = self.backup_dir / f"{backup_id}_{self.BACKUP_MANIFEST}"
            if not manifest_path.exists():
                self.logger.error(f"Backup manifest not found: {manifest_path}")
                return 0
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            success_count = 0
            for entry in manifest['files']:
                if self.restore_file(entry['original_path'], backup_id):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            self.logger.error(f"Failed to restore all files: {str(e)}")
            return 0
    
    def list_backups(self) -> List[Dict]:
        """Mevcut backup'ları listele"""
        backups = []
        
        for manifest_file in self.backup_dir.glob(f"*_{self.BACKUP_MANIFEST}"):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    backups.append({
                        'backup_id': manifest['backup_id'],
                        'timestamp': manifest['timestamp'],
                        'file_count': len(manifest['files'])
                    })
            except Exception as e:
                self.logger.warning(f"Failed to read manifest {manifest_file}: {str(e)}")
        
        # Zamana göre sırala (en yeni önce)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def get_latest_backup_id(self) -> Optional[str]:
        """En son backup ID'sini döndür"""
        backups = self.list_backups()
        return backups[0]['backup_id'] if backups else None


if __name__ == '__main__':
    # Test
    manager = BackupManager()
    
    print("Testing BackupManager...")
    print(f"Backup directory: {manager.backup_dir}")
    print(f"Current backup ID: {manager.current_backup_id}")
    
    # Test backup listesi
    backups = manager.list_backups()
    print(f"\nExisting backups: {len(backups)}")
    for backup in backups:
        print(f"  - {backup['backup_id']}: {backup['file_count']} files")
