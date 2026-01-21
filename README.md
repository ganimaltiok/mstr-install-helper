# MicroStrategy Installation Helper

Linux sunucularını MicroStrategy Intelligence Server ve Web Server kurulumu için otomatik hazırlayan Python CLI uygulaması.

## Özellikler

### Temel Özellikler
- ✅ **Otomatik Linux Dağıtım Tespiti**: RHEL, CentOS, Oracle Linux, Ubuntu, SLES
- ✅ **Deployment Tipi Seçimi**: Combined, Web-Only, IS-Only
- ✅ **Sistem Kontrolleri**: CPU, RAM, Disk, Swap, Network, Portlar
- ✅ **Paket Yönetimi**: Gerekli tüm Linux paketlerini otomatik yükler
- ✅ **X Display Yapılandırması**: Xvfb otomatik kurulum ve yapılandırma
- ✅ **Veritabanı Bağlantı Testi**: PostgreSQL, Oracle, SQL Server, MySQL desteği
- ✅ **Güvenlik Yapılandırması**: Firewall, SELinux, System Limits
- ✅ **Post-Installation Verification**: Servis sağlık kontrolleri
- ✅ **Rollback Desteği**: Yapılan değişiklikleri geri alma

### Gelişmiş Özellikler
- ✅ **Configuration Persistence**: İlk çalıştırmada verilen cevaplar kaydedilir, sonraki çalıştırmalarda default olarak gelir- ✅ **Dedicated MicroStrategy User**: Özel Linux kullanıcısı oluşturma (opsiyonel, configurable, sudo yetkili)- ✅ **Distributed Deployment**: IS-Only veya Web-Only kurulumlarında karşı sunucunun port kontrollerini yapar
- ✅ **Smart Port Checks**: Remote sunucu henüz kurulu değilse port kontrollerini atlar
- ✅ **Auto-Fix**: FQDN ve ulimits sorunlarını otomatik düzeltir
- ✅ **Detaylı Özet**: Her işlemin pass/fail durumunu ve hata detaylarını gösterir
- ✅ **Git-Based Updates**: `git pull` ile kolayca güncellenebilir

## Kurulum

### Yöntem 1: Tek Komut Kurulum (Git Repository)

```bash
curl -sSL https://raw.githubusercontent.com/ganimaltiok/mstr-install-helper/main/quick-install.sh | sudo bash
```

### Yöntem 2: Manuel Kurulum

```bash
git clone https://github.com/ganimaltiok/mstr-install-helper.git
cd mstr-install-helper
sudo bash install.sh
```

Her iki yöntem de:
1. Python3 ve pip'i kontrol eder/yükler
2. Gerekli Python bağımlılıklarını kurar
3. `/opt/mstr-helper` dizinine uygulamayı kurar
4. `/usr/bin/mstr-helper` komutu oluşturur
5. Git repository'yi kopyalar (güncelleme için)

## Kullanım

### 1. Sunucu Hazırlığı

MicroStrategy kurulumu için sunucuyu hazırlamak:

```bash
sudo mstr-helper prepare
```

#### Bu komut:
- Linux dağıtımını tespit eder
- **Daha önce kaydedilmiş yapılandırmayı yükler** (varsa)
- Deployment tipini sorar (Combined/Web-Only/IS-Only)
- **Distributed deployment için:**
  - Remote sunucunun kurulu olup olmadığını sorar
  - Kuruluysa IP adresini ister ve port kontrolü yapar
  - Kurulu değilse kontrolleri atlar (kurulumdan sonra yapılacak)
- Veritabanı tipini ve bağlantı bilgilerini sorar (default değerlerle)
- Tüm sistem kontrollerini yapar
- **Sorunları otomatik düzeltir:**
  - FQDN sorunu varsa `/etc/hosts` dosyasını düzenler
  - Ulimits ayarlarını `/etc/security/limits.conf` dosyasına ekler
- Gerekli paketleri yükler
- Xvfb yapılandırması yapar
- Firewall kurallarını ekler
- SELinux ayarlarını yapar
- System limits'i ayarlar
- Veritabanı bağlantısını test eder
- **Detaylı özet gösterir** (pass/fail/atlanan işlemler)
- Kurulum talimatlarını gösterir
- HTML ve JSON rapor oluşturur

