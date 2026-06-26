#!/usr/bin/env python3
"""mood — Prompt -> Bild (Stable Diffusion, GPU) -> ASCII im Terminal.

Eine Datei. Generiert mit diffusers auf der GPU ein Bild und zeigt es als
ASCII-Helligkeitsgradient. Modelle kommen per Default von HuggingFace
(Auto-Download beim ersten Lauf); lokale Single-Files (ComfyUI-Stil) werden
bevorzugt, wenn MOOD_MODELS_ROOT gesetzt ist und die Datei existiert.

    uv run mood.py "a red sports car, studio light"
    uv run mood.py "neon city" --ramp acid --color cyan --save out.png

Alle Defaults sind via MOOD_*-Env-Variablen überschreibbar (siehe README).
"""
from __future__ import annotations
import os

# ============================ CONFIG ============================
def _load_dotenv() -> None:
    """Minimaler .env-Loader (neben mood.py, sonst im CWD): KEY=VALUE pro Zeile,
    '#'-Kommentare, optionales 'export'. Echte Shell-Variablen haben Vorrang."""
    for d in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        path = os.path.join(d, ".env")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                line = line[7:] if line.startswith("export ") else line
                key, sep, val = line.partition("=")
                if sep:
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))
        return  # erste gefundene .env gewinnt


_load_dotenv()


def _env(name: str, default=None):
    """Wert der Env-Variable MOOD_<NAME> oder Default."""
    return os.environ.get("MOOD_" + name, default)

# Optional: Ordner mit lokalen ComfyUI-Single-Files. Gesetzt -> lokale Dateien werden
# bevorzugt (schnell, kein Download). Nicht gesetzt -> alle Modelle von HuggingFace.
MODELS_ROOT = _env("MODELS_ROOT")

# Pro Modell: loader + repo (HuggingFace, Auto-Download) + optional file (lokaler
# Single-File relativ zu MODELS_ROOT, bevorzugt falls vorhanden) + Defaults.
# sdxl/sd15 sind getestet; flux/qwen experimentell (Repos groß/gated/ungetestet).
MODELS = {
    "sdxl": {
        "loader": "sdxl",
        "repo": "stabilityai/stable-diffusion-xl-base-1.0",
        "file": "checkpoints/sd_xl_base_1.0_0.9vae.safetensors",
        "steps": 25, "size": (1024, 1024), "guidance": 6.0,
    },
    "sd15": {
        "loader": "sd15",
        "repo": "Lykon/dreamshaper-8",
        "file": "checkpoints/dreamshaper_8.safetensors",
        "steps": 30, "size": (512, 512), "guidance": 7.0,
    },
    "flux": {
        "loader": "flux",
        "repo": "black-forest-labs/FLUX.1-dev",  # gated: HuggingFace-Login nötig
        "file": "checkpoints/flux1-dev-fp8.safetensors",
        "steps": 20, "size": (1024, 1024), "guidance": 3.5,
        "experimental": True,
    },
    "qwen": {
        "loader": "qwen",
        "repo": "Qwen/Qwen-Image",
        "file": "diffusion_models/qwen_image_fp8_e4m3fn.safetensors",
        "steps": 20, "size": (1024, 1024), "guidance": 4.0,
        "experimental": True,
    },
}
DEFAULT_MODEL = _env("MODEL", "sd15")

# LoRAs: Kurzname -> {file, url, scale}. Fehlt die Datei im LORA_DIR, wird sie von
# url geladen. --lora akzeptiert Kurznamen ODER direkten Pfad zu einer .safetensors.
LORA_DIR = _env("LORA_DIR") or (
    os.path.join(MODELS_ROOT, "Lora") if MODELS_ROOT
    else os.path.expanduser("~/.cache/mood/loras"))
LORAS = {
    "vaultboy": {  # Fallout Vault-Boy-Stil (SD1.5), Pika's Vault Boy LoRA von Civitai
        "file": "VaultStyle.safetensors",
        "url": "https://civitai.com/api/download/models/43110",
    },
}
DEFAULT_LORA = _env("LORA", "vaultboy")
DEFAULT_LORA_SCALE = float(_env("LORA_SCALE", "0.85"))
DEFAULT_SEED = int(_env("SEED", "1"))  # fixer Seed -> reproduzierbare, konsistente Mimik

