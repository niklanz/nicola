import time
import threading
import logging
from typing import Callable, Optional
import os

# Importa RPi.GPIO solo se disponibile (Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    GPIO = None

class GPIOManager:
    def __init__(self, spotify_manager):
        self.spotify_manager = spotify_manager
        self.gpio_pin = int(os.getenv('GPIO_PIN', 18))
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_trigger_time = 0
        self.debounce_time = float(os.getenv('GPIO_DEBOUNCE_TIME', 0.5))  # Tempo di debounce in secondi
        self.gpio_available = GPIO_AVAILABLE
        
        if self.gpio_available:
            self._setup_gpio()
        else:
            logging.warning("GPIO non disponibile - modalità simulazione attiva")
        
    def _setup_gpio(self):
        """Configura il pin GPIO"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            logging.info(f"GPIO pin {self.gpio_pin} configurato come input")
        except Exception as e:
            logging.error(f"Errore nella configurazione GPIO: {e}")
            
    def start_monitoring(self):
        """Avvia il monitoraggio del pin GPIO"""
        if self.is_monitoring:
            logging.warning("Monitoraggio GPIO già attivo")
            return
            
        if not self.gpio_available:
            logging.info("GPIO non disponibile - monitoraggio simulato")
            self.is_monitoring = True
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_gpio, daemon=True)
        self.monitor_thread.start()
        logging.info("Monitoraggio GPIO avviato")
        
    def stop_monitoring(self):
        """Ferma il monitoraggio del pin GPIO"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logging.info("Monitoraggio GPIO fermato")
        
    def _monitor_gpio(self):
        """Loop principale per il monitoraggio del GPIO"""
        if self.gpio_available:
            previous_state = GPIO.input(self.gpio_pin)
        else:
            previous_state = False
        
        while self.is_monitoring:
            try:
                if self.gpio_available:
                    current_state = GPIO.input(self.gpio_pin)
                    current_time = time.time()
                    
                    # Rileva il fronte di salita (da LOW a HIGH)
                    if current_state == GPIO.HIGH and previous_state == GPIO.LOW:
                        # Controllo debounce
                        if current_time - self.last_trigger_time > self.debounce_time:
                            self.last_trigger_time = current_time
                            self._handle_gpio_trigger()
                            
                    previous_state = current_state
                    time.sleep(0.01)  # Polling ogni 10ms
                else:
                    # Modalità simulazione - non fa nulla
                    time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Errore nel monitoraggio GPIO: {e}")
                time.sleep(0.1)
                
    def _handle_gpio_trigger(self):
        """Gestisce l'evento di trigger del GPIO"""
        logging.info(f"GPIO trigger rilevato sul pin {self.gpio_pin}")
        
        try:
            # Controlla lo stato attuale della riproduzione
            current_playback = self.spotify_manager.get_current_playback()
            
            if current_playback and current_playback.get('is_playing'):
                # Se sta suonando, metti in pausa
                self.spotify_manager.pause_music()
                logging.info("Musica messa in pausa tramite GPIO")
            else:
                # Se non sta suonando, avvia la riproduzione
                self.spotify_manager.play_music()
                logging.info("Musica avviata tramite GPIO")
                
        except Exception as e:
            logging.error(f"Errore nella gestione trigger GPIO: {e}")
            
    def set_pin(self, pin_number: int):
        """Cambia il pin GPIO da monitorare"""
        if self.is_monitoring:
            self.stop_monitoring()
            
        # Pulisce il pin precedente
        GPIO.cleanup(self.gpio_pin)
        
        # Configura il nuovo pin
        self.gpio_pin = pin_number
        self._setup_gpio()
        
        logging.info(f"Pin GPIO cambiato a: {pin_number}")
        
    def get_pin_state(self) -> bool:
        """Restituisce lo stato attuale del pin"""
        try:
            return bool(GPIO.input(self.gpio_pin))
        except Exception as e:
            logging.error(f"Errore nella lettura pin GPIO: {e}")
            return False
            
    def set_debounce_time(self, debounce_time: float):
        """Imposta il tempo di debounce"""
        self.debounce_time = max(0.1, debounce_time)  # Minimo 100ms
        logging.info(f"Tempo di debounce impostato a: {self.debounce_time}s")
        
    def cleanup(self):
        """Pulisce le risorse GPIO"""
        self.stop_monitoring()
        if self.gpio_available:
            try:
                GPIO.cleanup()
                self.logger.info("GPIO cleanup completato")
            except Exception as e:
                self.logger.error(f"Errore nel cleanup GPIO: {e}")
        else:
            self.logger.info("GPIO cleanup simulato")
            
    def __del__(self):
        """Destructor per cleanup automatico"""
        try:
            if hasattr(self, 'logger'):
                self.cleanup()
        except:
            pass