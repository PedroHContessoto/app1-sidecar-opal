# app1/app.py - CORRIGIDO para External Data Sources


from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import os
import jwt
from jwt import InvalidTokenError


app = FastAPI()

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

    public_key = os.getenv("OPAL_PUBLIC_KEY")
    if not public_key:
        raise HTTPException(status_code=500, detail="Chave pública do OPAL (OPAL_PUBLIC_KEY) não configurada")

    # Converter chave SSH RSA para formato PEM para PyJWT
    if public_key.startswith("ssh-rsa"):
        try:
            import base64
            import struct
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            
            # Remove o prefixo "ssh-rsa " e decodifica base64
            key_data = public_key.split()[1]
            key_bytes = base64.b64decode(key_data)
            
            # Parse do formato SSH
            offset = 0
            
            # Lê o tipo de chave
            key_type_len = struct.unpack('>I', key_bytes[offset:offset+4])[0]
            offset += 4
            key_type = key_bytes[offset:offset+key_type_len]
            offset += key_type_len
            
            # Lê o expoente público (e)
            e_len = struct.unpack('>I', key_bytes[offset:offset+4])[0]
            offset += 4
            e = int.from_bytes(key_bytes[offset:offset+e_len], 'big')
            offset += e_len
            
            # Lê o módulo (n)
            n_len = struct.unpack('>I', key_bytes[offset:offset+4])[0]
            offset += 4
            n = int.from_bytes(key_bytes[offset:offset+n_len], 'big')
            
            # Cria a chave RSA
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key_obj = public_numbers.public_key()
            
            # Serializa para PEM
            pem_key = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            public_key = pem_key.decode('utf-8')
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao converter chave SSH RSA: {str(e)}")

    try:
        claims = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token JWT inválido: {str(e)}")

    # 🔍 2. (Opcional, mas recomendado) Usar claims do token
    client_id = claims.get("scope_id", "default")

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
        "config": {
            "entries": [
                {
                    "url": db_url,
                    "topics": [f"policy_data/{client_id}"],
                    "dst_path": "employees",
                    "config": {
                        "fetcher": "PostgresFetchProvider",
                        "query": "SELECT id, name, department FROM employees"
                    }
                }
            ]
        }
    }