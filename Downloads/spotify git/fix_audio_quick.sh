#!/bin/bash

# Script di riparazione rapida audio per Raspberry Pi Spotify Connect
# Risolve automaticamente i problemi più comuni

set -e

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${YELLOW}[FIX]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=== Fix Rapido Audio Raspberry Pi ==="
echo "Questo script risolve automaticamente i problemi audio più comuni"
echo ""

# 1. Ferma processi librespot esistenti
print_status "Fermo processi librespot esistenti..."
pkill librespot 2>/dev/null || true
sleep 2
print_success "Processi librespot fermati"

# 2. Configura output audio su jack 3.5mm
print_status "Configuro output audio su jack 3.5mm..."
sudo amixer cset numid=3 1 >/dev/null 2>&1 || true
print_success "Output audio configurato"

# 3. Imposta volume al 70%
print_status "Imposto volume al 70%..."
amixer sset Master 70% >/dev/null 2>&1 || true
print_success "Volume impostato"

# 4. Ricarica moduli audio
print_status "Ricarico moduli audio..."
sudo modprobe -r snd_bcm2835 2>/dev/null || true
sudo modprobe snd_bcm2835 2>/dev/null || true
print_success "Moduli audio ricaricati"

# 5. Crea/aggiorna configurazione ALSA
print_status "Configuro ALSA..."
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
print_success "Configurazione ALSA aggiornata"

# 6. Test audio
print_status "Testo audio..."
if timeout 2s speaker-test -t wav -c 2 >/dev/null 2>&1; then
    print_success "Audio funzionante!"
else
    print_error "Audio ancora non funzionante - verifica connessioni hardware"
fi

# 7. Avvia librespot
print_status "Avvio librespot..."

# Carica configurazione da .env se esiste
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs) 2>/dev/null || true
fi

# Usa valori di default se non configurati
DEVICE_NAME="${LIBRESPOT_NAME:-RaspberryPi}"
BITRATE="${LIBRESPOT_BITRATE:-320}"
DEVICE_TYPE="${LIBRESPOT_DEVICE_TYPE:-speaker}"
BACKEND="${LIBRESPOT_BACKEND:-alsa}"

# Verifica se librespot è installato
if ! command -v librespot >/dev/null 2>&1; then
    print_error "Librespot non installato!"
    echo "Installa librespot con: cargo install librespot --features alsa-backend"
    echo "Oppure esegui: ./install.sh"
    exit 1
fi

# Avvia librespot in background
nohup librespot \
    --name "$DEVICE_NAME" \
    --bitrate $BITRATE \
    --device-type $DEVICE_TYPE \
    --backend $BACKEND \
    --mixer softvol \
    --initial-volume 70 \
    --volume-ctrl linear \
    --cache /tmp/librespot-cache \
    --enable-volume-normalisation \
    --normalisation-pregain -10 > /tmp/librespot.log 2>&1 &

# Attendi che librespot si avvii
sleep 3

# Verifica se librespot è in esecuzione
if pgrep librespot >/dev/null; then
    print_success "Librespot avviato con successo!"
    echo "Nome dispositivo: $DEVICE_NAME"
    echo "Il dispositivo dovrebbe ora apparire nell'app Spotify"
else
    print_error "Errore nell'avvio di librespot"
    echo "Log errori:"
    tail -10 /tmp/librespot.log 2>/dev/null || echo "Nessun log disponibile"
    exit 1
fi

echo ""
echo "=== ISTRUZIONI ==="
echo "1. Apri l'app Spotify sul tuo telefono/computer"
echo "2. Riproduci una canzone"
echo "3. Tocca l'icona 'Dispositivi disponibili' (speaker/cast)"
echo "4. Seleziona '$DEVICE_NAME' dalla lista"
echo ""
echo "Se il dispositivo non appare:"
echo "- Assicurati di essere sulla stessa rete WiFi"
echo "- Riavvia l'app Spotify"
echo "- Esegui: ./diagnose_audio.sh per diagnostica completa"
echo ""
print_success "Fix completato!"