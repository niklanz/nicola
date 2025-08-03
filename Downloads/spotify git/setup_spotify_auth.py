#!/usr/bin/env python3
"""
Script per configurare l'autenticazione Spotify manualmente
"""

import os
import sys
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
import spotipy

def setup_spotify_auth():
    """Configura l'autenticazione Spotify"""
    
    # Carica variabili d'ambiente
    load_dotenv()
    
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    
    if not all([client_id, client_secret, redirect_uri]):
        print("[ERROR] Errore: Variabili d'ambiente Spotify mancanti!")
        print("Assicurati che .env contenga:")
        print("- SPOTIFY_CLIENT_ID")
        print("- SPOTIFY_CLIENT_SECRET")
        print("- SPOTIFY_REDIRECT_URI")
        return False
    
    print("[INFO] Configurazione autenticazione Spotify")
    print(f"Client ID: {client_id}")
    print(f"Redirect URI: {redirect_uri}")
    print()
    
    # Configura OAuth
    scope = "playlist-read-collaborative playlist-read-private user-modify-playback-state user-read-currently-playing user-read-playback-state"
    
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=".spotify_cache"
    )
    
    print("[STEPS] Passi per completare l'autenticazione:")
    print()
    print("1. Assicurati che nel tuo account Spotify Developer:")
    print(f"   - L'app abbia come Redirect URI: {redirect_uri}")
    print()
    print("2. Apri questo URL nel browser:")
    
    # Genera URL di autorizzazione
    auth_url = sp_oauth.get_authorize_url()
    print(f"   {auth_url}")
    print()
    print("3. Dopo aver autorizzato l'app, verrai reindirizzato a un URL che inizia con:")
    print(f"   {redirect_uri}?code=...")
    print()
    print("4. Copia l'intero URL e incollalo qui sotto:")
    
    try:
        # Chiedi all'utente di incollare l'URL di callback
        callback_url = input("URL di callback: ").strip()
        
        if not callback_url.startswith(redirect_uri):
            print("[ERROR] URL non valido!")
            return False
        
        # Estrai il codice dall'URL
        if '?code=' in callback_url:
            code = callback_url.split('?code=')[1].split('&')[0]
        else:
            print("[ERROR] Codice di autorizzazione non trovato nell'URL!")
            return False
        
        print(f"\n[KEY] Codice estratto: {code[:20]}...")
        
        # Ottieni il token
        print("\n[WAIT] Ottenimento token di accesso...")
        token_info = sp_oauth.get_access_token(code)
        
        if token_info:
            print("[SUCCESS] Token ottenuto con successo!")
            
            # Testa la connessione
            sp = spotipy.Spotify(auth_manager=sp_oauth)
            user = sp.current_user()
            print(f"\n[USER] Utente autenticato: {user['display_name']} ({user['id']})")
            
            # Testa i dispositivi
            devices = sp.devices()
            print(f"\n[DEVICES] Dispositivi disponibili: {len(devices['devices'])}")
            for device in devices['devices']:
                status = "[ACTIVE]" if device['is_active'] else "[INACTIVE]"
                print(f"   - {device['name']} ({device['type']}) {status}")
            
            print("\n[SUCCESS] Autenticazione Spotify configurata correttamente!")
            print("\n[TIPS] Suggerimenti:")
            if not devices['devices']:
                print("   - Nessun dispositivo Spotify attivo trovato")
                print("   - Apri Spotify su un dispositivo (PC, telefono, ecc.)")
                print("   - Avvia la riproduzione di una canzone")
                print("   - Riprova a usare l'applicazione")
            else:
                print("   - L'autenticazione è completa")
                print("   - Ora puoi usare l'applicazione normalmente")
                print("   - Se non senti audio, controlla le impostazioni audio del Raspberry Pi")
            
            return True
        else:
            print("[ERROR] Errore nell'ottenimento del token!")
            return False
            
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Operazione annullata dall'utente")
        return False
    except Exception as e:
        print(f"\n[ERROR] Errore: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("    SPOTIFY RASPBERRY PI - SETUP AUTENTICAZIONE")
    print("=" * 60)
    print()
    
    success = setup_spotify_auth()
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] SETUP COMPLETATO CON SUCCESSO!")
        print("\nOra puoi avviare l'applicazione principale:")
        print("python3 main.py")
    else:
        print("[FAILED] SETUP FALLITO!")
        print("\nControlla la configurazione e riprova.")
    print("=" * 60)