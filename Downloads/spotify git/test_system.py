#!/usr/bin/env python3
"""
Script di test per Spotify Raspberry Pi Controller
Verifica che tutti i componenti siano configurati correttamente
"""

import os
import sys
import logging
import importlib
from typing import Dict, List, Tuple
from config import Config

class SystemTester:
    def __init__(self):
        self.results = []
        self.setup_logging()
        
    def setup_logging(self):
        """Configura logging per i test"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def test_python_dependencies(self) -> Tuple[bool, str]:
        """Testa le dipendenze Python"""
        self.logger.info("Testing Python dependencies...")
        
        required_modules = [
            'spotipy',
            'flask', 
            'requests',
            'psutil',
            'dotenv'
        ]
        
        # Test RPi.GPIO solo su Raspberry Pi
        if self.is_raspberry_pi():
            required_modules.append('RPi.GPIO')
            
        missing_modules = []
        
        for module in required_modules:
            try:
                importlib.import_module(module)
                self.logger.info(f"✅ {module} - OK")
            except ImportError:
                missing_modules.append(module)
                self.logger.error(f"❌ {module} - MISSING")
                
        if missing_modules:
            return False, f"Moduli mancanti: {', '.join(missing_modules)}"
        
        return True, "Tutte le dipendenze Python sono installate"
    
    def test_configuration(self) -> Tuple[bool, str]:
        """Testa la configurazione"""
        self.logger.info("Testing configuration...")
        
        validation = Config.validate()
        
        if validation['errors']:
            return False, f"Errori configurazione: {', '.join(validation['errors'])}"
        
        if validation['warnings']:
            self.logger.warning(f"Avvisi configurazione: {', '.join(validation['warnings'])}")
            
        return True, "Configurazione valida"
    
    def test_env_file(self) -> Tuple[bool, str]:
        """Testa il file .env"""
        self.logger.info("Testing .env file...")
        
        if not os.path.exists('.env'):
            return False, "File .env non trovato. Copia .env.example in .env"
            
        # Verifica variabili essenziali
        required_vars = ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                
        if missing_vars:
            return False, f"Variabili mancanti in .env: {', '.join(missing_vars)}"
            
        return True, "File .env configurato correttamente"
    
    def test_spotify_connection(self) -> Tuple[bool, str]:
        """Testa la connessione Spotify"""
        self.logger.info("Testing Spotify connection...")
        
        try:
            from spotify_manager import SpotifyManager
            spotify = SpotifyManager()
            
            # Test connessione
            devices = spotify.get_devices()
            self.logger.info(f"Dispositivi Spotify trovati: {len(devices)}")
            
            return True, f"Connessione Spotify OK - {len(devices)} dispositivi trovati"
            
        except Exception as e:
            return False, f"Errore connessione Spotify: {str(e)}"
    
    def test_gpio_setup(self) -> Tuple[bool, str]:
        """Testa la configurazione GPIO"""
        self.logger.info("Testing GPIO setup...")
        
        if not self.is_raspberry_pi():
            return True, "Non su Raspberry Pi - GPIO test saltato"
            
        try:
            import RPi.GPIO as GPIO
            
            # Test configurazione GPIO
            pin = Config.GPIO_PIN
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Test lettura pin
            state = GPIO.input(pin)
            self.logger.info(f"GPIO pin {pin} stato: {state}")
            
            GPIO.cleanup()
            
            return True, f"GPIO pin {pin} configurato correttamente"
            
        except Exception as e:
            return False, f"Errore GPIO: {str(e)}"
    
    def test_audio_system(self) -> Tuple[bool, str]:
        """Testa il sistema audio"""
        self.logger.info("Testing audio system...")
        
        try:
            import subprocess
            
            # Test ALSA
            result = subprocess.run(['aplay', '-l'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                audio_devices = [line for line in lines if 'card' in line.lower()]
                
                if audio_devices:
                    return True, f"Sistema audio OK - {len(audio_devices)} dispositivi trovati"
                else:
                    return False, "Nessun dispositivo audio trovato"
            else:
                return False, "Comando aplay fallito"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout nel test audio"
        except FileNotFoundError:
            return False, "aplay non trovato - installa alsa-utils"
        except Exception as e:
            return False, f"Errore test audio: {str(e)}"
    
    def test_web_interface(self) -> Tuple[bool, str]:
        """Testa l'interfaccia web"""
        self.logger.info("Testing web interface...")
        
        try:
            from web_interface import app
            
            # Test creazione app Flask
            with app.test_client() as client:
                # Test route principale
                response = client.get('/')
                
                if response.status_code == 200:
                    return True, "Interfaccia web funzionante"
                else:
                    return False, f"Errore HTTP {response.status_code}"
                    
        except Exception as e:
            return False, f"Errore interfaccia web: {str(e)}"
    
    def test_file_permissions(self) -> Tuple[bool, str]:
        """Testa i permessi dei file"""
        self.logger.info("Testing file permissions...")
        
        files_to_check = [
            ('install.sh', True),  # Deve essere eseguibile
            ('main.py', False),
            ('spotify_manager.py', False),
            ('gpio_manager.py', False),
            ('web_interface.py', False)
        ]
        
        issues = []
        
        for filename, should_be_executable in files_to_check:
            if not os.path.exists(filename):
                issues.append(f"{filename} non trovato")
                continue
                
            is_executable = os.access(filename, os.X_OK)
            
            if should_be_executable and not is_executable:
                issues.append(f"{filename} non è eseguibile")
            elif not should_be_executable and is_executable:
                # Non è un errore, solo un avviso
                self.logger.info(f"ℹ️  {filename} è eseguibile (non necessario)")
                
        if issues:
            return False, f"Problemi permessi: {', '.join(issues)}"
            
        return True, "Permessi file corretti"
    
    def test_network_connectivity(self) -> Tuple[bool, str]:
        """Testa la connettività di rete"""
        self.logger.info("Testing network connectivity...")
        
        try:
            import requests
            
            # Test connessione a Spotify API
            response = requests.get('https://api.spotify.com', timeout=10)
            
            if response.status_code in [200, 401]:  # 401 è normale senza auth
                return True, "Connettività di rete OK"
            else:
                return False, f"Errore connessione: HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Timeout connessione di rete"
        except requests.exceptions.ConnectionError:
            return False, "Errore connessione di rete"
        except Exception as e:
            return False, f"Errore rete: {str(e)}"
    
    def is_raspberry_pi(self) -> bool:
        """Verifica se il sistema è un Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'BCM' in cpuinfo or 'ARM' in cpuinfo
        except:
            return False
    
    def run_all_tests(self) -> Dict[str, Tuple[bool, str]]:
        """Esegue tutti i test"""
        tests = [
            ('Python Dependencies', self.test_python_dependencies),
            ('Configuration', self.test_configuration),
            ('Environment File', self.test_env_file),
            ('File Permissions', self.test_file_permissions),
            ('Network Connectivity', self.test_network_connectivity),
            ('Audio System', self.test_audio_system),
            ('GPIO Setup', self.test_gpio_setup),
            ('Web Interface', self.test_web_interface),
            ('Spotify Connection', self.test_spotify_connection)
        ]
        
        results = {}
        
        print("\n=== SPOTIFY RASPBERRY PI CONTROLLER - SYSTEM TEST ===")
        print(f"Sistema: {'Raspberry Pi' if self.is_raspberry_pi() else 'Altro sistema'}")
        print("\n")
        
        for test_name, test_func in tests:
            print(f"🔍 {test_name}...", end=" ")
            
            try:
                success, message = test_func()
                results[test_name] = (success, message)
                
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"❌ {message}")
                    
            except Exception as e:
                results[test_name] = (False, f"Errore test: {str(e)}")
                print(f"❌ Errore test: {str(e)}")
        
        # Riepilogo
        print("\n" + "="*60)
        passed = sum(1 for success, _ in results.values() if success)
        total = len(results)
        
        print(f"Test completati: {passed}/{total}")
        
        if passed == total:
            print("🎉 Tutti i test sono passati! Il sistema è pronto.")
        else:
            print("⚠️  Alcuni test sono falliti. Controlla i messaggi sopra.")
            
            # Mostra solo i test falliti
            print("\nTest falliti:")
            for test_name, (success, message) in results.items():
                if not success:
                    print(f"  ❌ {test_name}: {message}")
        
        return results

def main():
    """Funzione principale"""
    tester = SystemTester()
    results = tester.run_all_tests()
    
    # Exit code basato sui risultati
    failed_tests = [name for name, (success, _) in results.items() if not success]
    
    if failed_tests:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()