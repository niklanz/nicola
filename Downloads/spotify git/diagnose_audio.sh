#!/bin/bash

# Script di diagnostica audio per Raspberry Pi Spotify Connect
# Questo script identifica e risolve automaticamente i problemi audio comuni

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

print_fix() {
    echo -e "${GREEN}[FIX]${NC} $1"
}

# Funzione per chiedere conferma
ask_fix() {
    read -p "Vuoi che lo script risolva automaticamente questo problema? (y/N): " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Test 1: Verifica dispositivi audio
test_audio_devices() {
    print_header "Test 1: Dispositivi Audio"
    
    if aplay -l > /dev/null 2>&1; then
        print_success "Sistema audio disponibile"
        echo "Dispositivi trovati:"
        aplay -l | grep -E "^card|device"
    else
        print_error "Nessun dispositivo audio trovato"
        print_status "Possibili soluzioni:"
        echo "1. Verifica connessioni hardware"
        echo "2. Riavvia il Raspberry Pi"
        echo "3. Controlla /boot/config.txt per configurazione audio"
        
        if ask_fix; then
            print_fix "Ricarico moduli audio..."
            sudo modprobe snd_bcm2835 || true
            sudo systemctl restart alsa-state || true
        fi
    fi
    echo ""
}

# Test 2: Configurazione ALSA
test_alsa_config() {
    print_header "Test 2: Configurazione ALSA"
    
    if [ -f ~/.asoundrc ]; then
        print_success "File .asoundrc presente"
        echo "Contenuto:"
        cat ~/.asoundrc
    else
        print_warning "File .asoundrc mancante"
        
        if ask_fix; then
            print_fix "Creo configurazione ALSA di base..."
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
            print_success "File .asoundrc creato"
        fi
    fi
    echo ""
}

# Test 3: Test audio funzionale
test_audio_playback() {
    print_header "Test 3: Test Riproduzione Audio"
    
    print_status "Eseguo test speaker (2 secondi)..."
    if timeout 2s speaker-test -t wav -c 2 > /dev/null 2>&1; then
        print_success "Audio funzionante"
    else
        print_error "Problemi nella riproduzione audio"
        
        print_status "Controllo mixer audio..."
        amixer sget Master | grep -E "Playback|Volume"
        
        if ask_fix; then
            print_fix "Configuro volume e output audio..."
            # Imposta volume al 70%
            amixer sset Master 70% > /dev/null 2>&1 || true
            # Forza output jack 3.5mm
            sudo amixer cset numid=3 1 > /dev/null 2>&1 || true
            print_success "Configurazione audio aggiornata"
        fi
    fi
    echo ""
}

# Test 4: Verifica librespot
test_librespot() {
    print_header "Test 4: Librespot"
    
    if command -v librespot > /dev/null 2>&1; then
        print_success "Librespot installato"
        librespot --version
    else
        print_error "Librespot non installato"
        
        if ask_fix; then
            print_fix "Installo librespot..."
            if ! command -v cargo > /dev/null 2>&1; then
                print_status "Installo Rust..."
                curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                source ~/.cargo/env
            fi
            print_status "Compilo librespot (può richiedere tempo)..."
            cargo install librespot --features alsa-backend
            print_success "Librespot installato"
        fi
    fi
    
    # Verifica se librespot è in esecuzione
    if pgrep librespot > /dev/null; then
        print_success "Librespot in esecuzione"
        echo "Processi librespot:"
        ps aux | grep librespot | grep -v grep
    else
        print_warning "Librespot non in esecuzione"
        
        if ask_fix; then
            print_fix "Avvio librespot..."
            nohup librespot \
                --name "RaspberryPi" \
                --bitrate 320 \
                --device-type speaker \
                --backend alsa \
                --mixer softvol \
                --initial-volume 70 \
                --volume-ctrl linear \
                --enable-volume-normalisation > /tmp/librespot.log 2>&1 &
            sleep 2
            if pgrep librespot > /dev/null; then
                print_success "Librespot avviato"
            else
                print_error "Errore nell'avvio di librespot"
                echo "Log errori:"
                tail /tmp/librespot.log
            fi
        fi
    fi
    echo ""
}

# Test 5: Verifica rete
test_network() {
    print_header "Test 5: Connettività di Rete"
    
    # Verifica connessione internet
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        print_success "Connessione internet OK"
    else
        print_error "Nessuna connessione internet"
        return
    fi
    
    # Mostra IP locale
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    print_status "IP locale: $LOCAL_IP"
    
    # Verifica porte librespot
    if netstat -tlnp 2>/dev/null | grep librespot > /dev/null; then
        print_success "Librespot in ascolto su porte di rete"
        netstat -tlnp 2>/dev/null | grep librespot
    else
        print_warning "Librespot non in ascolto su porte di rete"
    fi
    echo ""
}

# Test 6: Verifica configurazione .env
test_env_config() {
    print_header "Test 6: Configurazione .env"
    
    if [ -f ".env" ]; then
        print_success "File .env presente"
        
        # Verifica configurazioni librespot
        if grep -q "LIBRESPOT_NAME" .env; then
            DEVICE_NAME=$(grep "LIBRESPOT_NAME" .env | cut -d'=' -f2)
            print_status "Nome dispositivo: $DEVICE_NAME"
        else
            print_warning "LIBRESPOT_NAME non configurato"
        fi
        
        if grep -q "LIBRESPOT_BACKEND" .env; then
            BACKEND=$(grep "LIBRESPOT_BACKEND" .env | cut -d'=' -f2)
            print_status "Backend audio: $BACKEND"
        else
            print_warning "LIBRESPOT_BACKEND non configurato"
        fi
    else
        print_error "File .env mancante"
        
        if ask_fix; then
            print_fix "Creo file .env di base..."
            cat > .env << EOF
# Configurazione Librespot
LIBRESPOT_NAME=RaspberryPi
LIBRESPOT_BITRATE=320
LIBRESPOT_DEVICE_TYPE=speaker
LIBRESPOT_BACKEND=alsa

# Web Interface
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False

# GPIO Pin
GPIO_PIN=18

# Authentication
WEB_PASSWORD=raspberry123
SECRET_KEY=your-secret-key-change-this

# Demo mode
DEMO_MODE=False
EOF
            print_success "File .env creato"
        fi
    fi
    echo ""
}

# Riepilogo e raccomandazioni
show_summary() {
    print_header "Riepilogo e Raccomandazioni"
    
    echo "Per utilizzare Spotify Connect:"
    echo "1. Assicurati che librespot sia in esecuzione"
    echo "2. Apri l'app Spotify sul tuo telefono/computer"
    echo "3. Riproduci una canzone"
    echo "4. Tocca l'icona 'Dispositivi disponibili'"
    echo "5. Seleziona 'RaspberryPi' (o il nome configurato)"
    echo ""
    
    echo "Comandi utili:"
    echo "- Avvia librespot: ./start_librespot.sh"
    echo "- Ferma librespot: pkill librespot"
    echo "- Test audio: speaker-test -t wav -c 2 -l 1"
    echo "- Verifica processi: ps aux | grep librespot"
    echo ""
    
    print_status "Se il dispositivo non appare ancora in Spotify:"
    echo "1. Riavvia librespot: pkill librespot && ./start_librespot.sh"
    echo "2. Riavvia l'app Spotify"
    echo "3. Verifica di essere sulla stessa rete WiFi"
    echo "4. Controlla il firewall del router"
}

# Funzione principale
main() {
    echo "=== Diagnostica Audio Raspberry Pi Spotify Connect ==="
    echo "Questo script identifica e risolve problemi audio comuni"
    echo ""
    
    test_audio_devices
    test_alsa_config
    test_audio_playback
    test_librespot
    test_network
    test_env_config
    show_summary
    
    print_success "Diagnostica completata!"
}

# Esegui solo se chiamato direttamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi