# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from app import run_playwright_script

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = FastAPI(
    title="Automation API",
    description="API para automatizar a consulta em um sistema usando Playwright.",
    version="1.0.0"
)

class QueryParams(BaseModel):
    date: str = Field(..., example="2024-06-24", description="Data da consulta no formato YYYY-MM-DD")
    time: str = Field(..., example="13:34:17", description="Hora da consulta no formato HH:MM:SS")
    ipv6: str = Field(..., example="2804:145c:86f7:fc00::/56", description="Endereço IPv6 para a consulta")

@app.post("/consultar", summary="Consulta no sistema", response_description="Resultado da consulta")
def consultar(params: QueryParams):
    """
    Executa uma consulta no sistema utilizando Playwright e retorna o resultado.

    - **date**: Data da consulta (formato YYYY-MM-DD)
    - **time**: Hora da consulta (formato HH:MM:SS)
    - **ipv6**: Endereço IPv6 para consulta
    """
    retorno = run_playwright_script(params.date, params.time, params.ipv6)
    if "error" in retorno:
        raise HTTPException(status_code=400, detail=retorno["error"])
    return retorno

@app.get("/download", summary="Download do arquivo Excel")
def download_excel():
    excel_path = os.path.join(os.getcwd(), "resposta_relatorio.xlsx")
    if not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Arquivo Excel não encontrado.")
    return FileResponse(excel_path, filename="resposta_relatorio.xlsx")