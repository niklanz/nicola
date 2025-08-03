from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
import os
import logging
import json
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from spotify_manager import SpotifyManager
from gpio_manager import GPIOManager
from werkzeug.utils import secure_filename
from version import get_version_info

# Carica le variabili d'ambiente prima di tutto
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-this')
app.logger.setLevel(logging.INFO)

@app.context_processor
def inject_version():
    """Rende le informazioni sulla versione disponibili in tutti i template"""
    return get_version_info()

# Password per l'accesso web
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'admin')

# Configurazione upload logo
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crea la cartella uploads se non esiste
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """Decoratore per richiedere l'autenticazione"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Variabili globali per i manager
spotify_manager = None
gpio_manager = None
system_status = {
    'spotify_connected': False,
    'gpio_monitoring': False,
    'gpio_status': False,
    'gpio_pin': 'N/A',
    'last_activity': None,
    'current_track': None
}

def init_managers():
    """Inizializza i manager Spotify e GPIO"""
    global spotify_manager, gpio_manager
    
    try:
        spotify_manager = SpotifyManager()
        system_status['spotify_connected'] = True
        logging.info("Spotify Manager inizializzato")
    except Exception as e:
        logging.error(f"Errore inizializzazione Spotify: {e}")
        system_status['spotify_connected'] = False
        
    try:
        gpio_manager = GPIOManager(spotify_manager)
        gpio_manager.start_monitoring()
        system_status['gpio_monitoring'] = True
        system_status['gpio_status'] = gpio_manager.get_pin_state()
        system_status['gpio_pin'] = gpio_manager.gpio_pin
        logging.info("GPIO Manager inizializzato")
    except Exception as e:
        logging.error(f"Errore inizializzazione GPIO: {e}")
        system_status['gpio_monitoring'] = False
        system_status['gpio_status'] = False
        system_status['gpio_pin'] = 'N/A'

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Pagina di login"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == WEB_PASSWORD:
            session['authenticated'] = True
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Password errata!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.pop('authenticated', None)
    flash('Logout effettuato con successo!', 'info')
    return redirect(url_for('login'))

@app.route('/callback')
def spotify_callback():
    """Callback per l'autenticazione Spotify"""
    try:
        code = request.args.get('code')
        if not code:
            return "Errore: Codice di autorizzazione mancante", 400
        
        # Se abbiamo un spotify_manager, proviamo a completare l'autenticazione
        if spotify_manager and hasattr(spotify_manager, 'sp_oauth'):
            token_info = spotify_manager.sp_oauth.get_access_token(code)
            if token_info:
                return "<h1>Autenticazione Spotify completata!</h1><p>Puoi chiudere questa finestra e tornare all'applicazione.</p>"
            else:
                return "Errore nell'ottenimento del token di accesso", 500
        else:
            return "Errore: Manager Spotify non disponibile", 500
            
    except Exception as e:
        app.logger.error(f"Errore nel callback Spotify: {e}")
        return f"Errore nell'autenticazione: {str(e)}", 500

@app.route('/')
@login_required
def index():
    """Pagina principale"""
    update_system_status()
    return render_template('index.html', status=system_status)

@app.route('/api/status')
@login_required
def api_status():
    """API per ottenere lo stato del sistema"""
    update_system_status()
    return jsonify(system_status)

@app.route('/api/play', methods=['POST'])
@login_required
def api_play():
    """API per avviare la riproduzione"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    playlist_uri = request.json.get('playlist_uri') if request.json else None
    success = spotify_manager.play_music(playlist_uri)
    
    return jsonify({
        'success': success,
        'message': 'Riproduzione avviata' if success else 'Errore nell\'avvio'
    })

@app.route('/api/pause', methods=['POST'])
@login_required
def api_pause():
    """API per mettere in pausa"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    success = spotify_manager.pause_music()
    return jsonify({
        'success': success,
        'message': 'Riproduzione in pausa' if success else 'Errore nella pausa'
    })

@app.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    """API per fermare la riproduzione"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    success = spotify_manager.stop_music()
    return jsonify({
        'success': success,
        'message': 'Riproduzione fermata' if success else 'Errore nello stop'
    })

@app.route('/api/toggle', methods=['POST'])
@login_required
def api_toggle():
    """API per alternare play/pausa"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    success = spotify_manager.toggle_playback()
    return jsonify({
        'success': success,
        'message': 'Stato riproduzione cambiato' if success else 'Errore nel cambio stato'
    })