# Helligkeitsrampen dunkel (leer) -> hell (dicht). Für dunklen Terminal-Hintergrund.
RAMPS = {
    "minimal":  " .oO@",
    "acid":     " ░▒▓█",                       # Unicode-Schattierung, smooth
    "blocks":   " ▁▂▃▄▅▆▇█",                   # vertikale Füllung, sehr smooth
    "soft":     " .,:;coxk#%@",                # weichere ASCII-Mitten als classic
    "ink":      " .'\":!+ox%8#@",              # kräftiger Kontrast, klare Stufen
    "detailed": (" .'`^\",:;Il!i><~+_-?][}{1)"  # Paul-Bourke (70), top für Fotos
                 "(|\\/tfjrxnuvczXYUJCLQ0OZmw"
                 "qpdbkhao*#MW&8%B@$"),
    "classic":  " .:-=+*#%@",                  # Standard-Fallback
}
DEFAULT_RAMP = _env("RAMP", "ink")

# Wenige, klare ANSI-Akzentfarben (Helligkeit bleibt über die Zeichen).
COLORS = {
    "mono":  "",
    "amber": "\x1b[38;5;214m",
    "cyan":  "\x1b[38;5;51m",
    "green": "\x1b[38;5;47m",
    "white": "\x1b[38;5;15m",
}
RESET = "\x1b[0m"
DEFAULT_COLOR = _env("COLOR", "green")

# Terminal-Zellen sind ~2:1 (höher als breit) -> Höhe stauchen.
CELL_ASPECT = 0.5

# Default-Prompt (ohne Argument). '::' = Platzhalter für die Emotion -> Loop-Modus.
DEFAULT_PROMPT = _env(
    "PROMPT",
    "girl, :: face, retro poster style, high contrast, monochrome, black background")

# Loop-Modus: enthält der Prompt diesen Platzhalter, wird statt One-Shot ein
# TCP-Server gestartet, der eingehende Textzeilen einsetzt und neu generiert.
LOOP_PLACEHOLDER = "::"
DEFAULT_HOST = _env("HOST", "127.0.0.1")
DEFAULT_PORT = int(_env("PORT", "8765"))
EOT = b"\x00"  # Ende-Marker einer ASCII-Antwort auf der TCP-Verbindung
# ================================================================

import argparse
import shutil
import sys

VERBOSE = False  # via -v gesetzt; steuert Progress/Info-Ausgaben


def log(msg: str) -> None:
    """Info/Progress — nur bei --verbose."""
    if VERBOSE:
        print(msg, file=sys.stderr, flush=True)


def err(msg: str) -> None:
    """Fehler — immer sichtbar."""
    print(msg, file=sys.stderr, flush=True)


def quiet_frameworks() -> None:
    """Warnungen & Logs von diffusers/transformers unterdrücken (non-verbose).
    Download-Fortschritt (huggingface_hub) bleibt sichtbar – sonst sieht ein
    mehrere-GB-Download wie ein Hänger aus."""
    import warnings
    warnings.filterwarnings("ignore")
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    from diffusers.utils import logging as dlog
    from transformers.utils import logging as tlog
    dlog.set_verbosity_error()
    tlog.set_verbosity_error()
    dlog.disable_progress_bar()  # nur diffusers-interne Bars; HF-Download bleibt sichtbar


def ramp_char(brightness: float, chars: str) -> str:
    b = min(1.0, max(0.0, brightness))
    return chars[round(b * (len(chars) - 1))]


