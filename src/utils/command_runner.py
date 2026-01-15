"""
Command Runner
Shell komutlarını güvenli şekilde çalıştırır ve sonuçlarını döndürür
"""

import subprocess
import shlex
from typing import Tuple, Optional, List
from .logger import get_logger


class CommandRunner:
    """Shell komutlarını çalıştırır"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def run(self, 
            command: str, 
            shell: bool = False,
            check: bool = False,
            capture_output: bool = True,
            timeout: Optional[int] = 300) -> Tuple[int, str, str]:
        """
        Komutu çalıştır ve sonucu döndür
        
        Args:
            command: Çalıştırılacak komut
            shell: Shell'de çalıştır (güvenlik riski, dikkatli kullan)
            check: Hata durumunda exception fırlat
            capture_output: Çıktıyı yakala
            timeout: Timeout (saniye)
        
        Returns:
            Tuple[return_code, stdout, stderr]
        """
        self.logger.debug(f"Executing command: {command}")
        
        try:
            if shell:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    check=check
                )
            else:
                # Güvenli: shell injection'a karşı korumalı
                cmd_list = shlex.split(command)
                result = subprocess.run(
                    cmd_list,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    check=check
                )
            
            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""
            
            if result.returncode == 0:
                self.logger.debug(f"Command succeeded: {command}")
            else:
                self.logger.warning(f"Command failed (rc={result.returncode}): {command}")
                if stderr:
                    self.logger.debug(f"stderr: {stderr}")
            
            return result.returncode, stdout, stderr
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout after {timeout}s: {command}")
            return -1, "", f"Command timeout after {timeout} seconds"
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}")
            return e.returncode, e.stdout or "", e.stderr or ""
        
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return -1, "", str(e)
    
    def run_sudo(self, command: str, **kwargs) -> Tuple[int, str, str]:
        """Komutu sudo ile çalıştır"""
        if not command.startswith('sudo '):
            command = f"sudo {command}"
        return self.run(command, **kwargs)
    
    def is_command_available(self, command: str) -> bool:
        """Komutun sistemde var olup olmadığını kontrol et"""
        rc, stdout, _ = self.run(f"command -v {command}", shell=True)
        return rc == 0
    
    def get_command_path(self, command: str) -> Optional[str]:
        """Komutun tam yolunu döndür"""
        rc, stdout, _ = self.run(f"which {command}")
        return stdout if rc == 0 else None
    
    def run_multiple(self, commands: List[str], stop_on_error: bool = True) -> List[Tuple[int, str, str]]:
        """
        Birden fazla komutu sırayla çalıştır
        
        Args:
            commands: Komut listesi
            stop_on_error: İlk hatada dur
        
        Returns:
            Her komut için (rc, stdout, stderr) listesi
        """
        results = []
        
        for cmd in commands:
            result = self.run(cmd)
            results.append(result)
            
            if stop_on_error and result[0] != 0:
                self.logger.warning(f"Stopping execution due to error in: {cmd}")
                break
        
        return results


# Global instance
_cmd_runner: Optional[CommandRunner] = None


def get_command_runner() -> CommandRunner:
    """Global CommandRunner instance'ı döndür"""
    global _cmd_runner
    if _cmd_runner is None:
        _cmd_runner = CommandRunner()
    return _cmd_runner


if __name__ == '__main__':
    # Test
    runner = get_command_runner()
    
    print("Testing CommandRunner...")
    
    # Test 1: Basit komut
    rc, out, err = runner.run("echo 'Hello World'")
    print(f"Echo test: rc={rc}, output={out}")
    
    # Test 2: Komut varlığı
    print(f"Python3 available: {runner.is_command_available('python3')}")
    print(f"Python3 path: {runner.get_command_path('python3')}")
    
    # Test 3: Başarısız komut
    rc, out, err = runner.run("false")
    print(f"False command: rc={rc}")
    
    # Test 4: Çoklu komut
    results = runner.run_multiple(["echo 'cmd1'", "echo 'cmd2'", "echo 'cmd3'"])
    print(f"Multiple commands executed: {len(results)} results")
