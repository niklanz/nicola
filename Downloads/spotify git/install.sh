#!/bin/bash

# Script di installazione per Spotify Raspberry Pi Controller
# Questo script configura tutto il necessario per far funzionare l'applicazione

set -e  # Esce se qualsiasi comando fallisce

echo "=== Spotify Raspberry Pi Controller - Installazione ==="
echo ""

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per stampare messaggi colorati
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica se siamo su Raspberry Pi
check_raspberry_pi() {
    if grep -q "BCM\|ARM" /proc/cpuinfo 2>/dev/null; then
        print_success "Raspberry Pi rilevato"
        return 0
    else
        print_warning "Non sembra essere un Raspberry Pi, alcune funzionalità potrebbero non funzionare"
        return 1
    fi
}

# Aggiorna il sistema
update_system() {
    print_status "Aggiornamento del sistema..."
    sudo apt update
    sudo apt upgrade -y
    print_success "Sistema aggiornato"
}

# Installa dipendenze di sistema
install_system_dependencies() {
    print_status "Installazione dipendenze di sistema..."
    
    # Pacchetti essenziali
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        alsa-utils \
        pulseaudio \
        pulseaudio-utils
    
    # GPIO per Raspberry Pi
    if check_raspberry_pi; then
        sudo apt install -y python3-rpi.gpio
    fi
    
    print_success "Dipendenze di sistema installate"
}

# Configura audio
setup_audio() {
    print_status "Configurazione audio..."
    
    # Abilita audio jack
    if [ -f /boot/config.txt ]; then
        sudo sed -i 's/#dtparam=audio=on/dtparam=audio=on/' /boot/config.txt
        print_status "Audio jack abilitato in /boot/config.txt"
    fi
    
    # Configura ALSA
    if [ ! -f ~/.asoundrc ]; then
        cat > ~/.asoundrc << EOF
pcm.!default {
    type hw
    card 0
    device 0
}
ctl.!default {
    type hw
    card 0
}
EOF
        print_status "Configurazione ALSA creata"
    fi
    
    # Avvia PulseAudio
    pulseaudio --start --log-target=syslog 2>/dev/null || true
    
    print_success "Audio configurato"
}

# Installa Spotify Connect
install_spotify_connect() {
    print_status "Installazione Spotify Connect (librespot)..."
    
    # Verifica se librespot è già installato
    if command -v librespot >/dev/null 2>&1; then
        print_success "librespot già installato"
        return
    fi
    
    # Installa Rust (necessario per compilare librespot)
    if ! command -v cargo >/dev/null 2>&1; then
        print_status "Installazione Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source ~/.cargo/env
    fi
    
    # Installa librespot
    print_status "Compilazione librespot (può richiedere diversi minuti)..."
    cargo install librespot --features alsa-backend
    
    print_success "Spotify Connect installato"
}

# Crea ambiente virtuale Python
setup_python_env() {
    print_status "Configurazione ambiente Python..."
    
    # Crea virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment creato"
    fi
    
    # Attiva virtual environment
    source venv/bin/activate
    
    # Aggiorna pip
    pip install --upgrade pip
    
    # Installa dipendenze Python
    pip install -r requirements.txt
    
    print_success "Ambiente Python configurato"
}

# Configura file .env
setup_env_file() {
    print_status "Configurazione file .env..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_warning "File .env creato da .env.example"
        print_warning "IMPORTANTE: Modifica il file .env con le tue credenziali Spotify!"
        echo ""
        echo "Passi necessari:"
        echo "1. Vai su https://developer.spotify.com/dashboard/"
        echo "2. Crea una nuova app"
        echo "3. Copia Client ID e Client Secret nel file .env"
        echo "4. Imposta Redirect URI: http://localhost:8888/callback"
        echo ""
    else
        print_success "File .env già esistente"
    fi
}

# Crea servizio systemd
create_systemd_service() {
    print_status "Creazione servizio systemd..."
    
    SERVICE_FILE="/etc/systemd/system/spotify-pi.service"
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Spotify Raspberry Pi Controller
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Ricarica systemd
    sudo systemctl daemon-reload
    
    print_success "Servizio systemd creato"
    print_status "Per abilitare l'avvio automatico: sudo systemctl enable spotify-pi"
    print_status "Per avviare il servizio: sudo systemctl start spotify-pi"
}

# Crea script di avvio librespot
create_librespot_script() {
    print_status "Creazione script librespot..."
    
    cat > start_librespot.sh << 'EOF'
#!/bin/bash

# Script per avviare librespot (Spotify Connect)
# Modifica i parametri secondo le tue necessità

DEVICE_NAME="RaspberryPi"
BITRATE="320"
DEVICE_TYPE="speaker"

# Avvia librespot
librespot \
    --name "$DEVICE_NAME" \
    --bitrate $BITRATE \
    --device-type $DEVICE_TYPE \
    --backend alsa \
    --enable-volume-normalisation \
    --initial-volume 70
EOF

    chmod +x start_librespot.sh
    print_success "Script librespot creato (start_librespot.sh)"
}

# Test installazione
test_installation() {
    print_status "Test dell'installazione..."
    
    # Test Python
    if source venv/bin/activate && python -c "import spotipy, flask, RPi.GPIO" 2>/dev/null; then
        print_success "Dipendenze Python OK"
    else
        print_error "Problema con le dipendenze Python"
        return 1
    fi
    
    # Test audio
    if aplay -l >/dev/null 2>&1; then
        print_success "Sistema audio OK"
    else
        print_warning "Possibili problemi con il sistema audio"
    fi
    
    print_success "Test completati"
}

# Funzione principale
main() {
    echo "Questo script installerà e configurerà Spotify Raspberry Pi Controller"
    echo "Assicurati di avere una connessione internet attiva."
    echo ""
    read -p "Continuare con l'installazione? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installazione annullata"
        exit 1
    fi
    
    echo ""
    print_status "Inizio installazione..."
    
    # Verifica Raspberry Pi
    check_raspberry_pi
    
    # Aggiorna sistema
    update_system
    
    # Installa dipendenze
    install_system_dependencies
    
    # Configura audio
    setup_audio
    
    # Installa Spotify Connect
    install_spotify_connect
    
    # Configura Python
    setup_python_env
    
    # Configura .env
    setup_env_file
    
    # Crea servizio systemd
    create_systemd_service
    
    # Crea script librespot
    create_librespot_script
    
    # Test installazione
    test_installation
    
    echo ""
    print_success "=== INSTALLAZIONE COMPLETATA ==="
    echo ""
    echo "Prossimi passi:"
    echo "1. Modifica il file .env con le tue credenziali Spotify"
    echo "2. Avvia librespot: ./start_librespot.sh"
    echo "3. Avvia l'applicazione: python main.py"
    echo "4. Apri http://$(hostname -I | awk '{print $1}'):5000 nel browser"
    echo ""
    echo "Per l'avvio automatico:"
    echo "sudo systemctl enable spotify-pi"
    echo "sudo systemctl start spotify-pi"
    echo ""
    print_warning "IMPORTANTE: Configura le credenziali Spotify nel file .env prima di avviare!"
}

# Esegui solo se chiamato direttamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi