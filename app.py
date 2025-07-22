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

