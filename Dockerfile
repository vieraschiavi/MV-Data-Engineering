# © 2026 Martín Viera. Todos los derechos reservados.
# MV Data Engineering · imagen para servidor (VM del cliente, Docker, Kubernetes).
# La gente entra por navegador: no se instala nada en la PC de nadie.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/mvde

WORKDIR /app

# Las dependencias primero: cambiar el código no reinstala todo de nuevo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Corre como usuario sin privilegios: si alguien consigue ejecución dentro del
# contenedor, no es root de la máquina.
RUN useradd --create-home --uid 10001 mvde \
    && mkdir -p /datos \
    && chown -R mvde:mvde /app /datos
USER mvde

EXPOSE 8501

# Streamlit publica su propio endpoint de salud: lo usa el orquestador para
# saber si el contenedor está vivo o hay que reiniciarlo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

CMD ["streamlit", "run", "app/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
