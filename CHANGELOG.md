# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/),
e il progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

---

## [2.0.0] — 2026-07-21

### 🚀 Riscrittura completa

Riscrittura totale dell'integrazione con passaggio da configurazione
YAML a configurazione interamente via UI.

### Aggiunto

- **Config Subentries**: ogni dispositivo (luce, switch, cover, climate,
  sensore, binary_sensor, button) è ora un sotto-elemento del config entry
  del gateway, configurabile e modificabile via UI
- **Config flow per il gateway**: setup guidato con test di connessione,
  supporto SSDP per il rilevamento automatico
- **Reconfigure flow**: possibilità di modificare IP, porta e password del
  gateway senza eliminarlo e ricrearlo
- **Coordinator con riconnessione automatica**: il listener OWNd si
  riconnette automaticamente ogni 10 secondi se la connessione cade
- **ConfigEntryNotReady**: se il gateway non è raggiungibile all'avvio,
  HA riprova automaticamente invece di fallire silenziosamente
- **Servizio `myhome.migrate_yaml`**: importa tutti i dispositivi dal
  vecchio file `myhome.yaml` in un colpo solo
- **Servizio `myhome.sync_time`**: sincronizza l'orologio del gateway
- **Servizio `myhome.send_message`**: invia un frame OpenWebNet raw
- **Diagnostics**: export dello stato dell'integrazione per il debug
  (con redazione della password)
- **Piattaforma `binary_sensor`**: supporto per sensori binari
  (movimento, porta, finestra, ecc.) con WHO e valori ON/OFF configurabili
- **Piattaforma `button`**: invio di frame OpenWebNet personalizzati
  tramite pressione di un button in HA
- **Polling iniziale per-entity**: ogni dispositivo richiede il proprio
  stato al gateway al momento dell'aggiunta, con timeout e gestione errori
- **Traduzioni italiane** complete per config flow, subentries e servizi
- **`services.yaml`** per la visualizzazione corretta dei servizi nella UI

### Modificato

- **`manifest.json`**: `iot_class` corretto da `local_polling` a
  `local_push` (l'integrazione usa un event listener persistente)
- **`manifest.json`**: dipendenza aggiornata a `OWNd==0.7.49`
- **Device registry**: `manufacturer` e `model` sono ora sempre stringhe
  (risolve il warning `passes a non-string value of type list`)
- **Task management**: sostituito `hass.loop.create_task()` con
  `entry.async_create_background_task()` (task legati al ciclo di vita
  del config entry)
- **State updates**: sostituito `async_schedule_update_ha_state()` con
  `async_write_ha_state()`
- **Timeout**: sostituito `async_timeout` con `asyncio.timeout()`
  (Python 3.11+)
- **DeviceInfo**: uso della dataclass `DeviceInfo` al posto di dizionari
- **Servizi**: registrati una sola volta in `async_setup()` invece che
  in `async_setup_entry()` (corretto con config entry multipli)
- **Architettura**: `hass.data[DOMAIN]` sostituito con `entry.runtime_data`
- **Log**: i timeout del polling iniziale sono ora a livello DEBUG
  invece di ERROR

### Rimosso

- **`myhome.yaml`**: non più necessario, tutta la configurazione è via UI
- **`validate.py`**: la validazione è ora gestita dal config flow con
  voluptuous
- **`gateway.py`**: la logica è confluita in `coordinator.py`
- **`myhome_device.py`**: la logica è confluita in `entity.py`
- **`CONNECTION_CLASS`**: costante deprecata rimossa dal config flow
- **`CONFIG_SCHEMA`**: non più necessario (integrazione config-entry-only)

### Risolto

- Warning `passes a non-string value of type list as manufacturer to the
  device registry` (bloccante in HA 2026.12.0)
- Errori ripetuti `Could not send message *#1*XX##` all'avvio (il polling
  avveniva prima che la connessione fosse stabilita)
- Task orfani al reload/unload del config entry
- Servizi sovrascritti con config entry multipli

### Compatibilità

- Richiede Home Assistant **2025.4+** (Config Subentries)
- Testato su Home Assistant **2026.7.2**
- Compatibile con Python **3.13 / 3.14**
- Nessun pattern deprecato: compatibile con HA **2026.12**

---

## [1.x] — Versioni precedenti

- Configurazione dispositivi via file YAML esterno (`/config/myhome.yaml`)
- Config flow solo per il gateway
- Dipendenza da `async_timeout`
- Uso di `hass.loop.create_task()`
- `manufacturer` passato come lista al device registry
- Polling iniziale globale con errori ERROR nei log

---

[2.0.0]: https://github.com/<TUO-USERNAME>/MyHOME/releases/tag/v2.0.0
