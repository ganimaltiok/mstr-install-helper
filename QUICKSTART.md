# MicroStrategy Installation Helper - Quick Start Guide

## Proje Yapısı

```
MSTR_Install_Helper/
├── install.sh              # Bootstrap kurulum scripti
├── requirements.txt        # Python bağımlılıkları
├── README.md              # Detaylı dokümantasyon
├── config/                # Konfigürasyon dosyaları
│   ├── dependencies.yaml
│   ├── port_requirements.yaml
│   └── deployment.yaml.template
└── src/                   # Ana kaynak kod
    ├── __init__.py
    ├── __main__.py
    ├── main.py           # Ana entry point
    ├── checks/           # Sistem kontrolleri
    │   ├── system_check.py
    │   ├── network_check.py
    │   ├── dependency_check.py
    │   └── database_check.py
    ├── config/           # Yapılandırma modülleri
    │   ├── xdisplay_config.py
    │   ├── firewall_config.py
    │   ├── selinux_config.py
    │   └── limits_config.py
    ├── install/          # Kurulum orkestrasyon
    │   ├── pre_install.py
    │   ├── post_install.py
    │   └── rollback.py
    ├── cli/              # CLI arayüzü
    │   └── interface.py
    └── utils/            # Yardımcı modüller
        ├── distro_detector.py
        ├── logger.py
        ├── command_runner.py
        ├── backup_manager.py
        └── report_generator.py
```

## Kurulum (Linux Sunucusunda)

### 1. Dosyaları Sunucuya Kopyalayın

```bash
# Lokal makinenizden Linux sunucusuna kopyalayın
scp -r MSTR_Install_Helper user@linux-server:/tmp/

# Veya
rsync -av MSTR_Install_Helper/ user@linux-server:/tmp/MSTR_Install_Helper/
```

### 2. Sunucuda Kurulumu Çalıştırın

```bash
# SSH ile sunucuya bağlanın
ssh user@linux-server

# Kurulum dizinine gidin
cd /tmp/MSTR_Install_Helper

# Bootstrap kurulumunu çalıştırın (root gerekli)
sudo bash install.sh
```

Bootstrap script şunları yapar:
- Python3 ve pip kontrolü/kurulumu
- Python bağımlılıklarını kurma
- `/opt/mstr-helper` dizinine uygulamayı kopyalama
- `/usr/local/bin/mstr-helper` komutunu oluşturma

## Kullanım

### Komut 1: Prepare (Hazırlık)

Sunucuyu MicroStrategy kurulumu için hazırlar:

```bash
sudo mstr-helper prepare
```

**Bu komut:**
1. ✅ Linux dağıtımını tespit eder
2. ✅ Deployment tipini sorar (Combined/Web-Only/IS-Only)
3. ✅ **MicroStrategy kullanıcısı oluşturulsun mu sorar (opsiyonel, best practice)**
4. ✅ Veritabanı bilgilerini sorar (PostgreSQL/Oracle/SQL Server/MySQL)
5. ✅ Distributed deployment için remote sunucu IP'si sorar
6. ✅ Sistem kontrollerini yapar (CPU, RAM, Disk, Swap, FQDN)
7. ✅ Network kontrollerini yapar (portlar, DNS, remote sunucu erişimi)
8. ✅ Database bağlantısını test eder
9. ✅ **Tespit edilen sorunları otomatik düzeltir (FQDN, ulimits)**
10. ✅ **Özel kullanıcı oluşturur (isterseniz) - sudo yetkili, home directory hazır**
11. ✅ Gerekli paketleri yükler (Java, ODBC, X11 libs, vs.)
12. ✅ Xvfb kurar ve yapılandırır
13. ✅ Firewall kurallarını ekler
14. ✅ SELinux'u permissive yapar
15. ✅ System limits ayarlar (user-specific veya global)
16. ✅ **Tüm cevapları kaydeder (sonraki çalıştırmalarda default olur)**
17. ✅ **Detaylı pass/fail özeti gösterir**
18. ✅ HTML ve JSON rapor oluşturur
19. ✅ Kurulum talimatlarını gösterir

