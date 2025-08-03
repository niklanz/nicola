#!/bin/bash

# Script di deployment automatico per Raspberry Pi
# Sincronizza la versione locale con quella sul Raspberry Pi

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configurazione di default
DEFAULT_IP="192.168.1.100"
DEFAULT_USER="pi"
DEFAULT_PATH="/home/pi/spotify-pi"

# Funzione di aiuto
show_help() {
    echo "Uso: $0 [IP] [USER] [PATH]"
    echo ""
    echo "Parametri:"
    echo "  IP    - Indirizzo IP del Raspberry Pi (default: $DEFAULT_IP)"
    echo "  USER  - Username SSH (default: $DEFAULT_USER)"
    echo "  PATH  - Path del progetto sul Raspberry (default: $DEFAULT_PATH)"
    echo ""
    echo "Esempi:"
    echo "  $0                                    # Usa valori di default"
    echo "  $0 192.168.1.50                      # IP personalizzato"
    echo "  $0 192.168.1.50 pi /opt/spotify-pi   # Tutti i parametri"
    echo ""
    echo "Configurazione SSH:"
    echo "  Per evitare di inserire la password, configura le chiavi SSH:"
    echo "  ssh-keygen -t rsa -b 4096"
    echo "  ssh-copy-id pi@192.168.1.100"
}

# Parsing parametri
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

RASPBERRY_IP="${1:-$DEFAULT_IP}"
RASPBERRY_USER="${2:-$DEFAULT_USER}"
PROJECT_PATH="${3:-$DEFAULT_PATH}"

# Verifica che siamo nella directory corretta
if [[ ! -f "main.py" || ! -f "spotify_manager.py" ]]; then
    print_error "Esegui questo script dalla directory del progetto Spotify Pi"
    exit 1
fi

print_header "Deployment su Raspberry Pi"
echo "IP Raspberry: $RASPBERRY_IP"
echo "Username: $RASPBERRY_USER"
echo "Path progetto: $PROJECT_PATH"
echo ""

# Chiedi conferma
read -p "Continuare con il deployment? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment annullato"
    exit 1
fi

echo ""

# 1. Verifica connessione
print_status "Verifica connessione al Raspberry Pi..."
if ! ping -c 1 -W 3 $RASPBERRY_IP >/dev/null 2>&1; then
    print_error "Raspberry Pi non raggiungibile su $RASPBERRY_IP"
    echo "Verifica:"
    echo "- Che il Raspberry Pi sia acceso e connesso alla rete"
    echo "- Che l'indirizzo IP sia corretto"
    echo "- Che non ci siano firewall che bloccano la connessione"
    exit 1
fi
print_success "Raspberry Pi raggiungibile"

# 2. Verifica connessione SSH
print_status "Verifica connessione SSH..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $RASPBERRY_USER@$RASPBERRY_IP "echo 'SSH OK'" >/dev/null 2>&1; then
    print_error "Impossibile connettersi via SSH"
    echo "Verifica:"
    echo "- Username corretto: $RASPBERRY_USER"
    echo "- SSH abilitato sul Raspberry Pi"
    echo "- Credenziali SSH configurate"
    echo ""
    echo "Per configurare SSH senza password:"
    echo "ssh-keygen -t rsa -b 4096"
    echo "ssh-copy-id $RASPBERRY_USER@$RASPBERRY_IP"
    exit 1
fi
print_success "Connessione SSH OK"

# 3. Backup configurazione remota
print_status "Backup configurazione remota..."
ssh $RASPBERRY_USER@$RASPBERRY_IP << EOF
cd $PROJECT_PATH 2>/dev/null || { echo "Directory $PROJECT_PATH non trovata"; exit 1; }
cp .env .env.backup 2>/dev/null || echo "File .env non trovato, verrà creato"
cp .spotify_cache .spotify_cache.backup 2>/dev/null || echo "Cache Spotify non trovata"
EOF
print_success "Backup completato"