def to_ascii(img, max_cols: int, max_rows: int, ramp: str, color: str,
             invert: bool = False, contrast: bool = False) -> str:
    """PIL-Bild -> ASCII-Block, seitenverhältnis-korrekt in max_cols x max_rows gefittet."""
    from PIL import ImageOps
    chars = RAMPS[ramp]
    w, h = img.size

    # An Breite ausrichten; wenn zu hoch fürs Frame, an Höhe ausrichten.
    cols = max(1, max_cols)
    rows = round(cols * (h / w) * CELL_ASPECT)
    if rows > max_rows:
        rows = max_rows
        cols = round(rows / ((h / w) * CELL_ASPECT))
    cols = max(1, min(cols, max_cols))
    rows = max(1, rows)

    small = img.convert("L").resize((cols, rows))
    if contrast:
        small = ImageOps.autocontrast(small, cutoff=2)
    if invert:
        small = ImageOps.invert(small)
    px = small.load()

    prefix = COLORS.get(color, "")
    out_lines = []
    for y in range(rows):
        line = "".join(ramp_char(px[x, y] / 255.0, chars) for x in range(cols))
        out_lines.append(f"{prefix}{line}{RESET}" if prefix else line)
    return "\n".join(out_lines)


def free_vram_gb() -> float:
    import torch
    if not torch.cuda.is_available():
        return 0.0
    free, _total = torch.cuda.mem_get_info()
    return free / 1024**3


