#!/bin/bash

# Script per aggiornamento automatico del progetto Music Hub Pi
# Può essere eseguito come cron job per aggiornamenti automatici

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurazione
LOG_FILE="/tmp/music-hub-auto-update.log"
MAX_LOG_SIZE=1048576  # 1MB
CHECK_INTERVAL=3600   # 1 ora in secondi
BRANCH="main"
FORCE_UPDATE=false

# Funzioni di logging
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log_message "[INFO] $1"
}

log_success() {
    log_message "[SUCCESS] $1"
}

log_warning() {
    log_message "[WARNING] $1"
}

log_error() {
    log_message "[ERROR] $1"
}

# Gestione dimensione log
rotate_log() {
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        touch "$LOG_FILE"
        log_info "Log ruotato per dimensione"
    fi
}

# Verifica se siamo nella directory corretta
check_project_directory() {
    if [[ ! -f "main.py" || ! -f "spotify_manager.py" ]]; then
        log_error "Directory del progetto non trovata o non valida"
        return 1
    fi
    return 0
}

# Verifica connessione internet
check_internet() {
    if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        log_warning "Connessione internet non disponibile"
        return 1
    fi
    return 0
}

# Verifica se ci sono aggiornamenti disponibili
check_for_updates() {
    log_info "Controllo aggiornamenti disponibili..."
    
    # Fetch aggiornamenti
    if ! git fetch origin >/dev/null 2>&1; then
        log_error "Errore nel fetch da Git"
        return 1
    fi
    
    # Confronta versioni
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/$BRANCH)
    
    if [[ "$LOCAL" == "$REMOTE" ]]; then
        log_info "Nessun aggiornamento disponibile"
        return 1
    else
        log_info "Aggiornamenti disponibili: $LOCAL -> $REMOTE"
        return 0
    fi
}

# Esegue l'aggiornamento
perform_update() {
    log_info "Inizio aggiornamento automatico..."
    
    # Backup configurazione
    cp .env .env.auto-backup 2>/dev/null || log_warning "File .env non trovato"
    cp .spotify_cache .spotify_cache.auto-backup 2>/dev/null || log_warning "Cache Spotify non trovata"
    
    # Ferma servizi
    log_info "Fermo servizi..."
    if systemctl is-active --quiet spotify-pi 2>/dev/null; then
        sudo systemctl stop spotify-pi
        log_info "Servizio systemd fermato"
    fi
    
    if pgrep -f "python.*main.py" >/dev/null; then
        pkill -f "python.*main.py" || true
        sleep 2
        log_info "Processi Python fermati"
    fi
    
    if pgrep librespot >/dev/null; then
        pkill librespot || true
        sleep 1
        log_info "Librespot fermato"
    fi
    
    # Aggiorna codice
    if [[ "$FORCE_UPDATE" == "true" ]]; then
        git reset --hard origin/$BRANCH
        log_info "Aggiornamento forzato completato"
    else
        if ! git pull origin $BRANCH; then
            log_error "Errore durante git pull"
            return 1
        fi
        log_info "Aggiornamento Git completato"
    fi
    
    # Ripristina configurazione
    cp .env.auto-backup .env 2>/dev/null || log_warning "Backup .env non ripristinato"
    cp .spotify_cache.auto-backup .spotify_cache 2>/dev/null || log_warning "Backup cache non ripristinato"
    
    # Aggiorna dipendenze
    log_info "Aggiornamento dipendenze..."
    if [[ -d "venv" ]]; then
        source venv/bin/activate
        pip install -r requirements.txt --quiet
        log_info "Dipendenze aggiornate (venv)"
    elif [[ -d "spotify_env" ]]; then
        source spotify_env/bin/activate
        pip install -r requirements.txt --quiet
        log_info "Dipendenze aggiornate (spotify_env)"
    else
        pip3 install -r requirements.txt --quiet --user 2>/dev/null || log_warning "Errore aggiornamento dipendenze"
    fi
    
    # Rendi eseguibili gli script
    chmod +x *.sh 2>/dev/null || true
    
    # Riavvia applicazione
    log_info "Riavvio applicazione..."
    if systemctl list-unit-files | grep -q spotify-pi; then
        sudo systemctl start spotify-pi
        sleep 3
        if systemctl is-active --quiet spotify-pi; then
            log_success "Servizio systemd riavviato"
        else
            log_warning "Errore servizio systemd, avvio manuale..."
            nohup python3 main.py > /tmp/music-hub-pi.log 2>&1 &
        fi
    else
        nohup python3 main.py > /tmp/music-hub-pi.log 2>&1 &
        log_info "Applicazione avviata manualmente"
    fi
    
    sleep 5
    
    # Verifica avvio
    if pgrep -f "python.*main.py" >/dev/null; then
        log_success "✅ Aggiornamento automatico completato con successo!"
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        log_info "🌐 Interfaccia web: http://$LOCAL_IP:5000"
        return 0
    else
        log_error "❌ Errore nell'avvio dell'applicazione dopo aggiornamento"
        return 1
    fi
}

# Funzione principale
main() {
    rotate_log
    log_info "=== Avvio controllo aggiornamenti automatici ==="
    
    # Verifica directory progetto
    if ! check_project_directory; then
        exit 1
    fi
    
    # Verifica connessione internet
    if ! check_internet; then
        log_warning "Salto controllo aggiornamenti per mancanza di connessione"
        exit 0
    fi
    
    # Verifica repository Git
    if [[ ! -d ".git" ]]; then
        log_error "Directory non è un repository Git"
        exit 1
    fi
    
    # Controlla aggiornamenti
    if check_for_updates; then
        log_info "Aggiornamenti trovati, procedo con l'installazione..."
        if perform_update; then
            log_success "Aggiornamento automatico completato"
        else
            log_error "Errore durante l'aggiornamento automatico"
            exit 1
        fi
    else
        log_info "Nessun aggiornamento necessario"
    fi
    
    log_info "=== Fine controllo aggiornamenti automatici ==="
}

# Parsing parametri
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_UPDATE=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --daemon)
            # Modalità daemon - esegue controlli periodici
            log_info "Avvio in modalità daemon (controllo ogni $CHECK_INTERVAL secondi)"
            while true; do
                main
                sleep $CHECK_INTERVAL
            done
            ;;
        --help)
            echo "Uso: $0 [OPZIONI]"
            echo ""
            echo "Opzioni:"
            echo "  --force     Forza l'aggiornamento"
            echo "  --branch    Specifica il branch (default: main)"
            echo "  --daemon    Esegue controlli periodici"
            echo "  --help      Mostra questo aiuto"
            echo ""
            echo "Per configurare aggiornamenti automatici:"
            echo "  # Aggiungi a crontab per controllo ogni ora:"
            echo "  0 * * * * cd /path/to/project && ./auto_update.sh"
            echo ""
            echo "  # Oppure avvia come daemon:"
            echo "  ./auto_update.sh --daemon"
            exit 0
            ;;
        *)
            echo "Opzione sconosciuta: $1"
            echo "Usa --help per vedere le opzioni disponibili"
            exit 1
            ;;
    esac
done

# Esegui controllo singolo se non in modalità daemon
main