# 4. Ferma servizi sul Raspberry
print_status "Fermo servizi sul Raspberry Pi..."
ssh $RASPBERRY_USER@$RASPBERRY_IP << EOF
cd $PROJECT_PATH
echo "Fermo servizio systemd..."
sudo systemctl stop spotify-pi 2>/dev/null || echo "Servizio systemd non attivo"
echo "Fermo processi Python..."
pkill -f "python.*main.py" 2>/dev/null || echo "Nessun processo Python da fermare"
echo "Fermo librespot..."
pkill librespot 2>/dev/null || echo "Librespot non in esecuzione"
sleep 2
echo "Servizi fermati"
EOF
print_success "Servizi fermati"

# 5. Sincronizzazione file
print_status "Sincronizzazione file..."
echo "Trasferimento in corso..."

# Usa rsync per sincronizzazione efficiente
rsync -avz --progress \
      --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.env' \
      --exclude='.env.backup' \
      --exclude='venv' \
      --exclude='spotify_env' \
      --exclude='spotify-env' \
      --exclude='*.log' \
      --exclude='.spotify_cache' \
      --exclude='.spotify_cache.backup' \
      --exclude='.DS_Store' \
      --exclude='node_modules' \
      ./ $RASPBERRY_USER@$RASPBERRY_IP:$PROJECT_PATH/

print_success "File sincronizzati"

# 6. Configurazione e riavvio sul Raspberry
print_status "Configurazione e riavvio..."
ssh $RASPBERRY_USER@$RASPBERRY_IP << EOF
cd $PROJECT_PATH

echo "Ripristino configurazione..."
cp .env.backup .env 2>/dev/null || echo "Configurazione .env non ripristinata"
cp .spotify_cache.backup .spotify_cache 2>/dev/null || echo "Cache Spotify non ripristinata"

echo "Rendo eseguibili gli script..."
chmod +x *.sh 2>/dev/null || echo "Nessuno script da rendere eseguibile"

echo "Aggiorno dipendenze Python..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "Dipendenze aggiornate"
else
    echo "Virtual environment non trovato, uso Python di sistema"
    pip3 install -r requirements.txt --quiet --user 2>/dev/null || echo "Errore aggiornamento dipendenze"
fi

echo "Avvio applicazione..."
nohup python3 main.py > /tmp/spotify-pi.log 2>&1 &
APP_PID=\$!
echo "Applicazione avviata con PID: \$APP_PID"

# Attendi che l'applicazione si avvii
echo "Attendo avvio applicazione..."
sleep 5

# Verifica che l'applicazione sia in esecuzione
if pgrep -f "python.*main.py" >/dev/null; then
    echo "✅ Applicazione avviata con successo!"
    LOCAL_IP=\$(hostname -I | awk '{print \$1}')
    echo "🌐 Interfaccia web: http://\$LOCAL_IP:5000"
    
    # Mostra stato librespot
    if pgrep librespot >/dev/null; then
        echo "🎵 Librespot attivo"
    else
        echo "⚠️  Librespot non attivo - esegui ./fix_audio_quick.sh se necessario"
    fi
else
    echo "❌ Errore nell'avvio dell'applicazione"
    echo "Log errori:"
    tail -10 /tmp/spotify-pi.log 2>/dev/null || echo "Nessun log disponibile"
    exit 1
fi
EOF

if [ $? -eq 0 ]; then
    print_success "Deployment completato con successo!"
    echo ""
    print_header "Informazioni Post-Deployment"
    echo "🌐 Interfaccia web: http://$RASPBERRY_IP:5000"
    echo "📱 Apri l'URL nel browser per controllare l'applicazione"
    echo ""
    echo "Comandi utili sul Raspberry Pi:"
    echo "  ssh $RASPBERRY_USER@$RASPBERRY_IP"
    echo "  cd $PROJECT_PATH"
    echo "  ./diagnose_audio.sh          # Diagnostica audio"
    echo "  ./fix_audio_quick.sh         # Fix rapido audio"
    echo "  tail -f /tmp/spotify-pi.log  # Visualizza log"
    echo ""
    print_warning "Se il dispositivo non appare in Spotify, esegui ./fix_audio_quick.sh sul Raspberry Pi"
else
    print_error "Errore durante il deployment"
    exit 1
fi