#!/bin/bash

# Script per configurare l'aggiornamento automatico di Music Hub Pi
# Da eseguire sul Raspberry Pi

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
    echo "  -m, --method METHOD   Metodo di aggiornamento automatico:"
    echo "                        cron    - Usa crontab (default)"
    echo "                        systemd - Usa servizio systemd"
    echo "                        manual  - Solo installazione script"
    echo "  -i, --interval MINS   Intervallo in minuti (default: 60)"
    echo "  -h, --help           Mostra questo aiuto"
    echo ""
    echo "Esempi:"
    echo "  $0                           # Configurazione cron ogni ora"
    echo "  $0 -m systemd               # Servizio systemd"
    echo "  $0 -m cron -i 30            # Cron ogni 30 minuti"
    echo "  $0 -m manual                # Solo installazione script"
}

# Configurazione di default
METHOD="cron"
INTERVAL=60
PROJECT_PATH=$(pwd)

# Parsing parametri
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--method)
            METHOD="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Opzione sconosciuta: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validazione parametri
if [[ "$METHOD" != "cron" && "$METHOD" != "systemd" && "$METHOD" != "manual" ]]; then
    print_error "Metodo non valido: $METHOD"
    echo "Metodi supportati: cron, systemd, manual"
    exit 1
fi

if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || [[ "$INTERVAL" -lt 1 ]]; then
    print_error "Intervallo non valido: $INTERVAL"
    echo "L'intervallo deve essere un numero positivo di minuti"
    exit 1
fi

# Verifica che siamo nella directory corretta
if [[ ! -f "main.py" || ! -f "auto_update.sh" ]]; then
    print_error "Esegui questo script dalla directory del progetto Music Hub Pi"
    print_error "Assicurati che il file auto_update.sh sia presente"
    exit 1
fi

print_header "Configurazione Aggiornamento Automatico Music Hub Pi"
echo "Metodo: $METHOD"
echo "Intervallo: $INTERVAL minuti"
echo "Directory progetto: $PROJECT_PATH"
echo ""

# Chiedi conferma
read -p "Continuare con la configurazione? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Configurazione annullata"
    exit 1
fi

echo ""

# 1. Verifica e rendi eseguibile lo script
print_status "Configurazione script di aggiornamento..."
chmod +x auto_update.sh
print_success "Script auto_update.sh configurato"

# 2. Test dello script
print_status "Test dello script di aggiornamento..."
if ./auto_update.sh --help >/dev/null 2>&1; then
    print_success "Script funzionante"
else
    print_error "Errore nel test dello script"
    exit 1
fi

# 3. Configurazione in base al metodo scelto
case $METHOD in
    "cron")
        print_status "Configurazione crontab..."
        
        # Calcola la configurazione cron
        if [[ $INTERVAL -eq 60 ]]; then
            CRON_TIME="0 * * * *"  # Ogni ora
        elif [[ $INTERVAL -eq 30 ]]; then
            CRON_TIME="0,30 * * * *"  # Ogni 30 minuti
        elif [[ $INTERVAL -eq 15 ]]; then
            CRON_TIME="0,15,30,45 * * * *"  # Ogni 15 minuti
        elif [[ $INTERVAL -lt 60 ]]; then
            CRON_TIME="*/$INTERVAL * * * *"  # Ogni N minuti
        else
            # Per intervalli maggiori di 60 minuti
            HOURS=$((INTERVAL / 60))
            CRON_TIME="0 */$HOURS * * *"
        fi
        
        CRON_COMMAND="cd $PROJECT_PATH && ./auto_update.sh >/dev/null 2>&1"
        
        # Rimuovi eventuali entry esistenti
        crontab -l 2>/dev/null | grep -v "auto_update.sh" | crontab - 2>/dev/null || true
        
        # Aggiungi nuova entry
        (crontab -l 2>/dev/null; echo "$CRON_TIME $CRON_COMMAND") | crontab -
        
        print_success "Crontab configurato: $CRON_TIME"
        print_status "L'aggiornamento automatico verrà eseguito ogni $INTERVAL minuti"
        ;;
        
    "systemd")
        print_status "Configurazione servizio systemd..."
        
        # Verifica che il file di servizio esista
        if [[ ! -f "music-hub-auto-update.service" ]]; then
            print_error "File music-hub-auto-update.service non trovato"
            exit 1
        fi
        
        # Copia il file di servizio
        sudo cp music-hub-auto-update.service /etc/systemd/system/
        
        # Aggiorna il path nel file di servizio
        sudo sed -i "s|/home/pi/music-hub-pi|$PROJECT_PATH|g" /etc/systemd/system/music-hub-auto-update.service
        
        # Ricarica systemd
        sudo systemctl daemon-reload
        
        # Abilita e avvia il servizio
        sudo systemctl enable music-hub-auto-update.service
        sudo systemctl start music-hub-auto-update.service
        
        print_success "Servizio systemd configurato e avviato"
        print_status "Il servizio controllerà gli aggiornamenti ogni ora"
        
        # Mostra stato del servizio
        sleep 2
        if systemctl is-active --quiet music-hub-auto-update.service; then
            print_success "✅ Servizio attivo"
        else
            print_warning "⚠️  Servizio non attivo, controlla i log"
        fi
        ;;
        
    "manual")
        print_status "Installazione solo script..."
        print_success "Script auto_update.sh pronto per l'uso manuale"
        echo ""
        echo "Comandi disponibili:"
        echo "  ./auto_update.sh              # Controllo singolo"
        echo "  ./auto_update.sh --daemon     # Modalità daemon"
        echo "  ./auto_update.sh --force      # Aggiornamento forzato"
        ;;
esac

# 4. Informazioni finali
print_header "Configurazione Completata!"

case $METHOD in
    "cron")
        echo "📅 Aggiornamento automatico configurato con crontab"
        echo "⏰ Intervallo: ogni $INTERVAL minuti"
        echo ""
        echo "Comandi utili:"
        echo "  crontab -l                    # Visualizza crontab"
        echo "  crontab -e                    # Modifica crontab"
        echo "  tail -f /tmp/music-hub-auto-update.log  # Log aggiornamenti"
        ;;
        
    "systemd")
        echo "🔧 Servizio systemd configurato"
        echo "⏰ Controllo automatico ogni ora"
        echo ""
        echo "Comandi utili:"
        echo "  sudo systemctl status music-hub-auto-update   # Stato servizio"
        echo "  sudo systemctl stop music-hub-auto-update     # Ferma servizio"
        echo "  sudo systemctl start music-hub-auto-update    # Avvia servizio"
        echo "  sudo journalctl -u music-hub-auto-update -f   # Log servizio"
        echo "  tail -f /tmp/music-hub-auto-update.log        # Log aggiornamenti"
        ;;
        
    "manual")
        echo "📋 Script installato per uso manuale"
        echo ""
        echo "Per configurare aggiornamenti automatici in seguito:"
        echo "  ./setup_auto_update.sh -m cron     # Usa crontab"
        echo "  ./setup_auto_update.sh -m systemd  # Usa systemd"
        ;;
esac

echo ""
echo "📁 Log aggiornamenti: /tmp/music-hub-auto-update.log"
echo "🔧 Per modificare la configurazione, riesegui questo script"
echo ""
print_success "Tutto pronto! 🚀"

# Test finale
if [[ "$METHOD" != "manual" ]]; then
    echo ""
    print_status "Eseguo un test dell'aggiornamento automatico..."
    if ./auto_update.sh >/dev/null 2>&1; then
        print_success "✅ Test completato con successo"
    else
        print_warning "⚠️  Test fallito, controlla i log per dettagli"
    fi
fi