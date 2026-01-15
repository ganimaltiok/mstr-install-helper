"""
Logging Utility
Konsol ve dosya logging için yapılandırılmış logger
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from colorama import Fore, Style, init

# Colorama başlat
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Renkli konsol çıktısı için formatter"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        # Level için renk ekle
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        
        return super().format(record)


class Logger:
    """Centralized logging utility"""
    
    def __init__(self, name: str = 'mstr-helper', log_dir: str = '/var/log/mstr-helper'):
        self.name = name
        self.log_dir = Path(log_dir)
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Logger'ı yapılandır"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        
        # Önceki handler'ları temizle
        if logger.handlers:
            logger.handlers.clear()
        
        # Log dizini oluştur
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Root erişimi yoksa /tmp kullan
            self.log_dir = Path('/tmp/mstr-helper')
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler - detaylı loglar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f"mstr-helper_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - sadece önemli mesajlar
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Handler'ları ekle
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, message: str):
        """Debug seviyesi log"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Info seviyesi log"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Warning seviyesi log"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Error seviyesi log"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Critical seviyesi log"""
        self.logger.critical(message)
    
    def section(self, title: str):
        """Bölüm başlığı"""
        separator = "=" * 60
        self.logger.info(f"\n{separator}")
        self.logger.info(f"  {title}")
        self.logger.info(separator)
    
    def subsection(self, title: str):
        """Alt bölüm başlığı"""
        self.logger.info(f"\n--- {title} ---")
    
    def success(self, message: str):
        """Başarı mesajı (yeşil)"""
        self.logger.info(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
    
    def failure(self, message: str):
        """Hata mesajı (kırmızı)"""
        self.logger.error(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
    
    def get_log_file(self) -> str:
        """Aktif log dosyasının yolunu döndür"""
        handlers = [h for h in self.logger.handlers if isinstance(h, logging.FileHandler)]
        if handlers:
            return handlers[0].baseFilename
        return ""


# Global logger instance
_global_logger: Optional[Logger] = None


def get_logger(name: str = 'mstr-helper') -> Logger:
    """Global logger instance'ı döndür"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name)
    return _global_logger


if __name__ == '__main__':
    # Test
    logger = get_logger()
    logger.section("Testing Logger")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.success("This is a success message")
    logger.failure("This is a failure message")
    print(f"\nLog file: {logger.get_log_file()}")