@app.route('/api/next', methods=['POST'])
@login_required
def api_next():
    """API per traccia successiva"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    success = spotify_manager.next_track()
    return jsonify({
        'success': success,
        'message': 'Traccia successiva' if success else 'Errore nel passaggio'
    })

@app.route('/api/previous', methods=['POST'])
@login_required
def api_previous():
    """API per traccia precedente"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    success = spotify_manager.previous_track()
    return jsonify({
        'success': success,
        'message': 'Traccia precedente' if success else 'Errore nel passaggio'
    })

@app.route('/api/volume', methods=['POST'])
@login_required
def api_volume():
    """API per impostare il volume"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    try:
        volume = int(request.json.get('volume', 50))
        success = spotify_manager.set_volume(volume)
        return jsonify({
            'success': success,
            'message': f'Volume impostato a {volume}%' if success else 'Errore nell\'impostazione volume'
        })
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Volume non valido'})

@app.route('/api/devices')
@login_required
def api_devices():
    """API per ottenere i dispositivi disponibili"""
    if not spotify_manager:
        return jsonify({'devices': [], 'error': 'Spotify non connesso'})
        
    devices = spotify_manager.get_devices()
    return jsonify({'devices': devices})

@app.route('/api/set_device', methods=['POST'])
@login_required
def api_set_device():
    """API per impostare il dispositivo attivo"""
    if not spotify_manager:
        return jsonify({'success': False, 'error': 'Spotify non connesso'})
        
    device_id = request.json.get('device_id')
    if not device_id:
        return jsonify({'success': False, 'error': 'ID dispositivo mancante'})
        
    spotify_manager.set_device(device_id)
    return jsonify({'success': True, 'message': 'Dispositivo impostato'})

@app.route('/api/playlists')
@login_required
def api_playlists():
    """API per ottenere le playlist dell'utente"""
    if not spotify_manager:
        return jsonify({'playlists': [], 'error': 'Spotify non connesso'})
        
    playlists = spotify_manager.get_user_playlists()
    return jsonify({'playlists': playlists})

@app.route('/api/search')
@login_required
def api_search():
    """API per cercare tracce"""
    if not spotify_manager:
        return jsonify({'tracks': [], 'error': 'Spotify non connesso'})
        
    query = request.args.get('q', '')
    if not query:
        return jsonify({'tracks': [], 'error': 'Query di ricerca mancante'})
        
    tracks = spotify_manager.search_tracks(query)
    return jsonify({'tracks': tracks})

@app.route('/api/gpio/status')
@login_required
def api_gpio_status():
    """API per ottenere lo stato del GPIO"""
    if not gpio_manager:
        return jsonify({'error': 'GPIO non inizializzato'})
        
    return jsonify({
        'pin': gpio_manager.gpio_pin,
        'state': gpio_manager.get_pin_state(),
        'monitoring': gpio_manager.is_monitoring,
        'debounce_time': gpio_manager.debounce_time
    })

@app.route('/api/gpio/set_pin', methods=['POST'])
@login_required
def api_gpio_set_pin():
    """API per cambiare il pin GPIO"""
    if not gpio_manager:
        return jsonify({'success': False, 'error': 'GPIO non inizializzato'})
        
    try:
        pin = int(request.json.get('pin', 18))
        gpio_manager.set_pin(pin)
        return jsonify({'success': True, 'message': f'Pin GPIO impostato a {pin}'})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Numero pin non valido'})

@app.route('/api/gpio/toggle_monitoring', methods=['POST'])
@login_required
def api_gpio_toggle_monitoring():
    """API per attivare/disattivare il monitoraggio GPIO"""
    if not gpio_manager:
        return jsonify({'success': False, 'error': 'GPIO non inizializzato'})
        
    if gpio_manager.is_monitoring:
        gpio_manager.stop_monitoring()
        message = 'Monitoraggio GPIO fermato'
    else:
        gpio_manager.start_monitoring()
        message = 'Monitoraggio GPIO avviato'
        
    return jsonify({'success': True, 'message': message})

