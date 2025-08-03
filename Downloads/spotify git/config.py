#!/usr/bin/env python3
"""
File di configurazione per Spotify Raspberry Pi Controller
Contiene tutte le impostazioni configurabili del sistema
"""

import os
from typing import Dict, Any

class Config:
    """Classe di configurazione principale"""
    
    # Configurazione Spotify
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
    SPOTIFY_SCOPE = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,playlist-read-private,playlist-read-collaborative"
    SPOTIFY_CACHE_PATH = ".spotify_cache"
    
    # Configurazione GPIO
    GPIO_PIN = int(os.getenv('GPIO_PIN', 18))
    GPIO_DEBOUNCE_TIME = float(os.getenv('GPIO_DEBOUNCE_TIME', 0.5))
    GPIO_PULL_UP_DOWN = 'PUD_DOWN'  # PUD_UP, PUD_DOWN, PUD_OFF
    
    # Configurazione Web
    WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
    WEB_PORT = int(os.getenv('WEB_PORT', 5000))
    WEB_DEBUG = os.getenv('WEB_DEBUG', 'False').lower() == 'true'
    
    # Configurazione Audio
    DEFAULT_DEVICE_NAME = os.getenv('DEFAULT_DEVICE_NAME', 'raspberrypi')
    DEFAULT_VOLUME = int(os.getenv('VOLUME_LEVEL', 70))
    DEFAULT_PLAYLIST_URI = os.getenv('DEFAULT_PLAYLIST_URI')
    
    # Configurazione Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'spotify_pi.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    
    # Configurazione Sistema
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 30))  # secondi
    STATUS_UPDATE_INTERVAL = int(os.getenv('STATUS_UPDATE_INTERVAL', 5))  # secondi
    
    # Configurazione librespot
    LIBRESPOT_NAME = os.getenv('LIBRESPOT_NAME', 'RaspberryPi')
    LIBRESPOT_BITRATE = os.getenv('LIBRESPOT_BITRATE', '320')
    LIBRESPOT_DEVICE_TYPE = os.getenv('LIBRESPOT_DEVICE_TYPE', 'speaker')
    LIBRESPOT_BACKEND = os.getenv('LIBRESPOT_BACKEND', 'alsa')
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Valida la configurazione e restituisce errori"""
        errors = []
        warnings = []
        
        # Verifica credenziali Spotify
        if not cls.SPOTIFY_CLIENT_ID:
            errors.append("SPOTIFY_CLIENT_ID mancante")
        if not cls.SPOTIFY_CLIENT_SECRET:
            errors.append("SPOTIFY_CLIENT_SECRET mancante")
            
        # Verifica configurazione GPIO
        if not (1 <= cls.GPIO_PIN <= 40):
            warnings.append(f"GPIO_PIN {cls.GPIO_PIN} potrebbe non essere valido")
            
        if not (0.1 <= cls.GPIO_DEBOUNCE_TIME <= 5.0):
            warnings.append(f"GPIO_DEBOUNCE_TIME {cls.GPIO_DEBOUNCE_TIME} potrebbe essere troppo alto/basso")
            
        # Verifica configurazione Web
        if not (1024 <= cls.WEB_PORT <= 65535):
            warnings.append(f"WEB_PORT {cls.WEB_PORT} potrebbe non essere valida")
            
        # Verifica configurazione Audio
        if not (0 <= cls.DEFAULT_VOLUME <= 100):
            warnings.append(f"DEFAULT_VOLUME {cls.DEFAULT_VOLUME} deve essere tra 0 e 100")
            
        return {
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0
        }
    
    @classmethod
    def get_gpio_config(cls) -> Dict[str, Any]:
        """Restituisce la configurazione GPIO"""
        return {
            'pin': cls.GPIO_PIN,
            'debounce_time': cls.GPIO_DEBOUNCE_TIME,
            'pull_up_down': cls.GPIO_PULL_UP_DOWN
        }
    
    @classmethod
    def get_spotify_config(cls) -> Dict[str, Any]:
        """Restituisce la configurazione Spotify"""
        return {
            'client_id': cls.SPOTIFY_CLIENT_ID,
            'client_secret': cls.SPOTIFY_CLIENT_SECRET,
            'redirect_uri': cls.SPOTIFY_REDIRECT_URI,
            'scope': cls.SPOTIFY_SCOPE,
            'cache_path': cls.SPOTIFY_CACHE_PATH,
            'default_device': cls.DEFAULT_DEVICE_NAME,
            'default_volume': cls.DEFAULT_VOLUME,
            'default_playlist': cls.DEFAULT_PLAYLIST_URI
        }
    
    @classmethod
    def get_web_config(cls) -> Dict[str, Any]:
        """Restituisce la configurazione Web"""
        return {
            'host': cls.WEB_HOST,
            'port': cls.WEB_PORT,
            'debug': cls.WEB_DEBUG
        }
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Restituisce la configurazione Logging"""
        return {
            'level': cls.LOG_LEVEL,
            'file': cls.LOG_FILE,
            'max_bytes': cls.LOG_MAX_BYTES,
            'backup_count': cls.LOG_BACKUP_COUNT
        }
    
    @classmethod
    def get_librespot_config(cls) -> Dict[str, Any]:
        """Restituisce la configurazione librespot"""
        return {
            'name': cls.LIBRESPOT_NAME,
            'bitrate': cls.LIBRESPOT_BITRATE,
            'device_type': cls.LIBRESPOT_DEVICE_TYPE,
            'backend': cls.LIBRESPOT_BACKEND
        }
    
    @classmethod
    def print_config(cls):
        """Stampa la configurazione corrente"""
        print("=== Configurazione Spotify Raspberry Pi Controller ===")
        print(f"GPIO Pin: {cls.GPIO_PIN}")
        print(f"Web Interface: {cls.WEB_HOST}:{cls.WEB_PORT}")
        print(f"Default Volume: {cls.DEFAULT_VOLUME}%")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Spotify Device: {cls.DEFAULT_DEVICE_NAME}")
        print(f"librespot Name: {cls.LIBRESPOT_NAME}")
        
        validation = cls.validate()
        if validation['errors']:
            print("\n❌ ERRORI:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("\n⚠️  AVVISI:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        if validation['valid']:
            print("\n✅ Configurazione valida")
        else:
            print("\n❌ Configurazione non valida")

# Configurazioni predefinite per diversi scenari
class DevelopmentConfig(Config):
    """Configurazione per sviluppo"""
    WEB_DEBUG = True
    LOG_LEVEL = 'DEBUG'
    HEALTH_CHECK_INTERVAL = 10

class ProductionConfig(Config):
    """Configurazione per produzione"""
    WEB_DEBUG = False
    LOG_LEVEL = 'INFO'
    HEALTH_CHECK_INTERVAL = 60

class TestConfig(Config):
    """Configurazione per test"""
    WEB_DEBUG = True
    LOG_LEVEL = 'DEBUG'
    GPIO_PIN = 99  # Pin fittizio per test
    WEB_PORT = 5001

# Mappa delle configurazioni
CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
    'default': Config
}

def get_config(config_name: str = None) -> Config:
    """Restituisce la configurazione richiesta"""
    if not config_name:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return CONFIG_MAP.get(config_name, Config)

if __name__ == '__main__':
    # Test della configurazione
    config = get_config()
    config.print_config()