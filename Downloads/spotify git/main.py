#!/usr/bin/env python3
"""
Spotify Raspberry Pi Controller
Applicazione principale per il controllo di Spotify tramite GPIO e interfaccia web

Autore: Assistant
Data: 2024
"""

import os
import sys
import logging
import signal
import time
from threading import Thread
from dotenv import load_dotenv

# Importa i moduli personalizzati
from spotify_manager import SpotifyManager
from gpio_manager import GPIOManager
from web_interface import app, init_managers

class SpotifyPiController:
    def __init__(self):
        self.spotify_manager = None
        self.gpio_manager = None
        self.web_thread = None
        self.running = False
        
        # Configura logging
        self.setup_logging()
        
        # Carica variabili d'ambiente
        self.load_environment()
        
        # Configura gestione segnali
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Configura il sistema di logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('spotify_pi.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Riduci il livello di log per alcune librerie
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Sistema di logging inizializzato")
        
    def load_environment(self):
        """Carica le variabili d'ambiente"""
        # Carica il file .env se esiste
        env_file = '.env'
        if os.path.exists(env_file):
            load_dotenv(env_file)
            self.logger.info(f"Variabili d'ambiente caricate da {env_file}")
        else:
            self.logger.warning(f"File {env_file} non trovato. Usa .env.example come riferimento")
            
        # Verifica modalità demo o credenziali Spotify
        demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        
        if not demo_mode:
            required_vars = ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                self.logger.error(f"Variabili d'ambiente mancanti: {', '.join(missing_vars)}")
                self.logger.error("Configura le credenziali Spotify nel file .env o attiva DEMO_MODE=True")
                sys.exit(1)
        else:
            self.logger.info("Modalità demo attivata - interfaccia web disponibile senza Spotify")
            
    def setup_signal_handlers(self):
        """Configura i gestori dei segnali per shutdown pulito"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Gestisce i segnali di terminazione"""
        self.logger.info(f"Ricevuto segnale {signum}, avvio shutdown...")
        self.shutdown()
        
    def initialize_managers(self):
        """Inizializza i manager Spotify e GPIO"""
        try:
            # Inizializza Spotify Manager
            self.logger.info("Inizializzazione Spotify Manager...")
            self.spotify_manager = SpotifyManager()
            self.logger.info("Spotify Manager inizializzato con successo")
            
            # Inizializza GPIO Manager solo su Raspberry Pi
            if self.is_raspberry_pi():
                self.logger.info("Inizializzazione GPIO Manager...")
                self.gpio_manager = GPIOManager(self.spotify_manager)
                self.gpio_manager.start_monitoring()
                self.logger.info("GPIO Manager inizializzato con successo")
            else:
                self.logger.warning("Non su Raspberry Pi - GPIO Manager disabilitato")
                
        except Exception as e:
            self.logger.error(f"Errore nell'inizializzazione manager: {e}")
            raise
            
    def is_raspberry_pi(self):
        """Verifica se il sistema è un Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo or 'ARM' in cpuinfo
        except:
            return False
            
    def start_web_interface(self):
        """Avvia l'interfaccia web in un thread separato"""
        try:
            host = os.getenv('WEB_HOST', '0.0.0.0')
            port = int(os.getenv('WEB_PORT', 5000))
            
            self.logger.info(f"Avvio interfaccia web su {host}:{port}")
            
            # Inizializza i manager nell'app Flask
            init_managers()
            
            # Avvia Flask in un thread separato
            self.web_thread = Thread(
                target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
                daemon=True
            )
            self.web_thread.start()
            
            self.logger.info(f"Interfaccia web disponibile su http://{host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Errore nell'avvio interfaccia web: {e}")
            raise
            
    def run(self):
        """Avvia l'applicazione principale"""
        try:
            self.logger.info("=== Avvio Spotify Raspberry Pi Controller ===")
            
            # Inizializza i manager
            self.initialize_managers()
            
            # Avvia l'interfaccia web
            self.start_web_interface()
            
            self.running = True
            self.logger.info("Sistema avviato con successo")
            
            # Loop principale
            self.main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("Interruzione da tastiera ricevuta")
        except Exception as e:
            self.logger.error(f"Errore critico: {e}")
        finally:
            self.shutdown()
            
    def main_loop(self):
        """Loop principale dell'applicazione"""
        self.logger.info("Entrato nel loop principale")
        
        try:
            while self.running:
                # Verifica stato sistema ogni 30 secondi
                self.check_system_health()
                time.sleep(30)
                
        except Exception as e:
            self.logger.error(f"Errore nel loop principale: {e}")
            
    def check_system_health(self):
        """Verifica lo stato del sistema"""
        try:
            # Verifica connessione Spotify
            if self.spotify_manager:
                try:
                    devices = self.spotify_manager.get_devices()
                    self.logger.debug(f"Dispositivi Spotify disponibili: {len(devices)}")
                except Exception as e:
                    self.logger.warning(f"Problema connessione Spotify: {e}")
                    
            # Verifica GPIO
            if self.gpio_manager and not self.gpio_manager.is_monitoring:
                self.logger.warning("Monitoraggio GPIO non attivo")
                
        except Exception as e:
            self.logger.error(f"Errore nel controllo sistema: {e}")
            
    def shutdown(self):
        """Shutdown pulito dell'applicazione"""
        if not self.running:
            return
            
        self.logger.info("Avvio procedura di shutdown...")
        self.running = False
        
        try:
            # Ferma GPIO Manager
            if self.gpio_manager:
                self.logger.info("Shutdown GPIO Manager...")
                self.gpio_manager.cleanup()
                
            # Nota: Flask si chiuderà automaticamente quando il processo termina
            
            self.logger.info("Shutdown completato")
            
        except Exception as e:
            self.logger.error(f"Errore durante shutdown: {e}")
            
def main():
    """Funzione principale"""
    # Verifica che il file .env esista
    if not os.path.exists('.env'):
        print("ATTENZIONE: File .env non trovato!")
        print("Copia .env.example in .env e configura le tue credenziali Spotify")
        print("")
        print("Passi necessari:")
        print("1. Vai su https://developer.spotify.com/dashboard/")
        print("2. Crea una nuova app")
        print("3. Copia Client ID e Client Secret nel file .env")
        print("4. Imposta Redirect URI: http://localhost:8888/callback")
        print("")
        
        # Chiedi se continuare comunque
        response = input("Vuoi continuare comunque? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
            
    # Avvia l'applicazione
    controller = SpotifyPiController()
    controller.run()
    
if __name__ == '__main__':
    main()