**Örnek Akış (İlk Çalıştırma):**
```
=== Deployment Tipi Seçin ===
1. Combined - Intelligence Server + Web Server (aynı sunucu)
2. Web-Only - Sadece Web Server
3. IS-Only - Sadece Intelligence Server
Seçiminiz: 2

=== Distributed Deployment - Remote Server ===
Intelligence Server IP adresi: 192.168.1.10
Intelligence Server kurulu mu? (E/h): E
[INFO] Remote server portlarını kontrol ediyorum...

=== Veritabanı Tipi Seçin ===
1. PostgreSQL
2. Oracle
3. SQL Server
4. MySQL
Seçiminiz: 1

Database Host [localhost]: db-server.company.com
Database Port [5432]: 5432
Database Adı [metadata]: mstr_metadata
Kullanıcı Adı [mstr_admin]: mstr_user
Şifre: ********

Bu ayarlarla devam edilsin mi? (E/h): E

[INFO] Konfigürasyon kaydedildi: /opt/mstr-helper/config/deployment.yaml

=== Execution Summary ===
✅ PASS: CPU Cores (8 cores) - OK
✅ PASS: RAM (32 GB) - OK
✅ PASS: Disk Space (150 GB free) - OK
❌ FAIL: Hostname FQDN - Hostname does not resolve to FQDN
✅ PASS: Firewall Port 8080 - Port available
✅ PASS: Remote Server (192.168.1.10:34952) - Reachable
❌ FAIL: Ulimits - Open files: 4096 (required: 65535)

[INFO] Sorunlar tespit edildi. Otomatik düzeltme başlatılıyor...
[SUCCESS] /etc/hosts düzeltildi: web-server.localdomain eklendi
[SUCCESS] /etc/security/limits.conf güncellendi
[INFO] Yeni oturum açarak ulimits değişikliklerini aktifleştirin

[INFO] Kontroller tekrar yapılıyor...
✅ Tüm kontroller başarılı!
```

**Sonraki Çalıştırmalarda:**
```
=== Deployment Tipi Seçin ===
1. Combined - Intelligence Server + Web Server (aynı sunucu)
2. Web-Only - Sadece Web Server
3. IS-Only - Sadece Intelligence Server
Seçiminiz [2]: ← Enter (önceki değer kullanılır)

=== Distributed Deployment - Remote Server ===
Intelligence Server IP adresi [192.168.1.10]: ← Enter (önceki değer)
Intelligence Server kurulu mu? (E/h) [E]: ← Enter

=== Veritabanı Tipi Seçin ===
...
```

### Komut 2: MicroStrategy Kurulumu (Manuel)

Hazırlık tamamlandıktan sonra MicroStrategy installer'ı çalıştırın:

```bash
# Installer'a execute izni verin
chmod +x MicroStrategy-*.sh

# Installer'ı çalıştırın
sudo ./MicroStrategy-*.sh
```

**Kurulum sırasında:**
- Combined: Hem Intelligence Server hem Web Server seçin
- Web-Only: Sadece Web Server seçin
- IS-Only: Sadece Intelligence Server seçin

**Database bilgileri kurulum sırasında gerekli:**
- prepare komutu sonrası verilen bilgileri kullanın

### Komut 3: Verify (Doğrulama)

Kurulum sonrası servislerin çalıştığını doğrulayın:

```bash
sudo mstr-helper verify
```

**Bu komut:**
- ✅ Intelligence Server portlarını kontrol eder (34952, 34962, 34972)
- ✅ Web Server portlarını kontrol eder (8080, 8443)
- ✅ HTTP health check yapar
- ✅ Platform Analytics kontrol eder (39320)
- ✅ Library Server kontrol eder (41080)
- ✅ Systemd servislerini kontrol eder
- ✅ Erişim bilgilerini gösterir

### Komut 4: Rollback (Geri Alma)

Yapılan değişiklikleri geri alın:

```bash
sudo mstr-helper rollback
```

**Bu komut:**
- ⏪ Xvfb servisini durdurur ve kaldırır
- ⏪ SELinux ayarlarını eski haline getirir
- ⏪ System limits'i geri yükler
- ⏪ Backup'ları kullanır

## Deployment Senaryoları

### Senaryo 1: Combined (Tek Sunucu)

Hem IS hem Web aynı sunucuda:

```bash
# Sunucu 1
sudo mstr-helper prepare
# Deployment: Combined seçin
# Database bilgilerini girin

# MicroStrategy installer'ı çalıştırın
sudo ./MicroStrategy-*.sh
# Hem IS hem Web seçin

# Doğrulama
sudo mstr-helper verify
```

### Senaryo 2: Distributed (İki Sunucu)

**IS Sunucusu (Önce Kurulur):**
```bash
sudo mstr-helper prepare
# Deployment: IS-Only seçin
# Database bilgilerini girin
# Web Server IP'si: 192.168.1.11
# Web Server kurulu mu?: h (hayır - henüz kurulmadı)
# [Remote server kontrolleri atlanır]

# MicroStrategy installer'ı çalıştırın
sudo ./MicroStrategy-*.sh
# Sadece IS seçin

# Doğrulama
sudo mstr-helper verify
```

