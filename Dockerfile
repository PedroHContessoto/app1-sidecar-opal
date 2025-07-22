FROM python:3.9-slim

WORKDIR /app

# Adiciona os certificados da Netskope
COPY nscacert.crt /usr/local/share/ca-certificates/nscacert.crt
COPY nstenantcert.crt /usr/local/share/ca-certificates/nstenantcert.crt

# Instala certificados confiáveis e atualiza a CA store
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Instala dependências Python explicitando o bundle atualizado
COPY requirements.txt .
RUN pip install --no-cache-dir --cert /etc/ssl/certs/ca-certificates.crt -r requirements.txt

# Copia o restante do código
COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
