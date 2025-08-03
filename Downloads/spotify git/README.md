# Spotify Raspberry Pi Controller

Un'applicazione completa per controllare Spotify su Raspberry Pi tramite input GPIO e interfaccia web. Il sistema è progettato per funzionare in modo completamente autonomo, senza display, utilizzando solo la connessione internet e l'uscita audio jack.

## 🎵 Caratteristiche

- **Controllo GPIO**: Avvia/ferma la musica tramite input su pin GPIO
- **Interfaccia Web**: Controllo completo tramite browser web
- **Spotify Connect**: Integrazione nativa con Spotify
- **Controlli Completi**: Play/Pause, Next/Previous, Volume, Playlist
- **Gestione Dispositivi**: Selezione e controllo dispositivi Spotify
- **Ricerca Musica**: Cerca e riproduci brani direttamente
- **Monitoraggio Sistema**: Stato in tempo reale di tutti i componenti
- **Avvio Automatico**: Servizio systemd per l'avvio automatico

## 🛠️ Requisiti

### Hardware
- Raspberry Pi (qualsiasi modello con GPIO)
- Scheda microSD (minimo 8GB)
- Alimentatore per Raspberry Pi
- Cavo audio jack (per collegare altoparlanti/cuffie)
- Connessione internet (WiFi o Ethernet)
- Pulsante o sensore per input GPIO (opzionale)

### Software
- Raspberry Pi OS (Lite o Desktop)
- Account Spotify Premium
- App Spotify Developer (per credenziali API)

## 🚀 Installazione Rapida

### 1. Preparazione

```bash
# Clona o scarica il progetto
git clone <repository-url>
cd spotify-raspberry-pi-controller

# Rendi eseguibile lo script di installazione
chmod +x install.sh
```

### 2. Installazione Automatica

```bash
# Esegui lo script di installazione
./install.sh
```

Lo script installerà automaticamente:
- Dipendenze di sistema
- Python e librerie necessarie
- Configurazione audio
- Spotify Connect (librespot)
- Servizio systemd

### 3. Configurazione Spotify