**Web Sunucusu (Sonra Kurulur):**
```bash
sudo mstr-helper prepare
# Deployment: Web-Only seçin
# Database gerekmiyor (IS'den okur)
# IS Server IP'si: 192.168.1.10
# IS Server kurulu mu?: E (evet - önceki adımda kuruldu)
# [IS portları kontrol edilir: 34952, 9500, vb.]

sudo ./MicroStrategy-*.sh
# Sadece Web Server seçin
# IS bağlantısını yapılandırın (IS sunucusunun IP:34952)

sudo mstr-helper verify
```

**IS Sunucusu:**
```bash
sudo mstr-helper prepare
# Deployment: IS-Only seçin
# Database bilgilerini girin

sudo ./MicroStrategy-*.sh
# Sadece Intelligence Server seçin

sudo mstr-helper verify
```

## Loglar ve Raporlar

**Loglar:**
```
/var/log/mstr-helper/mstr-helper_YYYYMMDD_HHMMSS.log
```

**Raporlar:**
```
/var/log/mstr-helper/reports/mstr_helper_report_YYYYMMDD_HHMMSS.html
/var/log/mstr-helper/reports/mstr_helper_report_YYYYMMDD_HHMMSS.json
```

**Backups:**
```
/var/lib/mstr-helper/backups/YYYYMMDD_HHMMSS_backup_manifest.json
/var/lib/mstr-helper/backups/YYYYMMDD_HHMMSS_<filename>
```

**Konfigürasyon:**
```
/opt/mstr-helper/config/deployment.yaml
```

## Özellikler

✅ **Otomatik Linux Dağıtım Tespiti:** RHEL, CentOS, Oracle Linux, Ubuntu  
✅ **Sistem Kontrolleri:** CPU, RAM, Disk, Swap, ulimits  
✅ **Network Kontrolleri:** Port availability, DNS resolution  
✅ **Veritabanı Testi:** Connection, privileges (CREATE, INSERT, SELECT, DROP)  
✅ **Paket Yönetimi:** Otomatik yum/dnf/apt ile gerekli paketleri yükleme  
✅ **X Display:** Xvfb otomatik kurulum ve systemd service  
✅ **Firewall:** firewalld/ufw/iptables otomatik yapılandırma  
✅ **SELinux:** Otomatik permissive mod  
✅ **System Limits:** ulimit ve sysctl ayarları  
✅ **Backup/Rollback:** Tüm değişiklikler backup'lanır  
✅ **Post-Verification:** Kurulum sonrası servis healthcheck  
✅ **Raporlama:** HTML ve JSON formatında detaylı raporlar

## Troubleshooting

### Problem: Port zaten kullanımda

```bash
# Port'u kullanan process'i bulun
sudo lsof -i :34952
sudo netstat -tuln | grep 34952

# Process'i durdurun
sudo systemctl stop <service-name>
# veya
sudo kill <pid>
```

### Problem: Database bağlantısı başarısız

```bash
# Network bağlantısını test edin
telnet db-server 5432
nc -zv db-server 5432

# Firewall kontrolü
sudo firewall-cmd --list-all

# Database loglarını kontrol edin
# PostgreSQL: /var/lib/pgsql/data/log/
# Oracle: $ORACLE_HOME/diag/
```

### Problem: Xvfb başlatılamıyor

```bash
# Servis durumunu kontrol edin
sudo systemctl status xvfb

# Manuel başlatın
sudo systemctl start xvfb

# Logları kontrol edin
sudo journalctl -u xvfb -f
```

### Problem: Paket kurulamıyor

```bash
# Repo'ları kontrol edin
sudo yum repolist   # RHEL/CentOS
sudo apt update     # Ubuntu

# Manuel kurulum deneyin
sudo yum install <package>
sudo apt-get install <package>
```

## Sistem Gereksinimleri

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 60 GB
- Swap: 8 GB

**Önerilen:**
- CPU: 8+ cores
- RAM: 16-32 GB
- Disk: 100+ GB SSD
- Swap: 16+ GB

**Desteklenen Linux:**
- RHEL 7, 8, 9
- CentOS 7, 8
- Oracle Linux 7, 8, 9
- Ubuntu 18.04, 20.04, 22.04

**Desteklenen Veritabanları:**
- PostgreSQL
- Oracle
- SQL Server
- MySQL/MariaDB

## Destek

Issues ve sorular için GitHub repository.

---
**Version:** 1.0.0  
**Author:** ganimaltiok  
**Date:** January 2026
