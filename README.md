# BTicino MyHOME per Home Assistant

Integrazione custom per Home Assistant che consente di controllare gli impianti
domotici **BTicino MyHOME** (protocollo OpenWebNet) tramite gateway
MyHOME Server / MH200N / F452V / F453V e compatibili.

> **Versione 2.0** — Riscrittura completa con configurazione interamente via UI.
> Non richiede più alcun file YAML.

---

## Funzionalità

- 🔌 **Connessione locale** al gateway via TCP (porta 20000 di default)
- 📡 **Event listener persistente** con riconnessione automatica
- 🏠 **Configurazione via UI** — gateway e dispositivi si gestiscono da
  *Impostazioni → Dispositivi e servizi*
- 📦 **Config Subentries** — ogni dispositivo è un sotto-elemento del gateway,
  modificabile singolarmente
- 🔄 **Migrazione automatica** dal vecchio file `myhome.yaml` (v1.x → v2.0)
- 🩺 **Diagnostics** — esporta lo stato dell'integrazione per il debug

### Piattaforme supportate

| Piattaforma | Descrizione | Esempi |
|---|---|---|
| `light` | Luci ON/OFF e dimmerabili | BMSW1005, F418U2 |
| `switch` | Prese e uscite relè | BMSW1005 |
| `cover` | Tapparelle e tende (anche con posizione) | F411/4 |
| `climate` | Zone termoregolate | F430R8 |
| `sensor` | Sensori di potenza | F520 |
| `binary_sensor` | Sensori binari (movimento, porta, finestra…) | — |
| `button` | Invio frame OpenWebNet personalizzati | — |

---

## Requisiti

- Home Assistant **2025.4** o superiore (per il supporto ai Config Subentries)
- Python **3.13+** (incluso in HA 2026.x)
- Un gateway BTicino MyHOME raggiungibile sulla rete locale
- La password OpenWebNet del gateway (default: `12345`)

### Dipendenze

