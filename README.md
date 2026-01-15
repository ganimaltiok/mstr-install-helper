# MicroStrategy Installation Helper

Linux sunucularını MicroStrategy Intelligence Server ve Web Server kurulumu için otomatik hazırlayan Python CLI uygulaması.

## Özellikler

- ✅ **Otomatik Linux Dağıtım Tespiti**: RHEL, CentOS, Oracle Linux, Ubuntu, SLES
- ✅ **Deployment Tipi Seçimi**: Combined, Web-Only, IS-Only
- ✅ **Sistem Kontrolleri**: CPU, RAM, Disk, Swap, Network, Portlar
- ✅ **Paket Yönetimi**: Gerekli tüm Linux paketlerini otomatik yükler
- ✅ **X Display Yapılandırması**: Xvfb otomatik kurulum ve yapılandırma
- ✅ **Veritabanı Bağlantı Testi**: PostgreSQL, Oracle, SQL Server, MySQL desteği
- ✅ **Güvenlik Yapılandırması**: Firewall, SELinux, System Limits
- ✅ **Post-Installation Verification**: Servis sağlık kontrolleri
- ✅ **Rollback Desteği**: Yapılan değişiklikleri geri alma

## Kurulum

### Tek Komut Kurulum

```bash
sudo bash install.sh
```

Bu komut:
1. Python3 ve pip'i kontrol eder/yükler
2. Gerekli Python bağımlılıklarını kurar
3. `/opt/mstr-helper` dizinine uygulamayı kurar
4. `/usr/local/bin/mstr-helper` komutu oluşturur

## Kullanım

### 1. Sunucu Hazırlığı

MicroStrategy kurulumu için sunucuyu hazırlamak:

```bash
sudo mstr-helper prepare
```

Bu komut:
- Linux dağıtımını tespit eder
- Deployment tipini sorar (Combined/Web-Only/IS-Only)
- Veritabanı tipini ve bağlantı bilgilerini sorar
- Tüm sistem kontrollerini yapar
- Gerekli paketleri yükler
- Xvfb yapılandırması yapar
- Firewall kurallarını ekler
- SELinux ayarlarını yapar
- System limits'i ayarlar
- Veritabanı bağlantısını test eder
- Kurulum talimatlarını gösterir
- HTML rapor oluşturur

### 2. Kurulum Sonrası Doğrulama

MicroStrategy kurulumu yaptıktan sonra servisleri test etmek:

```bash
sudo mstr-helper verify
```

Bu komut:
- Deployment tipini config'den okur
- Intelligence Server port kontrolü (34952)
- Web Server HTTP/HTTPS health check
- Platform Analytics port kontrolü (39320)
- Library Server port kontrolü (41080)
- Tüm servisler için detaylı rapor

### 3. Rollback

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
- 34962 (Metadata)
- 34972 (Statistics)
- 39321 (Collaboration)
- 41080 (Library)
- 8080 (Tomcat HTTP)
- 8443 (Tomcat HTTPS)

### Web-Only (Sadece Web Sunucusu)
Sadece MicroStrategy Web Server.

**Açılan Portlar:**
- 8080 (Tomcat HTTP)
- 8443 (Tomcat HTTPS)

**Kurulum Notları:**
- Intelligence Server IP adresi gerekli
- Web konfigürasyonunda IS bağlantısı belirtilmeli

### IS-Only (Sadece Intelligence Server)
Sadece MicroStrategy Intelligence Server.

**Açılan Portlar:**
- 34952 (Intelligence Server)
- 34962 (Metadata)
- 34972 (Statistics)
- 39321 (Collaboration)
- 41080 (Library)

## Desteklenen Veritabanları

- **PostgreSQL** - psycopg2 driver
- **Oracle** - cx_Oracle driver (Oracle Instant Client gerekli)
- **SQL Server** - pyodbc + Microsoft ODBC Driver
- **MySQL/MariaDB** - pymysql driver

## Sistem Gereksinimleri

### Minimum:
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 60 GB boş alan
- **Swap**: RAM kadar

### Önerilen:
- **CPU**: 8+ cores
- **RAM**: 16-32 GB
- **Disk**: 100+ GB SSD
- **Swap**: 16+ GB

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