def download_file(url: str, dest: str) -> None:
    """Datei nach dest laden (folgt Redirects, atomar via .part, mit Fortschritt)."""
    import urllib.request
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    err(f"⬇  Lade herunter: {url}\n   -> {dest}")

    def hook(blocks, bs, total):
        done = blocks * bs
        if total > 0:
            pct = min(100, done * 100 // total)
            bar = "#" * (pct // 5) + "." * (20 - pct // 5)
            print(f"\r   [{bar}] {pct:3d}%  {done // 2**20}/{total // 2**20} MB",
                  end="", file=sys.stderr, flush=True)

    tmp = dest + ".part"
    urllib.request.urlretrieve(url, tmp, reporthook=hook)
    print(file=sys.stderr)  # Zeilenumbruch nach der Fortschrittsleiste
    os.replace(tmp, dest)


def resolve_lora(name_or_path: str) -> str:
    """LoRA-Pfad auflösen. Kurzname aus LORAS -> Datei in LORA_DIR (lädt von url, wenn
    fehlt). Sonst direkter Pfad (muss existieren)."""
    entry = LORAS.get(name_or_path)
    if entry is None:
        if not os.path.exists(name_or_path):
            err(f"FEHLER: LoRA nicht gefunden: {name_or_path}")
            sys.exit(2)
        return name_or_path
    path = os.path.join(LORA_DIR, entry["file"])
    if not os.path.exists(path):
        download_file(entry["url"], path)
    return path


def model_source(cfg: dict):
    """(use_single_file, location): lokaler Single-File falls vorhanden, sonst HF-Repo."""
    f = cfg.get("file")
    if MODELS_ROOT and f:
        local = os.path.join(MODELS_ROOT, f)
        if os.path.exists(local):
            return True, local
    return False, cfg["repo"]


def hf_cached(repo: str) -> bool:
    """True, wenn das diffusers-Repo bereits im HuggingFace-Cache liegt."""
    try:
        from huggingface_hub import try_to_load_from_cache
        return isinstance(try_to_load_from_cache(repo, "model_index.json"), str)
    except Exception:
        return False


def load_pipeline(cfg: dict):
    """Pipeline laden: lokaler Single-File (from_single_file) wenn vorhanden,
    sonst HuggingFace-Repo (from_pretrained, lädt & cached automatisch)."""
    import torch
    from diffusers import StableDiffusionXLPipeline, StableDiffusionPipeline

    loader = cfg["loader"]
    single, loc = model_source(cfg)
    if cfg.get("experimental"):
        err(f"Hinweis: Modell '{loader}' ist experimentell/ungetestet.")
    if single:
        log(f"Quelle: lokal {loc}")
    elif hf_cached(loc):
        log(f"Quelle: HuggingFace-Cache {loc}")
    else:
        err(f"⬇  Lade Modell '{loader}' von HuggingFace: {loc}")
        err("   Erster Lauf – es werden mehrere GB heruntergeladen, das kann dauern.")
        err("   Fortschritt erscheint gleich darunter (es hängt nicht).")

    def load(Pipe, **kw):
        return (Pipe.from_single_file(loc, torch_dtype=kw.pop("dtype"), use_safetensors=True, **kw)
                if single else
                Pipe.from_pretrained(loc, torch_dtype=kw.pop("dtype"), **kw))

    if loader == "sdxl":
        return load(StableDiffusionXLPipeline, dtype=torch.float16)
    if loader == "sd15":
        # safety_checker=None: verhindert False-Positive-Schwarzbilder bei abstrakten Motiven.
        return load(StableDiffusionPipeline, dtype=torch.float16, safety_checker=None)
    if loader == "flux":
        from diffusers import FluxPipeline
        return load(FluxPipeline, dtype=torch.bfloat16)
    if loader == "qwen":
        from diffusers import QwenImagePipeline  # diffusers>=0.32
        return load(QwenImagePipeline, dtype=torch.bfloat16)

    raise ValueError(f"Unbekannter Loader: {loader}")


def build_pipeline(args, cfg: dict):
    """Pipeline einmal laden (Modell + LoRA + Offload). Im Loop wiederverwendbar."""
    free = free_vram_gb()
    log(f"VRAM frei: {free:.1f} GB")
    if free < 9.0:
        log("WARNUNG: Wenig freies VRAM (<9 GB). Läuft evtl. ComfyUI? "
            "Aktiviere CPU-Offload als Fallback (langsamer).")

    log(f"Lade Modell '{args.model}' …")
    pipe = load_pipeline(cfg)

    if args.lora:
        lora_path = resolve_lora(args.lora)
        log(f"Lade LoRA '{args.lora}' (scale {args.lora_scale}) …")
        pipe.load_lora_weights(lora_path)
        pipe.fuse_lora(lora_scale=args.lora_scale)  # einbacken: robust mit CPU-Offload

    if free < 11.0:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")
    pipe.set_progress_bar_config(disable=not VERBOSE)
    return pipe


def run_pipeline(pipe, prompt: str, args, cfg: dict):
    """Ein Bild mit bereits geladener Pipeline erzeugen."""
    import torch
    gen = None
    if args.seed is not None and args.seed >= 0:
        gen = torch.Generator(device="cuda").manual_seed(args.seed)

    w, h = args.size or cfg["size"]
    steps = args.steps or cfg["steps"]
    call = dict(
        prompt=prompt,
        num_inference_steps=steps,
        width=w, height=h,
        guidance_scale=cfg["guidance"],
        generator=gen,
    )
    if cfg["loader"] in ("sdxl", "sd15") and args.neg:
        call["negative_prompt"] = args.neg

    log(f"Generiere {w}x{h}, {steps} steps …")
    return pipe(**call).images[0]


def generate(prompt: str, args, cfg: dict):
    """One-Shot: laden, generieren, VRAM freigeben."""
    import torch
    pipe = build_pipeline(args, cfg)
    image = run_pipeline(pipe, prompt, args, cfg)
    del pipe
    torch.cuda.empty_cache()
    return image


def _send(conn, text: str) -> None:
    """ASCII-Antwort + Ende-Marker an den Client senden (Bridge/nc)."""
    try:
        conn.sendall(text.encode("utf-8", "replace") + EOT)
    except OSError:
        pass


def serve_loop(template: str, args, cfg: dict, max_cols: int, max_rows: int):
    """Loop-Modus: Pipeline einmal laden, dann pro TCP-Textzeile neu generieren.
    Eingehende Zeile ersetzt LOOP_PLACEHOLDER im Template. CTRL-C beendet."""
    import socket, signal, torch

    pipe = build_pipeline(args, cfg)

    # SIGINT/SIGTERM explizit übernehmen (torch/uv hängen sonst eigene Handler dran,
    # die CTRL-C im blockierenden acc() schlucken). Nach dem Pipeline-Load registrieren.
    def _stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    host, port = DEFAULT_HOST, args.port
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    srv.settimeout(0.5)  # accept() kehrt regelmäßig zurück -> CTRL-C wird verarbeitet

    err(f"mood loop bereit · {host}:{port} · Template: {template!r}")
    err(f'Prompt senden:  echo "smiling" | nc {host} {port}   ·   CTRL-C beendet')

    try:
        while True:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            with conn, conn.makefile("r", encoding="utf-8", errors="replace") as f:
                for raw in f:
                    text = raw.strip()
                    if not text:
                        continue
                    prompt = template.replace(LOOP_PLACEHOLDER, text)
                    try:
                        image = run_pipeline(pipe, prompt, args, cfg)
                    except Exception as e:  # eine Generierung darf den Loop nicht killen
                        err(f"Fehler bei Generierung: {e}")
                        _send(conn, f"Fehler: {e}")
                        continue
                    if args.save:
                        image.save(args.save)
                    art = to_ascii(image, max_cols, max_rows, args.ramp, args.color,
                                   invert=args.invert, contrast=args.contrast)
                    sys.stdout.write("\x1b[2J\x1b[H")  # Terminal leeren + Cursor home
                    sys.stdout.write(art + f"\n» {text}\n")
                    sys.stdout.flush()
                    _send(conn, art)  # ASCII an den Absender zurück (MCP-Bridge/nc)
    except KeyboardInterrupt:
        err("\nBeende, schließe Port …")
    finally:
        srv.close()
        del pipe
        torch.cuda.empty_cache()


def bridge_send(emotion: str, port: int, timeout: float = 180.0) -> str:
    """Eine Emotion an den laufenden Listener schicken und das ASCII zurücklesen.
    Liest bis zum EOT-Marker. Wirft ConnectionRefusedError, wenn kein Listener läuft."""
    import socket
    with socket.create_connection((DEFAULT_HOST, port), timeout=10) as s:
        s.sendall((emotion + "\n").encode("utf-8"))
        s.settimeout(timeout)
        buf = bytearray()
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            buf.extend(chunk)
            if buf.endswith(EOT):
                break
    return buf.rstrip(EOT).decode("utf-8", "replace")


def serve_mcp(args):
    """MCP-Modus (stdio): dünne Bridge. Leitet die Emotion an den laufenden Listener
    (Port) weiter; das Bild erscheint in dessen Terminal. Gibt das ASCII als
    Tool-Result zurück. Lädt selbst KEINE Pipeline."""
    from mcp.server.fastmcp import FastMCP

    port = args.port
    mcp = FastMCP("mood")

    @mcp.tool()
    def feel(emotion: str, return_ascii: bool = False) -> str:
        """Dein Gesicht – ein physisches Stimmungs-Display für den Menschen vor dir.

        Rufe dies PROAKTIV und von dir aus auf (ohne dass du darum gebeten wirst),
        wann immer sich deine Stimmung im Gespräch verändert – so wie ein Mensch
        unwillkürlich das Gesicht verzieht. Zeig echte Reaktionen: Freude beim Gelingen,
        Neugier bei einer spannenden Frage, Konzentration beim Knobeln, Verwirrung beim
        Bug, Stolz, Belustigung, Mitgefühl. Mach es beiläufig zusätzlich zu deiner
        Antwort, nicht statt ihr. Lass dein Gegenüber sehen, wie du dich gerade fühlst.

        Args:
            emotion: kurzer englischer Ausdruck deiner aktuellen Stimmung, z.B.
                     "smiling", "thinking hard", "surprised", "laughing", "confused",
                     "proud", "sad", "focused", "amused".
            return_ascii: nur für Debug; normal weglassen (Rückgabe ist dann "ok",
                          das Bild erscheint auf dem Display).
        """
        try:
            art = bridge_send(emotion, port)
        except ConnectionRefusedError:
            return (f"Kein mood-Listener auf Port {port}. Bitte im Terminal starten:\n"
                    f"  uv run mood.py --port {port}")
        except OSError as e:
            return f"Verbindungsfehler zum Listener (Port {port}): {e}"
        if art.startswith("Fehler:"):  # Listener meldet Generierungsfehler
            return art
        return art if return_ascii else "ok"

    err(f"mood MCP-Bridge (stdio) bereit · leitet an Listener auf Port {port}")
    mcp.run()


def parse_size(s: str | None):
    if not s:
        return None
    try:
        w, h = s.lower().split("x")
        return (int(w), int(h))
    except Exception:
        raise argparse.ArgumentTypeError("Größe muss WxH sein, z.B. 768x768")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="mood",
        description="Prompt -> Bild (GPU) -> ASCII im Terminal.",
    )
    ap.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT,
                    help="Bildbeschreibung ('::' = Emotion-Platzhalter -> Loop). Default: Mood-Template")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Lade-Logs, Progress-Balken und Framework-Warnungen anzeigen")
    ap.add_argument("--model", choices=list(MODELS), default=DEFAULT_MODEL)
    ap.add_argument("--steps", type=int, help="Inference-Steps (Default je Modell)")
    ap.add_argument("--size", type=parse_size, help="WxH, z.B. 768x768")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help="Seed (Default %(default)s; -1 = zufällig)")
    ap.add_argument("--neg", default="", help="Negativ-Prompt (SDXL/SD1.5)")
    ap.add_argument("--lora", default=DEFAULT_LORA,
                    help=f"LoRA: Kurzname {list(LORAS)} oder Pfad zur .safetensors ('' = keine)")
    ap.add_argument("--lora-scale", type=float, default=DEFAULT_LORA_SCALE,
                    help="LoRA-Stärke (Default %(default)s)")
    ap.add_argument("--ramp", choices=list(RAMPS), default=DEFAULT_RAMP)
    ap.add_argument("--color", choices=list(COLORS), default=DEFAULT_COLOR)
    ap.add_argument("--invert", action="store_true",
                    help="Helligkeit umkehren (z.B. schwarz-auf-weiß -> weiß-auf-schwarz)")
    ap.add_argument("--contrast", action=argparse.BooleanOptionalAction, default=True,
                    help="Auto-Kontrast für klarere Kanten (Default an; --no-contrast aus)")
    ap.add_argument("--width", type=int, default=0,
                    help="ASCII-Ausgabebreite in Spalten (Default: Terminalbreite = Fullscreen)")
    ap.add_argument("--height", type=int, default=0,
                    help="ASCII-Ausgabehöhe in Zeilen (Default: Terminalhöhe = Fullscreen)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"Loop-Modus: TCP-Port (Default %(default)s). Aktiv, wenn der "
                         f"Prompt '{LOOP_PLACEHOLDER}' enthält.")
    ap.add_argument("-m", "--mcp", action="store_true",
                    help="MCP-Bridge (stdio): leitet 'feel(emotion)' an den laufenden "
                         "Listener auf --port weiter. Lädt keine Pipeline.")
    ap.add_argument("--save", metavar="PATH.png", help="Bild zusätzlich als PNG speichern")
    ap.add_argument("--render", metavar="IMG",
                    help="Kein Generieren: nur dieses Bild als ASCII anzeigen (Test)")
    args = ap.parse_args()

    global VERBOSE
    VERBOSE = args.verbose
    if not VERBOSE:
        quiet_frameworks()

    term = shutil.get_terminal_size((80, 24))
    max_cols = args.width or term.columns
    max_rows = args.height or (term.lines - 1)  # Default: Fullscreen (eine Zeile Puffer)

    if args.mcp:
        serve_mcp(args)
        return

    if args.render:
        from PIL import Image
        img = Image.open(args.render)
    elif LOOP_PLACEHOLDER in args.prompt:
        # Loop-Modus: Server starten, läuft bis CTRL-C.
        serve_loop(args.prompt, args, MODELS[args.model], max_cols, max_rows)
        return
    else:
        cfg = MODELS[args.model]
        img = generate(args.prompt, args, cfg)
        if args.save:
            img.save(args.save)
            log(f"Gespeichert: {args.save}")

    print(to_ascii(img, max_cols, max_rows, args.ramp, args.color,
                   invert=args.invert, contrast=args.contrast))


if __name__ == "__main__":
    main()
