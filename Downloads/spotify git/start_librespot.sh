#!/bin/bash

# Script per avviare librespot (Spotify Connect) su Raspberry Pi
# Questo script configura il Raspberry Pi come dispositivo Spotify Connect

set -e

# Carica configurazione da .env se esiste
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configurazione librespot
DEVICE_NAME="${LIBRESPOT_NAME:-RaspberryPi}"
BITRATE="${LIBRESPOT_BITRATE:-320}"
DEVICE_TYPE="${LIBRESPOT_DEVICE_TYPE:-speaker}"
BACKEND="${LIBRESPOT_BACKEND:-alsa}"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica se librespot è installato
if ! command -v librespot &> /dev/null; then
    print_error "librespot non è installato!"
    echo "Installa librespot con: cargo install librespot --features alsa-backend"
    echo "Oppure esegui lo script di installazione: ./install.sh"
    exit 1
fi

# Verifica sistema audio
if ! aplay -l &> /dev/null; then
    print_error "Sistema audio non disponibile!"
    echo "Verifica la configurazione audio del Raspberry Pi"
    exit 1
fi

print_status "Avvio Spotify Connect (librespot)..."
print_status "Nome dispositivo: $DEVICE_NAME"
print_status "Bitrate: $BITRATE kbps"
print_status "Backend audio: $BACKEND"

# Avvia librespot
librespot \
    --name "$DEVICE_NAME" \
    --bitrate $BITRATE \
    --device-type $DEVICE_TYPE \
    --backend $BACKEND \
    --mixer softvol \
    --initial-volume 70 \
    --volume-ctrl linear \
    --cache /tmp/librespot-cache \
    --enable-volume-normalisation \
    --normalisation-pregain -10 &

LIBRESPOT_PID=$!

print_success "Spotify Connect avviato (PID: $LIBRESPOT_PID)"
print_status "Il dispositivo '$DEVICE_NAME' dovrebbe ora apparire nell'app Spotify"
print_status "Premi Ctrl+C per fermare"

# Gestione segnali per shutdown pulito
trap 'print_status "Arresto Spotify Connect..."; kill $LIBRESPOT_PID; exit 0' INT TERM

# Attendi che il processo termini
wait $LIBRESPOT_PID