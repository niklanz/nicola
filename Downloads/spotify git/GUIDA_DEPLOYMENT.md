# Guida: Sincronizzazione e Deployment su Raspberry Pi

## Panoramica
Questa guida spiega come sincronizzare la versione locale (GitHub) con quella presente sul Raspberry Pi.

## Metodi di Sincronizzazione

### Metodo 1: Git Pull (Raccomandato)

#### Sul Raspberry Pi:
```bash
# Naviga nella directory del progetto
cd /path/to/spotify-pi-project

# Ferma l'applicazione se in esecuzione
sudo systemctl stop spotify-pi 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill librespot 2>/dev/null || true

# Backup della configurazione attuale
cp .env .env.backup

# Aggiorna dal repository
git fetch origin
git pull origin main

# Ripristina la configurazione
cp .env.backup .env

# Installa nuove dipendenze (se necessarie)
source venv/bin/activate
pip install -r requirements.txt

# Riavvia l'applicazione
python main.py
# Oppure se usi systemd:
# sudo systemctl start spotify-pi
```

### Metodo 2: Script di Deployment Automatico

Ho creato degli script che automatizzano tutto il processo di sincronizzazione.

#### Script per Computer Locale (`deploy_to_raspberry.sh`)

Questo script sincronizza il progetto dal tuo computer locale al Raspberry Pi:
```bash
# Uso dello script di deployment
./deploy_to_raspberry.sh [IP] [USER] [PATH]

# Esempi:
./deploy_to_raspberry.sh                                    # Usa valori di default
./deploy_to_raspberry.sh 192.168.1.50                      # IP personalizzato
./deploy_to_raspberry.sh 192.168.1.50 pi /opt/spotify-pi   # Tutti i parametri

**Caratteristiche dello script:**
- ✅ Verifica automatica della connessione
- 💾 Backup automatico della configurazione
- 🔄 Sincronizzazione intelligente con `rsync`
- 🚀 Riavvio automatico dell'applicazione
- 📊 Output colorato e informativo
- ⚠️ Gestione errori completa
```

### Metodo 3: SCP per File Singoli

```bash
# Copia file specifici
scp main.py pi@192.168.1.100:/home/pi/spotify-pi/
scp spotify_manager.py pi@192.168.1.100:/home/pi/spotify-pi/
scp web_interface.py pi@192.168.1.100:/home/pi/spotify-pi/

# Copia directory
scp -r templates/ pi@192.168.1.100:/home/pi/spotify-pi/
scp -r static/ pi@192.168.1.100:/home/pi/spotify-pi/
```

## Script di Sincronizzazione Completa

### Per il Computer Locale (deploy_to_raspberry.sh):
```bash
#!/bin/bash

# Configurazione
RASPBERRY_IP="${1:-192.168.1.100}"
RASPBERRY_USER="${2:-pi}"
PROJECT_PATH="${3:-/home/pi/spotify-pi}"

echo "=== Deployment su Raspberry Pi ==="
echo "IP: $RASPBERRY_IP"
echo "User: $RASPBERRY_USER"
echo "Path: $PROJECT_PATH"
echo ""

# Verifica connessione
if ! ping -c 1 $RASPBERRY_IP >/dev/null 2>&1; then
    echo "ERRORE: Raspberry Pi non raggiungibile su $RASPBERRY_IP"
    exit 1
fi

# Backup remoto
echo "Backup configurazione remota..."
ssh $RASPBERRY_USER@$RASPBERRY_IP "cd $PROJECT_PATH && cp .env .env.backup 2>/dev/null || true"

# Ferma servizi
echo "Fermo servizi sul Raspberry..."
ssh $RASPBERRY_USER@$RASPBERRY_IP << EOF
cd $PROJECT_PATH
sudo systemctl stop spotify-pi 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill librespot 2>/dev/null || true
sleep 2
EOF

# Sincronizza file
echo "Sincronizzazione file..."
rsync -avz --progress \
      --exclude='.git' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.env' \
      --exclude='venv' \
      --exclude='spotify_env' \
      --exclude='spotify-env' \
      --exclude='*.log' \
      --exclude='.spotify_cache' \
      ./ $RASPBERRY_USER@$RASPBERRY_IP:$PROJECT_PATH/

# Ripristina configurazione e riavvia
echo "Riavvio servizi..."
ssh $RASPBERRY_USER@$RASPBERRY_IP << EOF
cd $PROJECT_PATH

# Ripristina configurazione
cp .env.backup .env 2>/dev/null || true

# Rendi eseguibili gli script
chmod +x *.sh

# Aggiorna dipendenze
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Riavvia applicazione
echo "Riavvio applicazione..."
nohup python main.py > /tmp/spotify-pi.log 2>&1 &

# Attendi avvio
sleep 3

# Verifica stato
if pgrep -f "python.*main.py" >/dev/null; then
    echo "Applicazione avviata con successo!"
else
    echo "ERRORE: Applicazione non avviata"
    echo "Log errori:"
    tail -10 /tmp/spotify-pi.log
fi
EOF

echo ""
echo "=== Deployment Completato ==="
echo "Applicazione disponibile su: http://$RASPBERRY_IP:5000"
```

