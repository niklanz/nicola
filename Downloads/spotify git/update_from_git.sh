#!/bin/bash

# Script per aggiornare il progetto Spotify Pi da Git
# Da eseguire direttamente sul Raspberry Pi

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

# Funzione di aiuto
show_help() {
    echo "Uso: $0 [OPZIONI]"
    echo ""
    echo "Opzioni:"
    echo "  -h, --help     Mostra questo aiuto"
    echo "  -f, --force    Forza l'aggiornamento (sovrascrive modifiche locali)"
    echo "  -b, --branch   Specifica il branch da utilizzare (default: main)"
    echo "  --no-restart   Non riavvia l'applicazione dopo l'aggiornamento"
    echo ""
    echo "Esempi:"
    echo "  $0                    # Aggiornamento normale"
    echo "  $0 --force           # Forza aggiornamento"
    echo "  $0 -b develop        # Usa branch develop"
    echo "  $0 --no-restart      # Non riavvia l'app"
}

# Parsing parametri
FORCE_UPDATE=false
BRANCH="main"
RESTART_APP=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_UPDATE=true
            shift
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        --no-restart)
            RESTART_APP=false
            shift
            ;;
        *)
            echo "Opzione sconosciuta: $1"
            show_help
            exit 1
            ;;
    esac
done

# Verifica che siamo nella directory corretta
if [[ ! -f "main.py" || ! -f "spotify_manager.py" ]]; then
    print_error "Esegui questo script dalla directory del progetto Spotify Pi"
    exit 1
fi

print_header "Aggiornamento Spotify Pi da Git"
echo "Branch: $BRANCH"
echo "Forza aggiornamento: $FORCE_UPDATE"
echo "Riavvia applicazione: $RESTART_APP"
echo ""

# 1. Verifica connessione internet
print_status "Verifica connessione internet..."
if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    print_error "Connessione internet non disponibile"
    exit 1
fi
print_success "Connessione internet OK"

# 2. Verifica repository Git
print_status "Verifica repository Git..."
if [[ ! -d ".git" ]]; then
    print_error "Questa directory non è un repository Git"
    echo "Per inizializzare:"
    echo "git init"
    echo "git remote add origin <URL_REPOSITORY>"
    echo "git pull origin main"
    exit 1
fi
print_success "Repository Git trovato"

# 3. Backup configurazione
print_status "Backup configurazione..."
cp .env .env.backup 2>/dev/null || print_warning "File .env non trovato"
cp .spotify_cache .spotify_cache.backup 2>/dev/null || print_warning "Cache Spotify non trovata"
print_success "Backup completato"

# 4. Ferma servizi
if [[ "$RESTART_APP" == "true" ]]; then
    print_status "Fermo servizi..."
    
    # Ferma servizio systemd se esiste
    if systemctl is-active --quiet spotify-pi 2>/dev/null; then
        print_status "Fermo servizio systemd..."
        sudo systemctl stop spotify-pi
    fi
    
    # Ferma processi Python
    if pgrep -f "python.*main.py" >/dev/null; then
        print_status "Fermo applicazione Python..."
        pkill -f "python.*main.py" || true
        sleep 2
    fi
    
    # Ferma librespot
    if pgrep librespot >/dev/null; then
        print_status "Fermo librespot..."
        pkill librespot || true
        sleep 1
    fi
    
    print_success "Servizi fermati"
fi

# 5. Aggiornamento Git
print_status "Aggiornamento da Git..."

# Controlla stato repository
if [[ "$FORCE_UPDATE" == "false" ]]; then
    if ! git diff --quiet || ! git diff --cached --quiet; then
        print_error "Ci sono modifiche locali non committate"
        echo "Modifiche trovate:"
        git status --porcelain
        echo ""
        echo "Opzioni:"
        echo "1. Committa le modifiche: git add . && git commit -m 'Local changes'"
        echo "2. Scarta le modifiche: git reset --hard HEAD"
        echo "3. Usa --force per sovrascrivere"
        exit 1
    fi
fi

# Fetch aggiornamenti
print_status "Download aggiornamenti..."
git fetch origin