@app.route('/api/time_playlists')
@login_required
def api_get_time_playlists():
    """API per ottenere le playlist configurate per le fasce orarie"""
    try:
        # Leggi la configurazione dal file .env o usa valori di default
        periods = []
        
        # Prova a leggere i periodi personalizzati
        for i in range(1, 5):
            start = os.getenv(f'TIME_PERIOD_{i}_START', '')
            end = os.getenv(f'TIME_PERIOD_{i}_END', '')
            playlist = os.getenv(f'TIME_PERIOD_{i}_PLAYLIST', '')
            
            if start and end:
                periods.append({
                    'start': start,
                    'end': end,
                    'playlist': playlist
                })
        
        # Se non ci sono periodi personalizzati, usa i valori di default
        if not periods:
            periods = [
                {'start': '06:00', 'end': '12:00', 'playlist': os.getenv('PLAYLIST_MORNING', '')},
                {'start': '12:00', 'end': '18:00', 'playlist': os.getenv('PLAYLIST_AFTERNOON', '')},
                {'start': '18:00', 'end': '22:00', 'playlist': os.getenv('PLAYLIST_EVENING', '')},
                {'start': '22:00', 'end': '06:00', 'playlist': os.getenv('PLAYLIST_NIGHT', '')}
            ]
        
        # Determina il periodo corrente
        current_period_index = 0
        if gpio_manager:
            current_period_index = gpio_manager._get_current_time_period_index()
        else:
            from datetime import datetime
            current_hour = datetime.now().hour
            for i, period in enumerate(periods):
                start_hour = int(period['start'].split(':')[0])
                end_hour = int(period['end'].split(':')[0])
                
                if start_hour <= end_hour:
                    if start_hour <= current_hour < end_hour:
                        current_period_index = i
                        break
                else:  # Periodo che attraversa la mezzanotte
                    if current_hour >= start_hour or current_hour < end_hour:
                        current_period_index = i
                        break
        
        return jsonify({
            'periods': periods,
            'current_period_index': current_period_index
        })
    except Exception as e:
        app.logger.error(f"Errore nel recupero playlist temporali: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/time_playlists', methods=['POST'])
@login_required
def api_set_time_playlists():
    """API per impostare le playlist per le fasce orarie"""
    try:
        data = request.json
        periods = data.get('periods', [])
        
        # Aggiorna le variabili d'ambiente
        env_updates = {}
        
        # Rimuovi le vecchie configurazioni
        for i in range(1, 5):
            env_updates[f'TIME_PERIOD_{i}_START'] = ''
            env_updates[f'TIME_PERIOD_{i}_END'] = ''
            env_updates[f'TIME_PERIOD_{i}_PLAYLIST'] = ''
        
        # Aggiungi le nuove configurazioni
        for i, period in enumerate(periods[:4], 1):  # Massimo 4 periodi
            if period.get('start') and period.get('end'):
                env_updates[f'TIME_PERIOD_{i}_START'] = period['start']
                env_updates[f'TIME_PERIOD_{i}_END'] = period['end']
                env_updates[f'TIME_PERIOD_{i}_PLAYLIST'] = period.get('playlist', '')
        
        # Aggiorna il file .env
        update_env_file(env_updates)
        
        # Ricarica la configurazione nel GPIO manager se disponibile
        if gpio_manager:
            gpio_manager._load_time_periods()
        
        return jsonify({'success': True, 'message': 'Playlist temporali aggiornate'})
        
    except Exception as e:
        app.logger.error(f"Errore nell'aggiornamento playlist temporali: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_gpio_trigger', methods=['POST'])
@login_required
def api_test_gpio_trigger():
    """API per testare il trigger GPIO manualmente"""
    if not gpio_manager:
        return jsonify({'success': False, 'error': 'GPIO non inizializzato'})
    
    try:
        # Simula un trigger GPIO
        gpio_manager._handle_gpio_trigger()
        return jsonify({'success': True, 'message': 'Trigger GPIO simulato con successo'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/verify', methods=['POST'])
@login_required
def verify_admin_password():
    """Verifica la password amministratore"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        # Password amministratore (puoi cambiarla nel file .env)
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        if password == admin_password:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Password non corretta'})
    except Exception as e:
        app.logger.error(f"Errore nella verifica password: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/spotify_config', methods=['GET'])
@login_required
def get_spotify_config():
    """Recupera la configurazione Spotify attuale"""
    try:
        config = {
            'client_id': os.getenv('SPOTIFY_CLIENT_ID', ''),
            'client_secret': os.getenv('SPOTIFY_CLIENT_SECRET', ''),
            'redirect_uri': os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:5004/callback')
        }
        
        # Maschera il client secret per sicurezza
        if config['client_secret']:
            config['client_secret'] = '*' * len(config['client_secret'])
        
        return jsonify(config)
    except Exception as e:
        app.logger.error(f"Errore nel recupero configurazione Spotify: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/spotify_config', methods=['POST'])
def set_spotify_config():
    """Imposta la configurazione Spotify"""
    try:
        data = request.get_json()
        
        client_id = data.get('client_id', '').strip()
        client_secret = data.get('client_secret', '').strip()
        redirect_uri = data.get('redirect_uri', '').strip()
        
        if not client_id or not redirect_uri:
            return jsonify({'success': False, 'message': 'Client ID e Redirect URI sono obbligatori'}), 400
        
        # Aggiorna le variabili d'ambiente
        env_updates = {
            'SPOTIFY_CLIENT_ID': client_id,
            'SPOTIFY_REDIRECT_URI': redirect_uri
        }
        
        # Includi il client secret solo se è stato fornito
        if client_secret:
            env_updates['SPOTIFY_CLIENT_SECRET'] = client_secret
        
        # Aggiorna il file .env
        update_env_file(env_updates)
        
        message = 'Configurazione Spotify aggiornata.'
        if not client_secret:
            message += ' Client Secret non modificato.'
        message += ' Riavvia il servizio per applicare le modifiche.'
        
        return jsonify({
            'success': True, 
            'message': message
        })
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione Spotify: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logo/upload', methods=['POST'])
@login_required
def upload_logo():
    """Upload di un logo personalizzato"""
    try:
        if 'logo' not in request.files:
            return jsonify({'success': False, 'error': 'Nessun file selezionato'})
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nessun file selezionato'})
        
        if file and allowed_file(file.filename):
            # Rimuovi il logo esistente se presente
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.startswith('custom_logo.'):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Salva il nuovo logo
            filename = secure_filename(file.filename)
            extension = filename.rsplit('.', 1)[1].lower()
            new_filename = f'custom_logo.{extension}'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)
            
            return jsonify({
                'success': True, 
                'message': 'Logo caricato con successo',
                'logo_url': f'/static/uploads/{new_filename}'
            })
        else:
            return jsonify({'success': False, 'error': 'Formato file non supportato. Usa PNG o SVG.'})
    
    except Exception as e:
        app.logger.error(f"Errore upload logo: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logo/remove', methods=['POST'])
@login_required
def remove_logo():
    """Rimuove il logo personalizzato"""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith('custom_logo.'):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        return jsonify({'success': True, 'message': 'Logo rimosso con successo'})
    
    except Exception as e:
        app.logger.error(f"Errore rimozione logo: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logo/status')
def logo_status():
    """Verifica se esiste un logo personalizzato"""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith('custom_logo.'):
                return jsonify({
                    'has_logo': True,
                    'logo_url': f'/static/uploads/{filename}'
                })
        
        return jsonify({'has_logo': False})
    
    except Exception as e:
        app.logger.error(f"Errore verifica logo: {e}")
        return jsonify({'has_logo': False, 'error': str(e)})

def update_system_status():
    """Aggiorna lo stato del sistema"""
    global system_status
    
    system_status['last_activity'] = datetime.now().strftime('%H:%M:%S')
    
    if spotify_manager:
        try:
            current_playback = spotify_manager.get_current_playback()
            if current_playback and current_playback.get('item'):
                track = current_playback['item']
                system_status['current_track'] = {
                    'name': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'is_playing': current_playback.get('is_playing', False),
                    'progress_ms': current_playback.get('progress_ms', 0),
                    'duration_ms': track.get('duration_ms', 0)
                }
            else:
                system_status['current_track'] = None
        except Exception as e:
            logging.error(f"Errore nell'aggiornamento stato: {e}")
            system_status['current_track'] = None
    
    if gpio_manager:
        system_status['gpio_monitoring'] = gpio_manager.is_monitoring
        system_status['gpio_status'] = gpio_manager.get_pin_state()
        system_status['gpio_pin'] = gpio_manager.gpio_pin
    else:
        system_status['gpio_monitoring'] = False
        system_status['gpio_status'] = False
        system_status['gpio_pin'] = 'N/A'

if __name__ == '__main__':
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Inizializza i manager
    init_managers()
    
    # Avvia l'app Flask
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', 5000))
    
    app.run(host=host, port=port, debug=False)