- [OWNd](https://pypi.org/project/OWNd/) `0.7.49` — libreria di comunicazione
  OpenWebNet (installata automaticamente)

---

## Installazione

### Via HACS (consigliato)

1. Apri **HACS → Integrazioni → ⋮ → Repository personalizzati**
2. Aggiungi l'URL del fork:
   ```
   https://github.com/<TUO-USERNAME>/MyHOME
   ```
3. Cerca **"BTicino MyHOME"** e installa
4. Riavvia Home Assistant

### Manuale

1. Copia la cartella `custom_components/myhome/` nella tua directory
   `config/custom_components/`
2. Riavvia Home Assistant

---

## Configurazione

### 1. Aggiungi il gateway

1. Vai in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**
2. Cerca **"MyHOME"** (o "BTicino MyHOME")
3. Compila il form:

   | Campo | Esempio |
   |---|---|
   | Nome gateway | `myhomeserver1` |
   | Indirizzo IP | `192.168.40.14` |
   | Porta | `20000` |
   | Password | `12345` |
   | MAC | `00:03:50:86:6B:6C` |

4. Ripeti per ogni gateway (es. un secondo appartamento)

> Il gateway viene anche rilevato automaticamente via **SSDP** se presente
> sulla rete.

### 2. Aggiungi i dispositivi

1. Nella pagina dell'integrazione, clicca sul gateway → **Aggiungi sotto-elemento**
2. Scegli il tipo (Luce, Switch, Tapparella, Termostato, Sensore, ecc.)
3. Compila i campi specifici:
   - **Where**: l'indirizzo A/PL del dispositivo (es. `23`, `0115`, `0010`)
   - **Nome**: il nome visualizzato in HA
   - Campi opzionali: dimmerabile, advanced, zona, classe, produttore, modello

### 3. Migrazione da v1.x (YAML)

Se hai già un file `/config/myhome.yaml` dalla versione precedente:

1. Installa la v2.0 e aggiungi i gateway via UI (punto 1)
2. Vai in **Strumenti per sviluppatori → Servizi**
3. Esegui il servizio **`myhome.migrate_yaml`**
4. Tutti i dispositivi vengono importati automaticamente come subentries
5. Verifica in **Impostazioni → MyHOME → Config entry → Sotto-elementi**
6. Cancella `/config/myhome.yaml`

---

## Servizi

| Servizio | Descrizione |
|---|---|
| `myhome.sync_time` | Sincronizza l'orologio del gateway con HA |
| `myhome.send_message` | Invia un frame OpenWebNet raw al gateway |
| `myhome.migrate_yaml` | Importa i dispositivi dal vecchio `myhome.yaml` |

### Esempio: invio frame raw

```yaml
service: myhome.send_message
data:
  gateway_mac: "00:03:50:86:6B:6C"
  message: "*1*1*21##"
```

---

## Formato degli indirizzi "Where"

Il protocollo OpenWebNet identifica ogni dispositivo con un indirizzo
**A/PL** (Ambiente / Punto Luce):

| Formato | Significato | Esempio |
|---|---|---|
| `23` | PL 23, nessun ambiente | Luce semplice |
| `0115` | A=01, PL=15 | Luce in ambiente 1 |
| `0010` | A=00, PL=10 | Luce in ambiente 0 |

Per i **termostati**, il campo `where` corrisponde al numero di **zona**
(es. `1`, `2`, `3`…).

---

## Note sulla compatibilità

- ✅ HA **2026.7.x** — testato
- ✅ Python **3.13 / 3.14** — compatibile
- ⚠️ Il vecchio warning `manufacturer as list` è **risolto**
- ⚠️ I vecchi errori `Could not send message *#1*XX##` sono **risolti**
  (il polling iniziale ora avviene per-entity dopo la connessione)
- 🔜 Compatibile con HA **2026.12** (nessun pattern deprecato)

---

## Struttura dei file

```
custom_components/myhome/
├── __init__.py          # Setup integrazione, ConfigEntryNotReady
├── manifest.json        # Metadati, dipendenze, SSDP
├── const.py             # Costanti
├── config_flow.py       # Config flow gateway + subentry flow dispositivi
├── coordinator.py       # Connessione OWNd, listener, riconnessione
├── entity.py            # Base entity con DeviceInfo
├── light.py             # Luci ON/OFF e dimmer
├── switch.py            # Prese / relè
├── cover.py             # Tapparelle / tende
├── climate.py           # Termostati / zone
├── sensor.py            # Sensori di potenza
├── binary_sensor.py     # Sensori binari
├── button.py            # Button con frame personalizzato
├── services.py          # Servizi (sync_time, send_message, migrate_yaml)
├── services.yaml        # Descrizioni servizi per la UI
├── diagnostics.py       # Export diagnostico
├── migrate_yaml.py      # Script migrazione da v1.x
├── strings.json         # Traduzioni (fallback)
└── translations/
    └── it.json          # Traduzioni italiane
```

---

## Troubleshooting

### Il gateway non si connette

- Verifica che l'IP e la porta siano corretti
- Verifica la password OpenWebNet (default `12345`)
- Assicurati che il gateway sia raggiungibile:
  ```bash
  ping 192.168.40.14
  ```
- L'integrazione riprova automaticamente ogni 10 secondi

### Un dispositivo non risponde

- Verifica il campo **Where** nel subentry
- Controlla i log: **Strumenti per sviluppatori → Log** → filtra `myhome`
- Usa il servizio `myhome.send_message` per testare il frame manualmente

### I log mostrano errori di altre integrazioni

Gli errori `proxmoxve`, `shelly`, `myskoda`, `opnsense`, `sonoff`,
`electrolux_status`, `petwalk`, `ksenia_lares`, `smartthings_find` presenti
nei log **non** sono correlati a questa integrazione.

---

## Crediti

- Integrazione originale: [anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME)
- Libreria OWNd: [anotherjulien/OWNd](https://pypi.org/project/OWNd/)
- Riscrittura v2.0: questo fork

---

## Licenza

Vedi [LICENSE](LICENSE).
```

---
