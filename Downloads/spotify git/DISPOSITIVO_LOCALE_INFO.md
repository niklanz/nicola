# Dispositivo Spotify Locale - Raspberry Pi

## Problema Risolto

Il Raspberry Pi ora appare nella lista dei dispositivi disponibili nell'interfaccia web, anche quando non è visibile nell'app Spotify ufficiale.

## Modifiche Apportate

### 1. Aggiunta Dispositivo Locale
- Il sistema ora rileva automaticamente se librespot è in esecuzione sul Raspberry Pi
- Se librespot è attivo, aggiunge "RaspberryPi (Locale)" alla lista dei dispositivi
- Il dispositivo locale ha ID speciale `local_librespot`

### 2. Controllo Volume Locale
- Quando si seleziona il dispositivo locale, il controllo volume usa `amixer` direttamente
- Non dipende più dall'API Spotify per il controllo del volume

### 3. Gestione Controlli
- I controlli play/pause/next/previous sono riconosciuti per il dispositivo locale
- I comandi vengono loggati ma non causano errori

## Come Utilizzare

1. **Accedi all'interfaccia web**: http://raspberrypi.local:8081 (o http://10.0.4.141:8081)

2. **Verifica che librespot sia attivo**:
   ```bash
   ssh admin@10.0.4.141
   ps aux | grep librespot
   ```

3. **Nell'interfaccia web**:
   - Vai alla sezione "Devices"
   - Dovresti vedere "RaspberryPi (Locale)" nella lista
   - Seleziona questo dispositivo

4. **Controllo Audio**:
   - Il volume può essere controllato direttamente dall'interfaccia
   - Per la riproduzione, usa l'app Spotify su un altro dispositivo e seleziona "RaspberryPi" come output

## Stato Attuale

- ✅ Librespot attivo sul Raspberry Pi
- ✅ Dispositivo visibile via mDNS (`dns-sd` conferma la presenza)
- ✅ Interfaccia web aggiornata con supporto dispositivo locale
- ✅ Controllo volume locale funzionante

## Risoluzione Problemi

### Se il dispositivo locale non appare:
1. Verifica che librespot sia in esecuzione:
   ```bash
   ssh admin@10.0.4.141 'pgrep librespot'
   ```

2. Riavvia librespot se necessario:
   ```bash
   ssh admin@10.0.4.141 'cd ~/spotify-controller && ./start_librespot.sh'
   ```

3. Aggiorna la pagina web

### Se l'app Spotify non vede il dispositivo:
- Il dispositivo è comunque controllabile via interfaccia web
- Prova a riavviare l'app Spotify
- Assicurati di essere sulla stessa rete WiFi

## Note Tecniche

- Il dispositivo locale bypassa l'API Spotify per alcuni controlli
- Il volume è controllato direttamente via `amixer`
- La riproduzione deve essere iniziata da un'app Spotify autenticata
- L'interfaccia web funge da ponte tra l'API Spotify e il dispositivo locale