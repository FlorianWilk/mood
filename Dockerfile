# mood — GPU-Container. torch-cu121-Wheels bündeln die CUDA-Libs; es braucht nur
# den NVIDIA-Treiber auf dem Host + nvidia-container-toolkit (Start mit --gpus all).
FROM python:3.11-slim

# uv (Paketmanager)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Modelle & LoRAs liegen auf einem gemounteten Host-Volume (siehe compose).
# Kein MOOD_MODELS_ROOT -> Modelle kommen von HuggingFace und landen unter HF_HOME.
ENV HF_HOME=/models/hf \
    MOOD_LORA_DIR=/models/loras \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Erst Metadaten + Code, dann Dependencies (torch etc. via uv).
COPY pyproject.toml README.md LICENSE mood.py ./
RUN uv sync

EXPOSE 8765
ENTRYPOINT ["uv", "run", "mood.py"]
