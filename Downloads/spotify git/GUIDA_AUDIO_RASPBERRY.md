# Guida: Configurazione Audio Raspberry Pi per Spotify Connect

## Problema
Il dispositivo Raspberry Pi non appare nell'app Spotify per la riproduzione audio.

## Soluzioni

### 1. Verifica Configurazione Audio

#### Controlla dispositivi audio disponibili:
```bash
aplay -l
```

#### Testa l'audio:
```bash
speaker-test -t wav -c 2
```

#### Configura output audio (se necessario):
```bash
# Per jack audio 3.5mm
sudo raspi-config
# Vai in Advanced Options > Audio > Force 3.5mm jack

# Oppure via comando
sudo amixer cset numid=3 1
```

### 2. Configurazione ALSA

Crea/modifica il file `~/.asoundrc`:
```bash
cat > ~/.asoundrc << EOF
pcm.!default {
    type hw
    card 0
    device 0
}
ctl.!default {
    type hw
    card 0
}
EOF
```

### 3. Avvio Librespot

#### Metodo 1: Script automatico
```bash
./start_librespot.sh
```

#### Metodo 2: Comando manuale
```bash
librespot \
    --name "RaspberryPi" \
    --bitrate 320 \
    --device-type speaker \
    --backend alsa \
    --mixer softvol \
    --initial-volume 70 \
    --volume-ctrl linear \
    --enable-volume-normalisation
```

### 4. Configurazione .env

Verifica che nel file `.env` sia configurato:
```bash
# Librespot settings
LIBRESPOT_NAME=RaspberryPi
LIBRESPOT_BITRATE=320
LIBRESPOT_DEVICE_TYPE=speaker
LIBRESPOT_BACKEND=alsa
```

### 5. Risoluzione Problemi Comuni

#### Problema: "No audio devices found"
```bash
# Riavvia servizio audio
sudo systemctl restart alsa-state
sudo systemctl restart pulseaudio

# Oppure ricarica moduli audio
sudo modprobe snd_bcm2835
```

#### Problema: "Permission denied" per audio
```bash
# Aggiungi utente al gruppo audio
sudo usermod -a -G audio $USER

# Riavvia per applicare le modifiche
sudo reboot
```

#### Problema: Dispositivo non appare in Spotify
1. Assicurati che librespot sia in esecuzione:
   ```bash
   ps aux | grep librespot
   ```

2. Verifica la rete (stesso WiFi di Spotify):
   ```bash
   ip route show
   ```

3. Riavvia librespot:
   ```bash
   pkill librespot
   ./start_librespot.sh
   ```

### 6. Test Completo

#### Script di test audio:
```bash
#!/bin/bash
echo "=== Test Audio Raspberry Pi ==="
echo "1. Dispositivi audio disponibili:"
aplay -l
echo ""
echo "2. Test speaker:"
speaker-test -t wav -c 2 -l 1
echo ""
echo "3. Stato librespot:"
ps aux | grep librespot
echo ""
echo "4. Porte in ascolto:"
netstat -tlnp | grep librespot
```

### 7. Configurazione Avanzata

#### Per audio USB:
```bash
# Trova il dispositivo USB
aplay -l

# Modifica .asoundrc per usare dispositivo USB (esempio card 1)
cat > ~/.asoundrc << EOF
pcm.!default {
    type hw
    card 1
    device 0
}
ctl.!default {
    type hw
    card 1
}
EOF
```

#### Per audio HDMI:
```bash
# Forza output HDMI
sudo amixer cset numid=3 2

# Oppure in /boot/config.txt
echo "hdmi_force_hotplug=1" | sudo tee -a /boot/config.txt
echo "hdmi_drive=2" | sudo tee -a /boot/config.txt
```

### 8. Servizio Automatico

Per avviare librespot automaticamente all'avvio:

```bash
# Crea servizio systemd per librespot
sudo tee /etc/systemd/system/librespot.service > /dev/null << EOF
[Unit]
Description=Spotify Connect (librespot)
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=pi
ExecStart=/home/pi/.cargo/bin/librespot --name RaspberryPi --bitrate 320 --device-type speaker --backend alsa --mixer softvol --initial-volume 70
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Abilita e avvia il servizio
sudo systemctl daemon-reload
sudo systemctl enable librespot
sudo systemctl start librespot
```

### 9. Verifica Finale

1. **Librespot attivo**: `sudo systemctl status librespot`
2. **Audio funzionante**: `speaker-test -t wav -c 2 -l 1`
3. **Dispositivo visibile**: Apri Spotify e cerca "RaspberryPi" nei dispositivi
4. **Test riproduzione**: Avvia una canzone e seleziona il dispositivo Raspberry

### Note Importanti

- Il Raspberry Pi e il dispositivo Spotify devono essere sulla stessa rete
- Librespot deve essere in esecuzione prima di aprire Spotify
- Alcuni router potrebbero bloccare la discovery, prova a riavviare il router
- Se usi un DAC USB, assicurati che sia riconosciuto con `lsusb` e `aplay -l`