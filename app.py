# app1/app.py

from fastapi import FastAPI
import os # Importe o módulo 'os' para ler variáveis de ambiente

app = FastAPI( )

@app.get("/opal/data-sources")
async def get_data_sources_app1():
    print("APP1: Endpoint /opal/data-sources foi chamado.")
    
    # MODIFICADO: Leia as credenciais das variáveis de ambiente
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    # Construa a URL dinamicamente
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    return {
        "entries": [{
            "url": db_url,
            "config": {
                "fetcher": "PostgresFetchProvider",
                "query": "SELECT id, name, department FROM employees"
            },
            "topics": ["policy_data"],
            "dst_path": "employees"
        }]
    }
