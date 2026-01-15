"""
Database Check Module
Veritabanı bağlantısı ve yetki kontrollerini yapar
"""

import socket
from typing import Dict, Tuple, Optional

from ..utils.logger import get_logger


class DatabaseCheck:
    """Veritabanı bağlantısını test eder"""
    
    SUPPORTED_DATABASES = {
        'PostgreSQL': {'default_port': 5432, 'driver': 'psycopg2'},
        'Oracle': {'default_port': 1521, 'driver': 'cx_Oracle'},
        'SQL Server': {'default_port': 1433, 'driver': 'pyodbc'},
        'MySQL': {'default_port': 3306, 'driver': 'pymysql'}
    }
    
    def __init__(self, db_type: str, host: str, port: int, database: str, 
                 username: str, password: str):
        self.logger = get_logger()
        self.db_type = db_type
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.results: Dict = {}
    
    def check_port_connectivity(self) -> Tuple[bool, Dict]:
        """Database port'una bağlanabilir miyiz?"""
        self.logger.subsection(f"Database Port Kontrolü ({self.host}:{self.port})")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            connected = (result == 0)
            
            if connected:
                self.logger.success(f"Database port erişilebilir: {self.host}:{self.port}")
            else:
                self.logger.failure(f"Database port erişilemiyor: {self.host}:{self.port}")
            
            result_dict = {
                'host': self.host,
                'port': self.port,
                'reachable': connected,
                'status': 'pass' if connected else 'fail'
            }
            
            self.results['port_connectivity'] = result_dict
            return connected, result_dict
            
        except socket.gaierror:
            self.logger.failure(f"Host çözümlenemedi: {self.host}")
            result_dict = {
                'host': self.host,
                'port': self.port,
                'reachable': False,
                'error': 'DNS resolution failed',
                'status': 'fail'
            }
            self.results['port_connectivity'] = result_dict
            return False, result_dict
        
        except Exception as e:
            self.logger.failure(f"Port kontrol hatası: {str(e)}")
            result_dict = {
                'host': self.host,
                'port': self.port,
                'reachable': False,
                'error': str(e),
                'status': 'fail'
            }
            self.results['port_connectivity'] = result_dict
            return False, result_dict
    
    def test_connection_postgresql(self) -> Tuple[bool, Dict]:
        """PostgreSQL bağlantısını test et"""
        try:
            import psycopg2
            
            self.logger.info(f"PostgreSQL'e bağlanılıyor: {self.username}@{self.host}:{self.port}/{self.database}")
            
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )
            
            # Version bilgisi
            cursor = self.connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            
            self.logger.success("PostgreSQL bağlantısı başarılı")
            self.logger.info(f"Version: {version.split(',')[0]}")
            
            return True, {
                'connected': True,
                'version': version,
                'status': 'pass'
            }
            
        except ImportError:
            self.logger.failure("psycopg2 modülü bulunamadı (pip install psycopg2-binary)")
            return False, {'connected': False, 'error': 'psycopg2 not installed', 'status': 'fail'}
        
        except Exception as e:
            self.logger.failure(f"PostgreSQL bağlantı hatası: {str(e)}")
            return False, {'connected': False, 'error': str(e), 'status': 'fail'}
    
    def test_connection_mysql(self) -> Tuple[bool, Dict]:
        """MySQL bağlantısını test et"""
        try:
            import pymysql
            
            self.logger.info(f"MySQL'e bağlanılıyor: {self.username}@{self.host}:{self.port}/{self.database}")
            
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )
            
            # Version bilgisi
            cursor = self.connection.cursor()
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()[0]
            cursor.close()
            
            self.logger.success("MySQL bağlantısı başarılı")
            self.logger.info(f"Version: {version}")
            
            return True, {
                'connected': True,
                'version': version,
                'status': 'pass'
            }
            
        except ImportError:
            self.logger.failure("pymysql modülü bulunamadı (pip install pymysql)")
            return False, {'connected': False, 'error': 'pymysql not installed', 'status': 'fail'}
        
        except Exception as e:
            self.logger.failure(f"MySQL bağlantı hatası: {str(e)}")
            return False, {'connected': False, 'error': str(e), 'status': 'fail'}
    
    def test_connection_sqlserver(self) -> Tuple[bool, Dict]:
        """SQL Server bağlantısını test et"""
        try:
            import pyodbc
            
            self.logger.info(f"SQL Server'a bağlanılıyor: {self.username}@{self.host}:{self.port}/{self.database}")
            
            # ODBC connection string
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"Connection Timeout=10;"
            )
            
            self.connection = pyodbc.connect(conn_str)
            
            # Version bilgisi
            cursor = self.connection.cursor()
            cursor.execute("SELECT @@VERSION;")
            version = cursor.fetchone()[0]
            cursor.close()
            
            self.logger.success("SQL Server bağlantısı başarılı")
            self.logger.info(f"Version: {version.split('\\n')[0]}")
            
            return True, {
                'connected': True,
                'version': version.split('\n')[0],
                'status': 'pass'
            }
            
        except ImportError:
            self.logger.failure("pyodbc modülü bulunamadı (pip install pyodbc)")
            return False, {'connected': False, 'error': 'pyodbc not installed', 'status': 'fail'}
        
        except Exception as e:
            self.logger.failure(f"SQL Server bağlantı hatası: {str(e)}")
            return False, {'connected': False, 'error': str(e), 'status': 'fail'}
    
    def test_connection_oracle(self) -> Tuple[bool, Dict]:
        """Oracle bağlantısını test et"""
        try:
            import cx_Oracle
            
            self.logger.info(f"Oracle'a bağlanılıyor: {self.username}@{self.host}:{self.port}/{self.database}")
            
            dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.database)
            self.connection = cx_Oracle.connect(
                user=self.username,
                password=self.password,
                dsn=dsn
            )
            
            # Version bilgisi
            version = self.connection.version
            
            self.logger.success("Oracle bağlantısı başarılı")
            self.logger.info(f"Version: {version}")
            
            return True, {
                'connected': True,
                'version': version,
                'status': 'pass'
            }
            
        except ImportError:
            self.logger.failure("cx_Oracle modülü bulunamadı (pip install cx_Oracle)")
            return False, {'connected': False, 'error': 'cx_Oracle not installed', 'status': 'fail'}
        
        except Exception as e:
            self.logger.failure(f"Oracle bağlantı hatası: {str(e)}")
            return False, {'connected': False, 'error': str(e), 'status': 'fail'}
    
    def test_connection(self) -> Tuple[bool, Dict]:
        """Database bağlantısını test et"""
        self.logger.subsection(f"{self.db_type} Bağlantı Testi")
        
        if self.db_type == 'PostgreSQL':
            success, result = self.test_connection_postgresql()
        elif self.db_type == 'MySQL':
            success, result = self.test_connection_mysql()
        elif self.db_type == 'SQL Server':
            success, result = self.test_connection_sqlserver()
        elif self.db_type == 'Oracle':
            success, result = self.test_connection_oracle()
        else:
            self.logger.failure(f"Desteklenmeyen veritabanı tipi: {self.db_type}")
            return False, {'connected': False, 'error': 'Unsupported database type', 'status': 'fail'}
        
        self.results['connection'] = result
        return success, result
    
    def test_privileges(self) -> Tuple[bool, Dict]:
        """Database yetkilerini test et"""
        if not self.connection:
            self.logger.warning("Bağlantı yok, yetki kontrolü atlanıyor")
            return False, {'status': 'skip'}
        
        self.logger.subsection("Database Yetki Kontrolü")
        
        try:
            cursor = self.connection.cursor()
            
            # Test tablosu oluştur
            test_table = "mstr_helper_test"
            
            privileges = {
                'create': False,
                'insert': False,
                'select': False,
                'drop': False
            }
            
            # CREATE
            try:
                cursor.execute(f"CREATE TABLE {test_table} (id INT, name VARCHAR(50))")
                privileges['create'] = True
                self.logger.success("CREATE yetkisi: OK")
            except Exception as e:
                self.logger.failure(f"CREATE yetkisi: FAILED - {str(e)}")
            
            # INSERT
            if privileges['create']:
                try:
                    cursor.execute(f"INSERT INTO {test_table} (id, name) VALUES (1, 'test')")
                    privileges['insert'] = True
                    self.logger.success("INSERT yetkisi: OK")
                except Exception as e:
                    self.logger.failure(f"INSERT yetkisi: FAILED - {str(e)}")
            
            # SELECT
            if privileges['insert']:
                try:
                    cursor.execute(f"SELECT * FROM {test_table}")
                    privileges['select'] = True
                    self.logger.success("SELECT yetkisi: OK")
                except Exception as e:
                    self.logger.failure(f"SELECT yetkisi: FAILED - {str(e)}")
            
            # DROP
            if privileges['create']:
                try:
                    cursor.execute(f"DROP TABLE {test_table}")
                    privileges['drop'] = True
                    self.logger.success("DROP yetkisi: OK")
                except Exception as e:
                    self.logger.failure(f"DROP yetkisi: FAILED - {str(e)}")
            
            cursor.close()
            
            all_ok = all(privileges.values())
            
            result = {
                'privileges': privileges,
                'all_granted': all_ok,
                'status': 'pass' if all_ok else 'fail'
            }
            
            self.results['privileges'] = result
            return all_ok, result
            
        except Exception as e:
            self.logger.failure(f"Yetki kontrolü hatası: {str(e)}")
            return False, {'error': str(e), 'status': 'fail'}
    
    def close(self):
        """Bağlantıyı kapat"""
        if self.connection:
            try:
                self.connection.close()
                self.logger.debug("Database bağlantısı kapatıldı")
            except Exception:
                pass
    
    def run_all_checks(self) -> Tuple[bool, Dict]:
        """Tüm database kontrollerini çalıştır"""
        self.logger.section(f"Database Kontrolü ({self.db_type})")
        
        # Port kontrolü
        port_ok, _ = self.check_port_connectivity()
        if not port_ok:
            return False, self.results
        
        # Bağlantı testi
        conn_ok, _ = self.test_connection()
        if not conn_ok:
            return False, self.results
        
        # Yetki kontrolü
        priv_ok, _ = self.test_privileges()
        
        # Bağlantıyı kapat
        self.close()
        
        all_passed = port_ok and conn_ok and priv_ok
        
        if all_passed:
            self.logger.success("\nTüm database kontrolleri başarılı!")
        else:
            self.logger.failure("\nBazı database kontrolleri başarısız!")
        
        return all_passed, self.results


if __name__ == '__main__':
    # Test (gerçek bilgilerle test edilmeli)
    print("DatabaseCheck module - use with real database credentials")
