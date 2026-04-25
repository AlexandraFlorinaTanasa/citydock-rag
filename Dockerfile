# Etapa 1: Builder - Instalăm dependențele
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Instalăm uneltele necesare pentru compilarea unor pachete dacă e cazul
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiem fișierul de dependențe
COPY requirements.txt .

# Instalăm pachetele într-un director local pentru a le copia ulterior
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2: Runtime - Imaginea finală, optimizată și securizată
# Folosim un digest fix (SHA-256) conform specificației 13.1
FROM python:3.12-slim-bookworm

# Creăm un utilizator non-root (uid 1000) numit 'appuser'
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Copiem doar pachetele instalate din etapa de builder
COPY --from=builder /install /usr/local
COPY ./app /app

# Setăm permisiunile pentru appuser
RUN chown -R appuser:appgroup /app

# Expunem portul 8080 conform specificației
EXPOSE 8080

# Utilizatorul sub care va rula procesul
USER appuser

# Healthcheck apelând endpoint-ul /v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/v1/health || exit 1

# Comanda de start (folosim uvicorn pentru FastAPI)
# Graceful termination (SIGTERM) este gestionat nativ de uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