# Controlla se ci sono aggiornamenti
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [[ "$LOCAL" == "$REMOTE" ]]; then
    print_success "Il progetto è già aggiornato!"
    if [[ "$RESTART_APP" == "true" ]]; then
        print_status "Riavvio applicazione..."
    else
        exit 0
    fi
else
    print_status "Aggiornamenti disponibili, applicazione in corso..."
    
    if [[ "$FORCE_UPDATE" == "true" ]]; then
        git reset --hard origin/$BRANCH
    else
        git pull origin $BRANCH
    fi
    
    # Incrementa versione automaticamente
    if [[ -f "version.py" ]]; then
        python3 version.py --increment 2>/dev/null || print_warning "Errore incremento versione"
        print_status "Versione incrementata automaticamente"
    fi
    
    print_success "Codice aggiornato"
fi

# 6. Ripristina configurazione
print_status "Ripristino configurazione..."
cp .env.backup .env 2>/dev/null || print_warning "Backup .env non trovato"
cp .spotify_cache.backup .spotify_cache 2>/dev/null || print_warning "Backup cache non trovato"
print_success "Configurazione ripristinata"

# 7. Aggiorna dipendenze
print_status "Aggiornamento dipendenze..."
if [[ -d "venv" ]]; then
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    print_success "Dipendenze aggiornate (venv)"
elif [[ -d "spotify_env" ]]; then
    source spotify_env/bin/activate
    pip install -r requirements.txt --quiet
    print_success "Dipendenze aggiornate (spotify_env)"
else
    print_warning "Virtual environment non trovato, uso Python di sistema"
    pip3 install -r requirements.txt --quiet --user 2>/dev/null || print_warning "Errore aggiornamento dipendenze"
fi

# 8. Rendi eseguibili gli script
print_status "Configurazione script..."
chmod +x *.sh 2>/dev/null || true
print_success "Script configurati"

# 9. Riavvia applicazione
if [[ "$RESTART_APP" == "true" ]]; then
    print_status "Riavvio applicazione..."
    
    # Prova prima con systemd
    if systemctl list-unit-files | grep -q spotify-pi; then
        print_status "Avvio tramite systemd..."
        sudo systemctl start spotify-pi
        sleep 3
        
        if systemctl is-active --quiet spotify-pi; then
            print_success "Servizio systemd avviato"
        else
            print_warning "Errore servizio systemd, avvio manuale..."
            nohup python3 main.py > /tmp/spotify-pi.log 2>&1 &
        fi
    else
        print_status "Avvio manuale..."
        nohup python3 main.py > /tmp/spotify-pi.log 2>&1 &
    fi
    
    APP_PID=$!
    print_status "Attendo avvio applicazione..."
    sleep 5
    
    # Verifica avvio
    if pgrep -f "python.*main.py" >/dev/null; then
        print_success "✅ Applicazione avviata con successo!"
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        echo "🌐 Interfaccia web: http://$LOCAL_IP:5000"
        
        # Controlla librespot
        if pgrep librespot >/dev/null; then
            print_success "🎵 Librespot attivo"
        else
            print_warning "⚠️  Librespot non attivo"
            echo "Esegui ./fix_audio_quick.sh per risolvere problemi audio"
        fi
    else
        print_error "❌ Errore nell'avvio dell'applicazione"
        echo "Log errori:"
        tail -10 /tmp/spotify-pi.log 2>/dev/null || echo "Nessun log disponibile"
        exit 1
    fi
fi

print_header "Aggiornamento Completato!"
echo "📋 Riepilogo:"
echo "   - Codice aggiornato dal branch: $BRANCH"
echo "   - Configurazione preservata"
echo "   - Dipendenze aggiornate"
if [[ "$RESTART_APP" == "true" ]]; then
    echo "   - Applicazione riavviata"
fi
echo ""
echo "🔧 Comandi utili:"
echo "   ./diagnose_audio.sh          # Diagnostica audio"
echo "   ./fix_audio_quick.sh         # Fix rapido audio"
echo "   tail -f /tmp/spotify-pi.log  # Visualizza log"
echo "   systemctl status spotify-pi  # Stato servizio"
echo ""
print_success "Tutto pronto! 🚀"