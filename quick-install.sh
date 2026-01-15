#!/bin/bash

#################################################
# MicroStrategy Installation Helper
# Quick Install Script - Git Repository Version
#################################################

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sabitler
REPO_URL="https://github.com/ganimaltiok/mstr-install-helper.git"
TEMP_DIR="/tmp/mstr-install-helper-$$"
INSTALL_DIR="/opt/mstr-helper"

echo -e "${BLUE}"
cat << "EOF"
========================================
   MicroStrategy Installation Helper
   Quick Install from Git Repository
========================================
EOF
echo -e "${NC}"

# Root kontrolü
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}✗ Bu script root olarak çalıştırılmalıdır!${NC}"
   echo "Lütfen 'sudo bash quick-install.sh' komutunu kullanın"
   exit 1
fi

# Git kontrolü
echo -e "\n${YELLOW}[1/6] Git kontrolü...${NC}"
if ! command -v git &> /dev/null; then
    echo "Git bulunamadı, kuruluyor..."
    if command -v dnf &> /dev/null; then
        dnf install -y git
    elif command -v yum &> /dev/null; then
        yum install -y git
    elif command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y git
    else
        echo -e "${RED}✗ Paket yöneticisi bulunamadı!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Git bulundu: $(git --version)${NC}"
fi

# Python3 kontrolü
echo -e "\n${YELLOW}[2/6] Python3 kontrolü...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Python3 bulunamadı, kuruluyor..."
    if command -v dnf &> /dev/null; then
        dnf install -y python3
    elif command -v yum &> /dev/null; then
        yum install -y python3
    elif command -v apt-get &> /dev/null; then
        apt-get install -y python3
    else
        echo -e "${RED}✗ Python3 kurulamadı!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Python3 bulundu: $(python3 --version)${NC}"
fi

# pip kontrolü
echo -e "\n${YELLOW}[3/6] pip kontrolü...${NC}"
if ! python3 -m pip --version &> /dev/null; then
    echo "pip bulunamadı, kuruluyor..."
    curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py
    rm /tmp/get-pip.py
else
    echo -e "${GREEN}✓ pip bulundu${NC}"
fi

# Repository'den indir
echo -e "\n${YELLOW}[4/6] Proje repository'den indiriliyor...${NC}"
echo "Kaynak: $REPO_URL"

# Önceki dosyaları temizle
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Git clone
if git clone "$REPO_URL" "$TEMP_DIR"; then
    echo -e "${GREEN}✓ Proje başarıyla indirildi${NC}"
else
    echo -e "${RED}✗ Proje indirilemedi!${NC}"
    echo "Lütfen repository URL'ini kontrol edin: $REPO_URL"
    exit 1
fi

# Kurulum dizinini hazırla
echo -e "\n${YELLOW}[5/6] Kurulum dizini hazırlanıyor...${NC}"
mkdir -p "$INSTALL_DIR"

# Dosyaları kopyala
echo "Dosyalar kopyalanıyor: $TEMP_DIR -> $INSTALL_DIR"
cp -r "$TEMP_DIR"/* "$INSTALL_DIR/"

# Python bağımlılıklarını kur
echo -e "\n${YELLOW}[6/6] Python bağımlılıkları kuruluyor...${NC}"
cd "$INSTALL_DIR"
python3 -m pip install --ignore-installed -r requirements.txt

# Executable oluştur
echo -e "\n${YELLOW}Komut satırı aracı oluşturuluyor...${NC}"

cat > /usr/local/bin/mstr-helper << 'EOFBIN'
#!/bin/bash
cd /opt/mstr-helper
python3 -m src.main "$@"
EOFBIN

chmod +x /usr/local/bin/mstr-helper

# Config dizini oluştur
mkdir -p /var/lib/mstr-helper/backups
mkdir -p /var/log/mstr-helper

# Temizlik
rm -rf "$TEMP_DIR"

# Başarılı mesajı
echo -e "\n${GREEN}"
cat << "EOF"
========================================
  ✓ Kurulum Başarıyla Tamamlandı!
========================================
EOF
echo -e "${NC}"

echo -e "${BLUE}Kullanım:${NC}"
echo "  1. Sunucu hazırlığı:    ${GREEN}sudo mstr-helper prepare${NC}"
echo "  2. Kurulum doğrulama:   ${GREEN}sudo mstr-helper verify${NC}"
echo "  3. Geri alma:           ${GREEN}sudo mstr-helper rollback${NC}"
echo ""
echo -e "${BLUE}Log dosyaları:${NC} /var/log/mstr-helper/"
echo -e "${BLUE}Yapılandırma:${NC} /opt/mstr-helper/config/"
echo ""
echo -e "${YELLOW}Kuruluma başlamak için 'sudo mstr-helper prepare' komutunu çalıştırın${NC}"
