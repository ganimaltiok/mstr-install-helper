# Git Repository Düzeltme Kılavuzu

## Sorun
`/opt/mstr-helper` dizininde `.git` klasörü olmadığı için `git pull` çalışmıyor.

## Çözüm

Sunucuda şu adımları uygulayın:

### Yöntem 1: Git Repository'yi Yeniden Başlat (Önerilen)

```bash
# 1. Mevcut kurulumun olduğu dizine git
cd /opt/mstr-helper

# 2. Git repository'yi başlat
sudo git init

# 3. Remote repository ekle
sudo git remote add origin https://github.com/ganimaltiok/mstr-install-helper.git

# 4. Fetch yap
sudo git fetch origin

# 5. Branch'i ayarla ve son commit'e git
sudo git reset --hard origin/main

# 6. Branch tracking ayarla
sudo git branch --set-upstream-to=origin/main main

# 7. Şimdi git pull çalışır
sudo git pull
```

### Yöntem 2: Tamamen Yeniden Kur (Alternatif)

```bash
# 1. Eski kurulumu yedekle (gerekirse)
sudo cp -r /opt/mstr-helper /opt/mstr-helper.backup

# 2. Temizle ve yeniden kur
sudo rm -rf /opt/mstr-helper
curl -sSL https://raw.githubusercontent.com/ganimaltiok/mstr-install-helper/main/quick-install.sh | sudo bash
```

### Yöntem 3: Manuel Git Clone (En Basit)

```bash
# 1. Backup al
sudo mv /opt/mstr-helper /opt/mstr-helper.backup

# 2. Git clone ile kur
sudo git clone https://github.com/ganimaltiok/mstr-install-helper.git /opt/mstr-helper

# 3. Python bağımlılıklarını kur
cd /opt/mstr-helper
sudo python3 -m pip install -r requirements.txt

# 4. Komut dosyasının çalıştığını doğrula
mstr-helper --help

# 5. Artık git pull çalışır
sudo git pull
```

## Test

```bash
cd /opt/mstr-helper
sudo git pull
```

Başarılı olursa şunu görmeli:
```
Already up to date.
```
veya
```
Updating ...
Fast-forward
 ...
```

## Sonraki Güncellemeler İçin

Artık güncelleme çok basit:

```bash
cd /opt/mstr-helper
sudo git pull
```

## Not

- Kurulum sonrası configuration'larınız `/opt/mstr-helper/config/deployment.yaml` dosyasında kayıtlı
- Log'lar `/var/log/mstr-helper/` dizininde
- Backup'lar `/var/lib/mstr-helper/backups/` dizininde

Bu dosyalar git pull ile değişmez.