1. Vai su [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Crea una nuova app
3. Copia `Client ID` e `Client Secret`
4. Imposta Redirect URI: `http://localhost:8888/callback`
5. Modifica il file `.env`:

```bash
nano .env
```

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

GPIO_PIN=18
WEB_PORT=5000
WEB_HOST=0.0.0.0

DEFAULT_DEVICE_NAME=raspberrypi
DEFAULT_PLAYLIST_URI=spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
VOLUME_LEVEL=70
```

## 🎮 Utilizzo

### Avvio Manuale

```bash
# Avvia Spotify Connect
./start_librespot.sh &

# Avvia l'applicazione principale
python main.py
```

### Avvio Automatico

```bash
# Abilita il servizio per l'avvio automatico
sudo systemctl enable spotify-pi

# Avvia il servizio
sudo systemctl start spotify-pi

# Controlla lo stato
sudo systemctl status spotify-pi
```

### Accesso all'Interfaccia Web

1. Trova l'IP del Raspberry Pi:
   ```bash
   hostname -I
   ```

2. Apri il browser e vai a: `http://IP_RASPBERRY:5000`

## 🔧 Configurazione GPIO

### Schema di Collegamento

```
Raspberry Pi GPIO:

Pin Fisico | GPIO | Funzione
-----------|------|----------
12         | 18   | Input (default)
GND        | GND  | Ground
```

### Collegamento Pulsante

```
Pulsante -----> GPIO 18 (Pin 12)
     |
     +-------> GND (Pin 6)
```

### Configurazione Pin

- **Pin di Default**: GPIO 18
- **Modalità**: Input con pull-down
- **Trigger**: Fronte di salita (LOW → HIGH)
- **Debounce**: 500ms (configurabile)

Puoi cambiare il pin tramite:
- File `.env`: `GPIO_PIN=XX`
- Interfaccia web: Sezione "Controllo GPIO"

## 🔐 Autenticazione

L'interfaccia web è protetta da un sistema di autenticazione con password.

### Configurazione Password

- **Password predefinita**: `raspberry123`
- **Configurazione**: Modifica `WEB_PASSWORD` nel file `.env`
- **Chiave di sessione**: Configura `SECRET_KEY` per la sicurezza delle sessioni

```env
# Autenticazione
WEB_PASSWORD=raspberry123
SECRET_KEY=your-secret-key-change-this-in-production
```

### Accesso

1. Apri l'interfaccia web nel browser
2. Inserisci la password configurata
3. Clicca "Login" per accedere
4. Usa il pulsante "Logout" per disconnetterti

**⚠️ Importante**: Cambia la password predefinita in produzione per motivi di sicurezza.

## 🌐 Interfaccia Web

### Funzionalità Principali

1. **Controlli Spotify**
   - Play/Pause/Stop
   - Traccia precedente/successiva
   - Controllo volume
   - Visualizzazione traccia corrente

2. **Gestione Dispositivi**
   - Lista dispositivi disponibili
   - Selezione dispositivo attivo
   - Stato connessione

3. **Playlist e Ricerca**
   - Visualizzazione playlist utente
   - Ricerca brani/artisti/album
   - Riproduzione diretta

4. **Controllo GPIO**
   - Stato pin in tempo reale
   - Cambio pin di monitoraggio
   - Attivazione/disattivazione monitoraggio

5. **Stato Sistema**
   - Connessione Spotify
   - Stato GPIO
   - Ultima attività

## 📁 Struttura del Progetto

```
spotify-raspberry-pi-controller/
├── main.py                 # Applicazione principale
├── spotify_manager.py      # Gestione API Spotify
├── gpio_manager.py         # Gestione GPIO
├── web_interface.py        # Interfaccia web Flask
├── requirements.txt        # Dipendenze Python
├── .env.example           # Template configurazione
├── install.sh             # Script installazione
├── start_librespot.sh     # Script Spotify Connect
├── templates/
│   ├── base.html          # Template base
│   └── index.html         # Pagina principale
└── README.md              # Questo file
```

## 🔧 Configurazione Avanzata

### Personalizzazione Audio

```bash
# Test audio
speaker-test -t wav

# Regola volume ALSA
alsamixer

# Lista dispositivi audio
aplay -l
```

### Configurazione librespot

Modifica `start_librespot.sh` per personalizzare:

```bash
DEVICE_NAME="Il Mio Raspberry"  # Nome dispositivo
BITRATE="320"                   # Qualità audio (96/160/320)
DEVICE_TYPE="speaker"           # Tipo dispositivo
```

### Log e Debug

```bash
# Log applicazione
tail -f spotify_pi.log

# Log servizio systemd
sudo journalctl -u spotify-pi -f

# Debug GPIO
gpio readall  # Se installato wiringpi
```

## 🐛 Risoluzione Problemi

### Problemi Comuni

1. **Spotify non si connette**
   - Verifica credenziali in `.env`
   - Controlla connessione internet
   - Riavvia librespot

2. **GPIO non funziona**
   - Verifica collegamenti hardware
   - Controlla permessi GPIO
   - Verifica pin configurato

3. **Audio non funziona**
   - Testa con `speaker-test`
   - Verifica configurazione ALSA
   - Controlla volume

4. **Interfaccia web non accessibile**
   - Verifica IP Raspberry Pi
   - Controlla firewall
   - Verifica porta (default: 5000)

### Comandi Utili

```bash
# Riavvia servizio
sudo systemctl restart spotify-pi

# Controlla stato
sudo systemctl status spotify-pi

# Ferma servizio
sudo systemctl stop spotify-pi

# Disabilita avvio automatico
sudo systemctl disable spotify-pi
```

## 🔒 Sicurezza

- Le credenziali Spotify sono memorizzate localmente
- L'interfaccia web è accessibile solo sulla rete locale
- Nessun dato sensibile viene trasmesso
- Cache token Spotify in `.spotify_cache`

## 📝 API Endpoints

### Controlli Spotify
- `POST /api/play` - Avvia riproduzione
- `POST /api/pause` - Pausa riproduzione
- `POST /api/toggle` - Alterna play/pausa
- `POST /api/next` - Traccia successiva
- `POST /api/previous` - Traccia precedente
- `POST /api/volume` - Imposta volume

### Informazioni
- `GET /api/status` - Stato sistema
- `GET /api/devices` - Dispositivi disponibili
- `GET /api/playlists` - Playlist utente
- `GET /api/search?q=query` - Ricerca brani

### GPIO
- `GET /api/gpio/status` - Stato GPIO
- `POST /api/gpio/set_pin` - Cambia pin
- `POST /api/gpio/toggle_monitoring` - Toggle monitoraggio

## 🤝 Contributi

I contributi sono benvenuti! Per contribuire:

1. Fork del repository
2. Crea un branch per la feature
3. Commit delle modifiche
4. Push del branch
5. Apri una Pull Request

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Vedi il file LICENSE per i dettagli.

## 🙏 Ringraziamenti

- [Spotipy](https://spotipy.readthedocs.io/) - Libreria Python per Spotify API
- [librespot](https://github.com/librespot-org/librespot) - Client Spotify Connect open source
- [Flask](https://flask.palletsprojects.com/) - Framework web Python
- [Bootstrap](https://getbootstrap.com/) - Framework CSS

## 📞 Supporto

Per problemi o domande:

1. Controlla la sezione "Risoluzione Problemi"
2. Verifica i log dell'applicazione
3. Apri una issue su GitHub

---

**Buon ascolto! 🎵**