#### Örnek Çıktı:
```
============================================================
                             ÖZET
============================================================

Başarılı (8):
  ✓ System
  ✓ Network
  ✓ Database
  ✓ Dependencies
  ✓ Xdisplay
  ✓ Firewall
  ✓ Selinux
  ✓ Limits

Başarısız (0):

Toplam: 8 işlem (8 başarılı, 0 başarısız, 0 atlanan)
============================================================
```

### 2. Kurulum Sonrası Doğrulama

MicroStrategy kurulumu yaptıktan sonra servisleri test etmek:

```bash
sudo mstr-helper verify
```

Bu komut:
- Deployment tipini config'den okur
- Intelligence Server port kontrolü (34952, 9500, 8300-8302, 34962)
- Web Server HTTP/HTTPS health check (8080, 8443)
- Platform Analytics port kontrolü (9092, 2181, 6379, 5432)
- Tüm servisler için detaylı rapor

### 3. Güncelleme

Uygulamayı güncellemek:

```bash
cd /opt/mstr-helper
sudo git pull
```

### 4. Rollback

Yapılan değişiklikleri geri almak:

```bash
sudo mstr-helper rollback
```

Bu komut:
- Firewall kurallarını geri alır
- SELinux ayarlarını restore eder
- System limits'i eski haline getirir
- Backup'ları kullanır

## Desteklenen Deployment Tipleri

### Combined (Birleşik)
Aynı sunucuda hem Intelligence Server hem Web Server.

**Açılan Portlar:**
- 34952 (Intelligence Server)
- 9500 (Modeling Service)
- 8300-8302 (Topology Services)
- 34962 (REST Server)
- 3000 (Collaboration Server)
- 8080 (Tomcat HTTP)
- 8443 (Tomcat HTTPS)
- 20100 (Strategy Export)

### Web-Only (Sadece Web Sunucusu)
Sadece MicroStrategy Web Server.

**Açılan Portlar:**
- 8080 (Tomcat HTTP)
- 8443 (Tomcat HTTPS)
- 20100 (Strategy Export)

**Distributed Deployment Özellikleri:**
- Intelligence Server IP adresi istenir
- IS sunucusu kurulu mu diye sorar
- Kuruluysa IS portlarına erişim kontrolü yapar
- Kurulu değilse kontrolleri atlar (kurulumdan sonra yapılır)

### IS-Only (Sadece Intelligence Server)
Sadece MicroStrategy Intelligence Server.

**Açılan Portlar:**
- 34952 (Intelligence Server)
- 9500 (Modeling Service)
- 8300-8302 (Topology Services)
- 34962 (REST Server)
- 3000 (Collaboration Server)

**Distributed Deployment Özellikleri:**
- Web Server IP adresi istenir
- Web sunucusu kurulu mu diye sorar
- Kuruluysa Web portlarına erişim kontrolü yapar
- Kurulu değilse kontrolleri atlar (kurulumdan sonra yapılır)

## Desteklenen Veritabanları

- **PostgreSQL** - psycopg2 driver
- **Oracle** - cx_Oracle driver (Oracle Instant Client gerekli)
- **SQL Server** - pyodbc + Microsoft ODBC Driver
- **MySQL/MariaDB** - pymysql driver

## Sistem Gereksinimleri

### Minimum (MicroStrategy Resmi):
- **CPU**: 4 cores
- **RAM**: 16 GB
- **Disk**: 48 GB boş alan (3x RAM)
- **Swap**: 8 GB

### Önerilen (Yüksek Performans):
- **CPU**: 8+ cores
- **RAM**: 64+ GB
- **Disk**: 192+ GB SSD (3x RAM)
- **Swap**: 16+ GB

### System Limits:
- **Open Files**: 65535
- **Processes**: 8194
- **Stack Size**: 8 MB
- **CPU Time**: Unlimited
- **File Size**: Unlimited
- **Data Size**: Unlimited

## Configuration Persistence

İlk çalıştırmada verilen tüm cevaplar `/opt/mstr-helper/config/deployment.yaml` dosyasına kaydedilir:
- Deployment role
- Database bilgileri (şifre hariç)
- Remote sunucu IP'si (distributed deployment için)