#### Script per Raspberry Pi (`update_from_git.sh`)

Questo script va eseguito direttamente sul Raspberry Pi per aggiornare da Git:
```bash
# Uso dello script di aggiornamento
./update_from_git.sh [OPZIONI]

# Esempi:
./update_from_git.sh                    # Aggiornamento normale
./update_from_git.sh --force           # Forza aggiornamento
./update_from_git.sh -b develop        # Usa branch develop
./update_from_git.sh --no-restart      # Non riavvia l'app

**Opzioni disponibili:**
- `-f, --force`: Forza l'aggiornamento (sovrascrive modifiche locali)
- `-b, --branch`: Specifica il branch da utilizzare (default: main)
- `--no-restart`: Non riavvia l'applicazione dopo l'aggiornamento
- `-h, --help`: Mostra l'aiuto

**Caratteristiche dello script:**
- 🔍 Verifica automatica delle modifiche locali
- 💾 Backup e ripristino della configurazione
- 📦 Aggiornamento automatico delle dipendenze
- 🔄 Gestione intelligente dei servizi
- ⚠️ Controllo errori e validazioni
```

## Configurazione SSH (Opzionale)

Per evitare di inserire la password ogni volta:

```bash
# Sul computer locale
ssh-keygen -t rsa -b 4096
ssh-copy-id pi@192.168.1.100

# Test connessione
ssh pi@192.168.1.100 "echo 'Connessione SSH OK'"
```

## Workflow Raccomandato

### Per Sviluppo Attivo:
1. **Lavora in locale** sul tuo computer
2. **Committa** le modifiche su GitHub
3. **Esegui** `./deploy_to_raspberry.sh` per sincronizzazione completa

### Per Aggiornamenti Occasionali:
1. **SSH** sul Raspberry Pi: `ssh pi@192.168.1.100`
2. **Esegui** `./update_from_git.sh` per aggiornamento da Git

### Per Aggiornamenti Forzati:
1. **Sul Raspberry Pi**: `./update_from_git.sh --force`
2. **Dal computer locale**: `./deploy_to_raspberry.sh` (sovrascrive sempre)

### Per Modifiche Rapide:
1. **Modifica** file specifici in locale
2. **Usa SCP** per trasferire singoli file
3. **Riavvia** manualmente l'applicazione

## Risoluzione Problemi

### Conflitti Git:
```bash
# Sul Raspberry Pi
git stash  # Salva modifiche locali
git pull origin main
git stash pop  # Ripristina modifiche se necessario
```

### Permessi File:
```bash
# Sul Raspberry Pi
chmod +x *.sh
chown -R pi:pi /home/pi/spotify-pi
```

### Verifica Stato:
```bash
# Sul Raspberry Pi
ps aux | grep python  # Verifica processo Python
ps aux | grep librespot  # Verifica processo librespot
sudo systemctl status spotify-pi  # Se usi systemd
tail -f /tmp/spotify-pi.log  # Log applicazione
```

## Note Importanti

1. **Backup sempre il file .env** prima degli aggiornamenti
2. **Non committare mai** file sensibili (.env, .spotify_cache)
3. **Testa sempre** dopo il deployment
4. **Usa branch separati** per sviluppo e produzione se necessario
5. **Monitora i log** per errori dopo il deployment

## Automazione con Cron (Opzionale)

Per aggiornamenti automatici:

```bash
# Sul Raspberry Pi
crontab -e

# Aggiungi (aggiornamento ogni notte alle 2:00)
0 2 * * * cd /home/pi/spotify-pi && ./update_from_git.sh >> /tmp/auto-update.log 2>&1
```