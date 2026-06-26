# mood

Prompt → Bild (Stable Diffusion, GPU) → ASCII im Terminal. Ein kleines CLI-Tool,
eine Datei. Modelle kommen automatisch von HuggingFace; lokale Single-Files
(ComfyUI-Stil) werden bevorzugt, wenn vorhanden.

```
   ▒▒▓▓███▓▓▓▓▒▒▒▒
   ▒▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒     prompt rein, ascii raus
```

## Setup

```sh
uv sync
```

Lädt torch (CUDA), diffusers, transformers in ein isoliertes venv.
GPU empfohlen (getestet auf RTX 3090); läuft via CPU-Offload auch mit wenig VRAM.

### Oder per Docker (GPU)

Braucht NVIDIA-Treiber + nvidia-container-toolkit. Modelle landen auf dem Host in
`./models` (per `MODELS_DIR` überschreibbar) und bleiben erhalten.

```sh
docker compose build
docker compose run --rm mood "a red sports car, studio light"   # One-Shot
docker compose up                                                # Listener (Port 8765)
```

Beim ersten Lauf wird das Modell von HuggingFace nach `./models` geladen — der
Fortschritt wird angezeigt (mehrere GB, kein Hänger).

## Nutzung

```sh
uv run mood.py "a red sports car, studio light"
uv run mood.py "neon city at night" --ramp blocks --color cyan
uv run mood.py "portrait" --steps 30 --seed 42 --save out.png
```

Beim ersten Lauf lädt diffusers das Modell von HuggingFace (einmalig, gecached).

Ausgabegröße (ASCII): ohne Angabe **Fullscreen** (Terminalgröße).

```sh
uv run mood.py "..." --width 60 --height 22   # fester Rahmen, aspect-korrekt gefittet
```

## Optionen

| Flag | Default | Zweck |
|------|---------|-------|
| `--model` | `sdxl` | `sdxl`, `sd15`, `flux`*, `qwen`* (*experimentell) |
| `--steps` | je Modell | Inference-Steps |
| `--size WxH` | je Modell | **Generierungs**auflösung (Pixel) |
| `--width` / `--height` | Terminal | **Ausgabe**rahmen (Zeichen), sonst Fullscreen |
| `--seed` | random | Reproduzierbarkeit |
| `--neg` | – | Negativ-Prompt (SDXL/SD1.5) |
| `--lora` | – | LoRA-Kurzname (z.B. `vaultboy`) oder `.safetensors`-Pfad |
| `--lora-scale` | 0.85 | LoRA-Stärke |
| `--ramp` | `acid` | `acid` ░▒▓█, `blocks` ▁▂▃▄▅▆▇█, `minimal`, `soft`, `ink`, `detailed`, `classic` |
| `--color` | `mono` | `mono`, `amber`, `cyan`, `green`, `white` |
| `--invert` / `--contrast` | – | Helligkeit umkehren / Auto-Kontrast |
| `--save PATH.png` | – | Bild zusätzlich als PNG |
| `--render IMG` | – | nur ein Bild als ASCII zeigen (kein GPU) |
| `-v` | – | Lade-Logs & Progress anzeigen |

## Konfiguration (Env)

Alle Defaults via `MOOD_*`-Variablen überschreibbar. Eine `.env` neben `mood.py`
wird automatisch geladen (kopiere `.env.example` → `.env`). Vorrang:
CLI-Flag > Shell-Env > `.env` > eingebauter Default.

| Variable | Default | Zweck |
|----------|---------|-------|
| `MOOD_MODELS_ROOT` | – | Ordner lokaler Single-Files; gesetzt → bevorzugt vor HF |
| `MOOD_LORA_DIR` | `~/.cache/mood/loras` | wohin LoRAs geladen werden |
| `MOOD_MODEL` / `MOOD_RAMP` / `MOOD_PROMPT` | s.o. | Defaults |
| `MOOD_PORT` / `MOOD_HOST` | `8765` / `127.0.0.1` | Loop/Bridge |
| `HF_HOME` | `~/.cache/huggingface` | HF-Modell-Cache |

## Modelle & LoRAs

- **sdxl / sd15** – getestet. `sdxl` = SDXL Base, `sd15` = DreamShaper 8.
- **flux / qwen** – experimentell (große/gated Repos, ungetestet).
- Lokaler Override: `MOOD_MODELS_ROOT` setzen; existiert dort die in `mood.py`
  hinterlegte Datei, wird sie statt HF genutzt (schnell, kein Download).
- **LoRAs**: Kurznamen in `mood.py` (`LORAS`) mit Download-URL; fehlt die Datei,
  wird sie automatisch geladen. `vaultboy` = Fallout-Vault-Boy-Stil (SD1.5).

## Loop-Modus (`::`)

Enthält der Prompt `::`, startet ein TCP-Server: Pipeline bleibt geladen, jede
eingehende Textzeile ersetzt `::` und generiert neu. CTRL-C beendet.

```sh
# Terminal 1 — Server:
uv run mood.py "vault boy, ::, retro poster style" --model sd15 --lora vaultboy --ramp blocks --contrast
# Terminal 2 — Prompts schicken:
echo "smiling" | nc 127.0.0.1 8765
```

Das Bild erscheint in Terminal 1; das ASCII wird auch an den Sender zurückgeschickt.

## MCP-Bridge (`-m`) — „Ausgabemedium für Gefühle"

Dünne Bridge ohne eigene Pipeline: leitet an den laufenden Listener weiter. Ein
MCP-Client (z.B. Claude Code) startet sie headless; das Bild erscheint in deinem
Listener-Terminal. Das Tool **`feel(emotion)`** ist so beschrieben, dass das LLM
es proaktiv nutzt, um seine aktuelle Stimmung zu zeigen.

```sh
# 1) Listener starten (siehe oben).
# 2) Bridge registrieren:
claude mcp add mood --scope user -- \
  /ABS/PFAD/.venv/bin/python /ABS/PFAD/mood.py -m --port 8765
```

`feel` gibt standardmäßig nur `"ok"` zurück (das Bild geht aufs Display, nicht in
den Chat); mit `return_ascii=true` liefert es das ASCII zurück.

## Lizenz

MIT — siehe `LICENSE`.
