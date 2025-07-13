# app1/app.py - CORRIGIDO para External Data Sources


from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import os
import jwt
from jwt import InvalidTokenError
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


app = FastAPI()

def ssh_rsa_to_pem(ssh_public_key: str) -> str:
    """
    Converte uma chave pública SSH RSA para formato PEM que o PyJWT aceita.
    Entrada: "ssh-rsa AAAAB3NzaC1yc2E... user@host"
    Saída: "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
    """
    try:
        # Remover prefixo "ssh-rsa " e sufixo " user@host"
        key_parts = ssh_public_key.strip().split()
        if len(key_parts) < 2 or key_parts[0] != 'ssh-rsa':
            raise ValueError("Formato de chave SSH RSA inválido")
        
        # Decodificar a parte base64
        key_data = base64.b64decode(key_parts[1])
        
        # Parse do formato SSH
        offset = 0
        
        # Ler tipo de chave
        type_len = int.from_bytes(key_data[offset:offset+4], 'big')
        offset += 4
        key_type = key_data[offset:offset+type_len].decode('ascii')
        offset += type_len
        
        if key_type != 'ssh-rsa':
            raise ValueError("Tipo de chave não é ssh-rsa")
        
        # Ler expoente público (e)
        e_len = int.from_bytes(key_data[offset:offset+4], 'big')
        offset += 4
        e = int.from_bytes(key_data[offset:offset+e_len], 'big')
        offset += e_len
        
        # Ler módulo público (n)
        n_len = int.from_bytes(key_data[offset:offset+4], 'big')
        offset += 4
        n = int.from_bytes(key_data[offset:offset+n_len], 'big')
        
        # Criar chave pública RSA
        public_key = rsa.RSAPublicNumbers(e, n).public_key()
        
        # Serializar para PEM
        pem_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return pem_bytes.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Erro ao converter chave SSH para PEM: {str(e)}")

@app.get("/")
async def read_root():
    """
    Endpoint de healthcheck
    """
    return {"status": "app1 is healthy"}


@app.get("/opal/data-sources")
async def get_data_sources_app1(token: Optional[str] = Query(None)):
    """
    External Data Source endpoint para OPAL Server.

    OPAL Server fará redirect para esta URL com ?token=<JWT>
    Este endpoint retorna a configuração dinâmica do cliente OPAL.
    """

    # 🔐 1. Validação do token JWT
    if not token:
        raise HTTPException(status_code=401, detail="Token JWT ausente")

    ssh_public_key = os.getenv("OPAL_PUBLIC_KEY")
    if not ssh_public_key:
        raise HTTPException(status_code=500, detail="Chave pública do OPAL (OPAL_PUBLIC_KEY) não configurada")

    try:
        # Converter chave SSH para formato PEM
        pem_public_key = ssh_rsa_to_pem(ssh_public_key)
        claims = jwt.decode(token, pem_public_key, algorithms=["RS256"])
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token JWT inválido: {str(e)}")

    # 🔍 2. (Opcional, mas recomendado) Usar claims do token
    client_id = claims.get("permit_client_id", "default")

    print(f"➡️ client_id = {client_id}")

    # 🔧 3. Carregar config do banco via env
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    if not all([user, password, host, db_name]):
        raise HTTPException(status_code=500, detail="Variáveis de ambiente do banco estão incompletas")

    # 🔗 4. Construir string de conexão
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    # 📦 5. Retornar config conforme schema da OPAL
    return {
        "entries": [
            {
                "url": db_url,
                "topics": ["policy_data/app1"],
                "dst_path": "employees",
                "config": {
                    "fetcher": "PostgresFetchProvider",
                    "query": "SELECT id, name, department FROM employees"
                }
            }
        ]
    }