Sonraki çalıştırmalarda:
- Kaydedilmiş değerler default olarak gösterilir
- Enter'a basarak önceki değerleri kullanabilirsiniz
- İsterseniz yeni değerler girebilirsiniz

## Otomatik Sorun Düzeltme

Uygulama tespit ettiği bazı sorunları otomatik düzeltir:

### 1. FQDN Sorunu
- `/etc/hosts` dosyasını düzenler
- Hostname için FQDN kaydı ekler
- Örnek: `172.25.8.155  MSTR-IS.localdomain MSTR-IS`
- Backup alır (rollback için)

### 2. Ulimits Sorunu
- `/etc/security/limits.conf` dosyasını düzenler
- MicroStrategy için gerekli değerleri ekler
- Yeni oturum açıldığında geçerli olur

### 3. Tekrar Kontrol
- Sorunlar düzeltildikten sonra otomatik olarak tüm kontroller tekrar yapılır
- Kullanıcıya düzeltilemeyen sorunlar için talimat verilir

## MicroStrategy İçin Özel Kullanıcı (Opsiyonel)

### Best Practice: Dedicated User

Uygulama opsiyonel olarak MicroStrategy için özel bir Linux kullanıcısı oluşturabilir:

**Avantajlar:**
- 🔒 **Güvenlik**: Root yerine minimum privilege principle
- 📦 **İzolasyon**: Ayrı user namespace, diğer uygulamalardan bağımsız
- 📊 **Yönetim**: Process ve file tracking kolay (`ps aux | grep mstr`)
- 🎯 **User-Specific Limits**: Sadece MicroStrategy kullanıcısı için ulimits

**Otomatik Yapılanlar:**
```bash
# Kullanıcı oluşturma
useradd -m -s /bin/bash mstr  # (veya seçtiğiniz isim)

# Sudo yetkisi
echo "mstr ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/mstr-mstr

# Home directory yapısı
/home/mstr/logs
/home/mstr/scripts
/home/mstr/backups
/home/mstr/installers

# User-specific ulimits
mstr soft nofile 65535
mstr hard nofile 65535
mstr soft nproc 8194
...
```

**Kurulum Talimatı:**
```bash
# 1. mstr kullanıcısı ile login
su - mstr

# 2. MicroStrategy installer'ı çalıştır
sudo ./MicroStrategy-*.sh
```

### Konfigrasyon

`prepare` komutu çalıştırıldığında:
1. "MicroStrategy için özel kullanıcı oluşturulsun mu?" sorusu sorulur
2. Evet derseniz, kullanıcı adını girersiniz (default: `mstr`)
3. Kullanıcı oluşturulur, sudo yetkisi verilir, home directory hazırlanır
4. Ulimits sadece bu kullanıcı için yapılandırılır

**Not:** Bu özellik opsiyoneldir. Hayır derseniz, root ile kuruluma devam edilir.

## Log ve Backup Konumları

- **Loglar**: `/var/log/mstr-helper/`
- **Backups**: `/var/lib/mstr-helper/backups/`
- **Config**: `/opt/mstr-helper/config/deployment.yaml`
- **Raporlar**: `/var/log/mstr-helper/reports/`

## Distributed Deployment

Distributed deployment için her sunucuda helper çalıştırılır:

**Web Sunucusunda:**
```bash
sudo mstr-helper prepare
# Deployment tipi: Web-Only seçin
# Intelligence Server IP'sini girin
```

**IS Sunucusunda:**
```bash
sudo mstr-helper prepare
# Deployment tipi: IS-Only seçin
```

## Troubleshooting

### Python3 bulunamadı
```bash
# RHEL/CentOS
sudo yum install python3

# Ubuntu
sudo apt-get install python3
```

### Permission denied
Script'i root olarak çalıştırın:
```bash
sudo mstr-helper prepare
```

### Port zaten kullanımda
```bash
# Port kontrolü
sudo netstat -tuln | grep 34952
sudo ss -tuln | grep 8080

# İlgili servisi durdur
sudo systemctl stop <service-name>
```

## Lisans

Internal use only - Ganimaltiok

## Destek

Issues: GitHub repository
