# ── Stage 1: descarga el modelo (no queda en imagen final) ───────────────────
FROM python:3.11-slim AS model-downloader

RUN pip install --no-cache-dir \
    torch==2.2.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir transformers==4.38.0 huggingface_hub sentencepiece

RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
AutoTokenizer.from_pretrained('lxyuan/distilbert-base-multilingual-cased-sentiments-student'); \
AutoModelForSequenceClassification.from_pretrained('lxyuan/distilbert-base-multilingual-cased-sentiments-student')"

# ── Stage 2: imagen final ─────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    torch==2.2.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=model-downloader /root/.cache/huggingface /root/.cache/huggingface

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]