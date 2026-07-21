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
