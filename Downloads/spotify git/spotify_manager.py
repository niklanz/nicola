import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import time
import logging
from typing import Optional, Dict, Any

class SpotifyManager:
    def __init__(self):
        self.demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        self.device_name = os.getenv('DEFAULT_DEVICE_NAME', 'raspberrypi')
        self.default_playlist = os.getenv('DEFAULT_PLAYLIST_URI')
        self.volume_level = int(os.getenv('VOLUME_LEVEL', 70))
        
        self.scope = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,playlist-read-private,playlist-read-collaborative"
        
        self.sp = None
        self.current_device_id = None
        self.is_playing = False
        
        # Inizializza Spotify solo se non in modalità demo
        if not self.demo_mode:
            self._setup_spotify()
        else:
            logging.info("Spotify Manager in modalità demo")
        
    def _setup_spotify(self):
        """Inizializza la connessione Spotify"""
        try:
            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache"
            )
            
            self.sp = spotipy.Spotify(auth_manager=self.sp_oauth)
            logging.info("Spotify client inizializzato con successo")
            
            # Trova il dispositivo Raspberry Pi
            self._find_device()
            
        except Exception as e:
            logging.error(f"Errore nell'inizializzazione Spotify: {e}")
            
    def _find_device(self):
        """Trova il dispositivo Raspberry Pi tra i dispositivi disponibili"""
        try:
            devices = self.sp.devices()
            for device in devices['devices']:
                if self.device_name.lower() in device['name'].lower():
                    self.current_device_id = device['id']
                    logging.info(f"Dispositivo trovato: {device['name']} (ID: {device['id']})")
                    return
                    
            # Se non trova il dispositivo specifico, usa il primo disponibile
            if devices['devices']:
                self.current_device_id = devices['devices'][0]['id']
                logging.warning(f"Dispositivo {self.device_name} non trovato, uso: {devices['devices'][0]['name']}")
            else:
                logging.error("Nessun dispositivo Spotify disponibile")
                
        except Exception as e:
            logging.error(f"Errore nella ricerca dispositivi: {e}")
            
    def get_devices(self) -> list:
        """Restituisce la lista dei dispositivi disponibili"""
        if self.demo_mode:
            return [
                {
                    'id': 'demo_device_1',
                    'name': 'Raspberry Pi Demo',
                    'type': 'Computer',
                    'is_active': True,
                    'is_private_session': False,
                    'is_restricted': False,
                    'volume_percent': 70
                },
                {
                    'id': 'demo_device_2',
                    'name': 'Smartphone Demo',
                    'type': 'Smartphone',
                    'is_active': False,
                    'is_private_session': False,
                    'is_restricted': False,
                    'volume_percent': 50
                }
            ]
            
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return []
            
        try:
            devices = self.sp.devices()
            device_list = devices.get('devices', []) if devices else []
            
            # Aggiungi sempre il dispositivo locale librespot se non è già presente
            local_device_names = ['RaspberryPi', 'SistemaPalestra']
            local_device_found = False
            
            for device in device_list:
                if device['name'] in local_device_names:
                    local_device_found = True
                    break
            
            # Se il dispositivo locale non è trovato, aggiungilo manualmente
            if not local_device_found:
                # Controlla se librespot è in esecuzione
                import subprocess
                try:
                    result = subprocess.run(['pgrep', 'librespot'], capture_output=True, text=True)
                    if result.returncode == 0:  # librespot è in esecuzione
                        local_device = {
                            'id': 'local_librespot',
                            'name': 'SistemaPalestra',
                            'type': 'Computer',
                            'is_active': False,
                            'is_private_session': False,
                            'is_restricted': False,
                            'volume_percent': 70
                        }
                        device_list.append(local_device)
                        logging.info("Dispositivo librespot locale aggiunto alla lista")
                except Exception as e:
                    logging.warning(f"Impossibile verificare stato librespot: {e}")
            
            if not device_list:
                logging.warning("Nessun dispositivo Spotify attivo trovato. Assicurati che un'app Spotify sia aperta e attiva.")
                
            return device_list
        except Exception as e:
            logging.error(f"Errore nel recupero dispositivi: {e}")
            return []
            
    def set_device(self, device_id: str):
        """Imposta il dispositivo attivo e trasferisce la riproduzione"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if device_id == 'local_librespot':
                # Verifica se librespot è in esecuzione
                import subprocess
                try:
                    result = subprocess.run(['pgrep', 'librespot'], capture_output=True, text=True)
                    if result.returncode != 0:  # librespot non è in esecuzione
                        logging.warning("Librespot non in esecuzione, tentativo di avvio...")
                        # Prova ad avviare librespot
                        subprocess.Popen([
                            'librespot',
                            '--name', 'RaspberryPi',
                            '--bitrate', '320',
                            '--device-type', 'speaker',
                            '--backend', 'alsa',
                            '--mixer', 'softvol',
                            '--initial-volume', '70',
                            '--volume-ctrl', 'linear',
                            '--cache', '/tmp/librespot-cache',
                            '--enable-volume-normalisation',
                            '--normalisation-pregain', '-10'
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # Attendi che librespot si avvii
                        time.sleep(3)
                        
                        # Verifica nuovamente
                        result = subprocess.run(['pgrep', 'librespot'], capture_output=True, text=True)
                        if result.returncode != 0:
                            logging.error("Impossibile avviare librespot")
                            return False
                        else:
                            logging.info("Librespot avviato con successo")
                    
                    # Attendi che il dispositivo sia disponibile in Spotify
                    time.sleep(2)
                    
                    # Cerca il dispositivo SistemaPalestra nei dispositivi Spotify
                    devices = self.sp.devices()
                    raspberry_device = None
                    for device in devices['devices']:
                        device_name_lower = device['name'].lower()
                        if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                            raspberry_device = device
                            break
                    
                    if raspberry_device:
                        # Trasferisci la riproduzione al dispositivo SistemaPalestra
                        self.sp.transfer_playback(device_id=raspberry_device['id'], force_play=True)
                        logging.info(f"Riproduzione trasferita al dispositivo SistemaPalestra: {raspberry_device['id']}")
                        # Salva l'ID del dispositivo reale per future operazioni
                        self.current_device_id = raspberry_device['id']
                        return True
                    else:
                        logging.warning("Dispositivo SistemaPalestra non trovato nei dispositivi Spotify disponibili")
                        logging.info("Tentativo di avviare riproduzione direttamente su librespot...")
                        
                        # Prova a riprodurre musica direttamente se c'è una riproduzione attiva
                        try:
                            current_playback = self.sp.current_playback()
                            if current_playback and current_playback['is_playing']:
                                # Pausa la riproduzione corrente
                                self.sp.pause_playback()
                                time.sleep(1)
                                
                                # Riprendi su qualsiasi dispositivo disponibile per "forzare" l'aggiornamento
                                devices = self.sp.devices()
                                if devices['devices']:
                                    available_device = devices['devices'][0]
                                    self.sp.transfer_playback(device_id=available_device['id'], force_play=True)
                                    time.sleep(2)
                                    
                                    # Ricontrolla se ora SistemaPalestra è disponibile
                                    devices = self.sp.devices()
                                    for device in devices['devices']:
                                        device_name_lower = device['name'].lower()
                                        if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                                            self.sp.transfer_playback(device_id=device['id'], force_play=True)
                                            self.current_device_id = device['id']
                                            logging.info(f"SistemaPalestra ora disponibile: {device['id']}")
                                            return True
                        except Exception as e:
                            logging.error(f"Errore nel tentativo di attivazione: {e}")
                        
                        # Fallback: imposta comunque come dispositivo locale
                        self.current_device_id = device_id
                        logging.info("Dispositivo impostato come locale - controllare manualmente su Spotify")
                        return True
                    
                    self.current_device_id = device_id
                    logging.info(f"Dispositivo locale impostato: {device_id}")
                    return True
                    
                except Exception as e:
                    logging.error(f"Errore nella gestione librespot: {e}")
                    return False
                
            # Per dispositivi Spotify normali, trasferisci la riproduzione
            self.sp.transfer_playback(device_id=device_id, force_play=False)
            self.current_device_id = device_id
            logging.info(f"Riproduzione trasferita al dispositivo: {device_id}")
            return True
            
        except Exception as e:
            logging.error(f"Errore nel trasferimento al dispositivo {device_id}: {e}")
            return False
        
    def play_music(self, playlist_uri: Optional[str] = None):
        """Avvia la riproduzione musicale"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Verifica se abbiamo trovato il dispositivo SistemaPalestra reale
                devices = self.sp.devices()
                raspberry_device = None
                for device in devices['devices']:
                    device_name_lower = device['name'].lower()
                    if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                        raspberry_device = device
                        break
                
                if raspberry_device:
                    # Aggiorna l'ID del dispositivo con quello reale
                    self.current_device_id = raspberry_device['id']
                    logging.info(f"Dispositivo SistemaPalestra trovato, aggiornato ID: {raspberry_device['id']}")
                else:
                    logging.info("Controllo diretto librespot locale - riproduzione non gestita via API")
                    return True
                
            if not self.current_device_id:
                self._find_device()
                if not self.current_device_id:
                    logging.error("Nessun dispositivo disponibile per la riproduzione")
                    return False
                    
            # Usa la playlist di default se non specificata
            if not playlist_uri:
                playlist_uri = self.default_playlist
                
            # Avvia la riproduzione
            if playlist_uri:
                self.sp.start_playback(
                    device_id=self.current_device_id,
                    context_uri=playlist_uri
                )
            else:
                self.sp.start_playback(device_id=self.current_device_id)
                
            # Imposta il volume
            self.sp.volume(self.volume_level, device_id=self.current_device_id)
            
            self.is_playing = True
            logging.info("Riproduzione avviata")
            return True
            
        except Exception as e:
            logging.error(f"Errore nell'avvio riproduzione: {e}")
            return False
            
    def pause_music(self):
        """Mette in pausa la riproduzione"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Verifica se abbiamo trovato il dispositivo SistemaPalestra reale
                devices = self.sp.devices()
                raspberry_device = None
                for device in devices['devices']:
                    device_name_lower = device['name'].lower()
                    if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                        raspberry_device = device
                        break
                
                if raspberry_device:
                    # Aggiorna l'ID del dispositivo con quello reale
                    self.current_device_id = raspberry_device['id']
                    logging.info(f"Dispositivo SistemaPalestra trovato per pausa, aggiornato ID: {raspberry_device['id']}")
                else:
                    logging.info("Controllo diretto librespot locale - pausa non gestita via API")
                    return True
                
            self.sp.pause_playback(device_id=self.current_device_id)
            self.is_playing = False
            logging.info("Riproduzione in pausa")
            return True
        except Exception as e:
            logging.error(f"Errore nella pausa: {e}")
            return False
            
    def stop_music(self):
        """Ferma la riproduzione"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Verifica se abbiamo trovato il dispositivo SistemaPalestra reale
                devices = self.sp.devices()
                raspberry_device = None
                for device in devices['devices']:
                    device_name_lower = device['name'].lower()
                    if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                        raspberry_device = device
                        break
                
                if raspberry_device:
                    # Aggiorna l'ID del dispositivo con quello reale
                    self.current_device_id = raspberry_device['id']
                    logging.info(f"Dispositivo SistemaPalestra trovato per stop, aggiornato ID: {raspberry_device['id']}")
                else:
                    logging.info("Controllo diretto librespot locale - stop non gestito via API")
                    return True
                
            self.sp.pause_playback(device_id=self.current_device_id)
            self.is_playing = False
            logging.info("Riproduzione fermata")
            return True
        except Exception as e:
            logging.error(f"Errore nello stop: {e}")
            return False
            
    def toggle_playback(self):
        """Alterna tra play e pausa"""
        current_playback = self.get_current_playback()
        if current_playback and current_playback.get('is_playing'):
            return self.pause_music()
        else:
            return self.play_music()
            
    def next_track(self):
        """Passa alla traccia successiva"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Verifica se abbiamo trovato il dispositivo SistemaPalestra reale
                devices = self.sp.devices()
                raspberry_device = None
                for device in devices['devices']:
                    device_name_lower = device['name'].lower()
                    if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                        raspberry_device = device
                        break
                
                if raspberry_device:
                    # Aggiorna l'ID del dispositivo con quello reale
                    self.current_device_id = raspberry_device['id']
                    logging.info(f"Dispositivo SistemaPalestra trovato per next, aggiornato ID: {raspberry_device['id']}")
                else:
                    logging.info("Controllo diretto librespot locale - next non gestito via API")
                    return True
                
            self.sp.next_track(device_id=self.current_device_id)
            logging.info("Traccia successiva")
            return True
        except Exception as e:
            logging.error(f"Errore nel passaggio alla traccia successiva: {e}")
            return False
            
    def previous_track(self):
        """Passa alla traccia precedente"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Verifica se abbiamo trovato il dispositivo SistemaPalestra reale
                devices = self.sp.devices()
                raspberry_device = None
                for device in devices['devices']:
                    device_name_lower = device['name'].lower()
                    if 'sistemapalestra' in device_name_lower or device['name'] == 'SistemaPalestra':
                        raspberry_device = device
                        break
                
                if raspberry_device:
                    # Aggiorna l'ID del dispositivo con quello reale
                    self.current_device_id = raspberry_device['id']
                    logging.info(f"Dispositivo SistemaPalestra trovato per previous, aggiornato ID: {raspberry_device['id']}")
                else:
                    logging.info("Controllo diretto librespot locale - previous non gestito via API")
                    return True
                
            self.sp.previous_track(device_id=self.current_device_id)
            logging.info("Traccia precedente")
            return True
        except Exception as e:
            logging.error(f"Errore nel passaggio alla traccia precedente: {e}")
            return False
            
    def set_volume(self, volume: int):
        """Imposta il volume (0-100)"""
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return False
            
        try:
            volume = max(0, min(100, volume))  # Limita tra 0 e 100
            
            # Gestione speciale per dispositivo locale librespot
            if self.current_device_id == 'local_librespot':
                # Usa amixer per controllare il volume locale
                import subprocess
                try:
                    subprocess.run(['amixer', 'set', 'Master', f'{volume}%'], 
                                 capture_output=True, check=True)
                    self.volume_level = volume
                    logging.info(f"Volume locale impostato a: {volume}%")
                    return True
                except subprocess.CalledProcessError as e:
                    logging.error(f"Errore nel controllo volume locale: {e}")
                    return False
                    
            self.sp.volume(volume, device_id=self.current_device_id)
            self.volume_level = volume
            logging.info(f"Volume impostato a: {volume}")
            return True
        except Exception as e:
            logging.error(f"Errore nell'impostazione volume: {e}")
            return False
            
    def get_current_playback(self) -> Optional[Dict[str, Any]]:
        """Restituisce informazioni sulla riproduzione corrente"""
        if self.demo_mode:
            return {
                'name': 'Demo Track',
                'artist': 'Demo Artist',
                'album': 'Demo Album',
                'album_image': 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzFkYjk1NCIvPjx0ZXh0IHg9IjE1MCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+RGVtbyBBbGJ1bTwvdGV4dD48L3N2Zz4=',
                'duration_ms': 180000,
                'progress_ms': 45000,
                'is_playing': True,
                'volume': 70
            }
            
        try:
            if not self.sp:
                return None
                
            current = self.sp.current_playback()
            if current and current.get('item'):
                track = current['item']
                album_images = track['album'].get('images', [])
                album_image_url = album_images[0]['url'] if album_images else None
                
                return {
                    'name': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': track['album']['name'],
                    'album_image': album_image_url,
                    'duration_ms': track['duration_ms'],
                    'progress_ms': current.get('progress_ms', 0),
                    'is_playing': current.get('is_playing', False),
                    'volume': current.get('device', {}).get('volume_percent', 0)
                }
        except Exception as e:
            logging.error(f"Errore nel recupero stato riproduzione: {e}")
        return None
            
    def get_user_playlists(self) -> list:
        """Restituisce le playlist dell'utente"""
        try:
            playlists = self.sp.current_user_playlists(limit=50)
            return playlists['items']
        except Exception as e:
            logging.error(f"Errore nel recupero playlist: {e}")
            return []
            
    def search_tracks(self, query: str, limit: int = 20) -> list:
        """Cerca tracce su Spotify"""
        if self.demo_mode:
            # Restituisce risultati demo per la ricerca
            demo_tracks = [
                {
                    'id': 'demo_track_1',
                    'name': f'Demo Song - {query}',
                    'artists': [{'name': 'Demo Artist'}],
                    'album': {'name': 'Demo Album'},
                    'duration_ms': 180000,
                    'uri': 'spotify:track:demo1'
                },
                {
                    'id': 'demo_track_2', 
                    'name': f'Another Demo - {query}',
                    'artists': [{'name': 'Demo Band'}],
                    'album': {'name': 'Demo Collection'},
                    'duration_ms': 210000,
                    'uri': 'spotify:track:demo2'
                },
                {
                    'id': 'demo_track_3',
                    'name': f'Test Track - {query}',
                    'artists': [{'name': 'Test Artist'}],
                    'album': {'name': 'Test Album'},
                    'duration_ms': 195000,
                    'uri': 'spotify:track:demo3'
                }
            ]
            return demo_tracks[:limit]
            
        if not self.sp:
            logging.error("Spotify client non inizializzato")
            return []
            
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            return results['tracks']['items']
        except Exception as e:
            logging.error(f"Errore nella ricerca: {e}")
            return []
            
    def is_connected(self):
        """Verifica se Spotify è connesso"""
        if self.demo_mode:
            return True
        return self.sp is not None
    
    def reinitialize_connection(self):
        """Reinizializza la connessione Spotify dopo una nuova autorizzazione"""
        try:
            if not self.demo_mode:
                self._setup_spotify()
                logging.info("Connessione Spotify reinizializzata con successo")
                return True
            return False
        except Exception as e:
            logging.error(f"Errore nella reinizializzazione Spotify: {e}")
            return False
    
    def disconnect_spotify(self):
        """Disconnette Spotify e rimuove l'autorizzazione"""
        try:
            if self.demo_mode:
                logging.info("Modalità demo: disconnessione simulata")
                return True
                
            # Rimuovi il file di cache del token
            cache_path = ".spotify_cache"
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logging.info("File cache Spotify rimosso")
            
            # Backup del file cache se esiste
            backup_path = ".spotify_cache.backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logging.info("File backup cache Spotify rimosso")
            
            # Reset delle variabili
            self.sp = None
            self.sp_oauth = None
            self.current_device_id = None
            self.is_playing = False
            
            logging.info("Spotify disconnesso con successo")
            return True
            
        except Exception as e:
            logging.error(f"Errore nella disconnessione Spotify: {e}")
            return False