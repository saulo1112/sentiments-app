from flask import Flask, request, render_template_string
from transformers import pipeline
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import torch
import os

app = Flask(__name__)

# Modelo distilado: ~250 MB vs ~700 MB del BERT base
# Misma precisión para sentimientos, 3x más liviano
MODEL_NAME = "lxyuan/distilbert-base-multilingual-cased-sentiments-student"

print("Cargando modelo de IA en español...")
analizador = pipeline(
    "sentiment-analysis",
    model=MODEL_NAME,
    device=-1,
)
torch.quantization.quantize_dynamic(
    analizador.model,
    {torch.nn.Linear},
    dtype=torch.qint8,
    inplace=True,
)
print("Modelo listo!")

# ── Pool de conexiones ────────────────────────────────────────────────────────
db_pool: ThreadedConnectionPool | None = None

def get_pool() -> ThreadedConnectionPool:
    global db_pool
    if db_pool is None:
        db_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.environ.get("DB_HOST", "db"),
            database=os.environ.get("DB_NAME", "sentimentdb"),
            user=os.environ.get("DB_USER", "admin"),
            password=os.environ.get("DB_PASSWORD", "password123"),
            port=os.environ.get("DB_PORT", "5432"),
        )
    return db_pool

def get_conn():
    return get_pool().getconn()

def release_conn(conn):
    get_pool().putconn(conn)

def init_db():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id         SERIAL PRIMARY KEY,
                text       TEXT,
                sentiment  VARCHAR(20),
                estrellas  INTEGER,
                confianza  FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        print("Base de datos lista!")
    except Exception as e:
        print(f"Error conectando a BD: {e}")
    finally:
        if conn:
            release_conn(conn)

HTML = '''<!DOCTYPE html>
<html><head><title>Analizador de Sentimientos</title>
<style>
  body { font-family: Arial; max-width: 700px; margin: 40px auto; padding: 20px; background: #f5f5f5; }
  .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  textarea { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #ddd; font-size: 15px; box-sizing: border-box; }
  button { margin-top: 10px; padding: 10px 24px; background: #185FA5; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }
  .positive { color: #3B6D11; background: #EAF3DE; padding: 4px 12px; border-radius: 99px; }
  .negative { color: #A32D2D; background: #FCEBEB; padding: 4px 12px; border-radius: 99px; }
  .neutral  { color: #5F5E5A; background: #F1EFE8; padding: 4px 12px; border-radius: 99px; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; }
  .estrellas { color: #f5a623; font-size: 16px; }
  .badge-host { font-size: 11px; background: #E6F1FB; color: #185FA5; padding: 2px 8px; border-radius: 99px; }
</style></head>
<body>
  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h2 style="margin:0">Analizador de Sentimientos</h2>
      <span class="badge-host">Servidor: {{ hostname }}</span>
    </div>
    <p style="color:#888; font-size:13px; margin-top:6px;">Funciona en español, inglés y más idiomas</p>
    <form method="POST" action="/analyze">
      <textarea name="text" rows="4" placeholder="Escribe tu texto aqui..."></textarea>
      <button type="submit">Analizar</button>
    </form>
    {% if result %}
    <div style="margin-top:16px; padding:12px; background:#f9f9f9; border-radius:8px;">
      <strong>Resultado:</strong>
      <span class="{{ result.sentiment }}">{{ result.sentiment }}</span>
      &nbsp;
      <span class="estrellas">{{ result.estrellas }}</span>
      &nbsp; Confianza: <strong>{{ result.confianza }}%</strong>
    </div>
    {% endif %}
  </div>
  <div class="card">
    <h3 style="margin-top:0">Historial (PostgreSQL)</h3>
    <table>
      <tr style="background:#f5f5f5;">
        <td><strong>Texto</strong></td>
        <td><strong>Sentimiento</strong></td>
        <td><strong>Estrellas</strong></td>
        <td><strong>Confianza</strong></td>
        <td><strong>Fecha</strong></td>
      </tr>
      {% for r in historial %}
      <tr>
        <td>{{ r[1][:50] }}</td>
        <td><span class="{{ r[2] }}">{{ r[2] }}</span></td>
        <td class="estrellas">{{ "★" * r[3] }}{{ "☆" * (5 - r[3]) }}</td>
        <td style="color:#888">{{ r[4] }}%</td>
        <td style="color:#888; font-size:12px;">{{ r[5].strftime("%d/%m %H:%M") }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
</body></html>'''

def fetch_historial(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM analyses ORDER BY created_at DESC LIMIT 10")
    return cur.fetchall()

@app.route("/")
def index():
    historial = []
    conn = None
    try:
        conn = get_conn()
        historial = fetch_historial(conn)
    except Exception as e:
        print(f"Error leyendo historial: {e}")
    finally:
        if conn:
            release_conn(conn)
    return render_template_string(
        HTML, result=None, historial=historial,
        hostname=os.environ.get("HOSTNAME", "local"),
    )

@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.form.get("text", "")
    resultado = analizador(text, truncation=True, max_length=128)[0]

    # Este modelo devuelve "positive"/"negative"/"neutral" directamente
    label = resultado["label"].lower()
    confianza = round(resultado["score"] * 100, 1)

    if label == "positive":
        sentiment = "positive"
        estrellas_num = 5
    elif label == "negative":
        sentiment = "negative"
        estrellas_num = 1
    else:
        sentiment = "neutral"
        estrellas_num = 3

    estrellas = "★" * estrellas_num + "☆" * (5 - estrellas_num)

    historial = []
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO analyses (text, sentiment, estrellas, confianza) VALUES (%s, %s, %s, %s)",
            (text, sentiment, estrellas_num, confianza),
        )
        conn.commit()
        historial = fetch_historial(conn)
    except Exception as e:
        print(f"Error guardando en BD: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_conn(conn)

    return render_template_string(
        HTML,
        result={"sentiment": sentiment, "estrellas": estrellas, "confianza": confianza},
        historial=historial,
        hostname=os.environ.get("HOSTNAME", "local"),
    )

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", debug=True, port=5000)