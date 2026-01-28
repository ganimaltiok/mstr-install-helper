#!/bin/bash

#############################################################################
# MicroStrategy Installation Helper - Bootstrap Script
# Bu script Python3, pip ve gerekli bağımlılıkları kurar ve uygulamayı
# /usr/local/bin/mstr-helper olarak erişilebilir hale getirir.
#############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/mstr-helper"
BIN_LINK="/usr/bin/mstr-helper"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MicroStrategy Installation Helper${NC}"
echo -e "${GREEN}Bootstrap Kurulumu${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Root kontrolü
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Bu script root olarak çalıştırılmalıdır!${NC}"
   echo "Lütfen: sudo bash install.sh"
   exit 1
fi

# Python3 kontrolü ve kurulumu
echo -e "${YELLOW}[1/5] Python3 kontrolü...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Python3 bulunamadı, kuruluyor..."
    if command -v yum &> /dev/null; then
        yum install -y python3 python3-pip
    elif command -v dnf &> /dev/null; then
        dnf install -y python3 python3-pip
    elif command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3 python3-pip
    elif command -v zypper &> /dev/null; then
        zypper install -y python3 python3-pip
    else
        echo -e "${RED}Desteklenmeyen paket yöneticisi!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Python3 bulundu: $(python3 --version)${NC}"
fi

# pip kontrolü
echo -e "\n${YELLOW}[2/5] pip kontrolü...${NC}"
if ! python3 -m pip --version &> /dev/null; then
    echo "pip bulunamadı, kuruluyor..."
    curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py
    rm /tmp/get-pip.py
else
    echo -e "${GREEN}✓ pip bulundu${NC}"
fi

# Kurulum dizini oluştur
echo -e "\n${YELLOW}[3/5] Kurulum dizini hazırlanıyor...${NC}"
mkdir -p "$INSTALL_DIR"

# Dosyaları kopyala (sadece farklı dizindeyse)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo "Dosyalar kopyalanıyor: $SCRIPT_DIR -> $INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
else
    echo "Zaten doğru dizindesiniz: $INSTALL_DIR (kopyalama atlanıyor)"
fi

# Python bağımlılıklarını kur
echo -e "\n${YELLOW}[4/5] Python bağımlılıkları kuruluyor...${NC}"
cd "$INSTALL_DIR"
python3 -m pip install --ignore-installed -r requirements.txt

# Executable oluştur
echo -e "\n${YELLOW}[5/5] Komut satırı aracı oluşturuluyor...${NC}"

cat > "$BIN_LINK" << 'EOFBIN'
#!/bin/bash
cd /opt/mstr-helper
python3 -m src.main "$@"
EOFBIN

chmod +x "$BIN_LINK"

# Config dizini oluştur
mkdir -p /var/lib/mstr-helper/backups
mkdir -p /var/log/mstr-helper

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Kurulum başarılı!${NC}"
echo -e "${GREEN}========================================${NC}\n"
echo -e "Kullanım:"
echo -e "  ${YELLOW}mstr-helper prepare${NC}  - Sunucuyu MicroStrategy kurulumu için hazırla"
echo -e "  ${YELLOW}mstr-helper verify${NC}   - Kurulum sonrası servis testleri"
echo -e "  ${YELLOW}mstr-helper rollback${NC} - Yapılan değişiklikleri geri al"
echo -e "\nLoglar: /var/log/mstr-helper/"
echo -e "Backup: /var/lib/mstr-helper/backups/\n"
