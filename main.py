from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import logging
import pandas as pd
import requests
import json

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Automation API",
    description="API para automatizar a consulta em um sistema usando Playwright.",
    version="1.0.0"
)

class QueryParams(BaseModel):
    date: str = Field(..., example="2024-06-24", description="Data da consulta no formato YYYY-MM-DD")
    time: str = Field(..., example="13:34:17", description="Hora da consulta no formato HH:MM:SS")
    ipv6: str = Field(..., example="2804:145c:86f7:fc00::/56", description="Endereço IPv6 para a consulta")

def run_playwright_script(date: str, time: str, ipv6: str):
    """
    Executa o script do Playwright para realizar a automação de consulta.
    """
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(os.getenv("LOGIN_URL"))
            page.wait_for_timeout(3000)

            # Preencher o formulário de login
            page.get_by_placeholder("Seu usuário").fill(os.getenv("LOGIN_USER"))
            page.wait_for_timeout(500)
            page.get_by_placeholder("Sua senha").fill(os.getenv("LOGIN_PASSWORD"))
            page.wait_for_timeout(500)

            # Submeter o formulário (assumindo que é um botão de submit)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(1000)

            # Esperar que o login seja concluído verificando a presença de um elemento na página do painel
            page.wait_for_url("https://tjsolutions.com.br/painel/dashboard")
            page.wait_for_timeout(1000)

            # Navegar para a página desejada após o login
            page.get_by_role("link", name=" NC Syslog ").click()
            page.wait_for_timeout(1000)
            page.get_by_role("link", name="Consultar Autenticação").click() 
            page.wait_for_timeout(1000)
            page.get_by_label("Data: *").fill(date)
            page.wait_for_timeout(1000)
            page.get_by_label("Hora:*").click()
            page.wait_for_timeout(1000)
            page.get_by_label("Hora:*").fill(time)
            page.wait_for_timeout(1000)
            page.get_by_label("IPv6:").click()
            page.wait_for_timeout(1000)
            page.get_by_label("IPv6:").fill(ipv6)
            page.wait_for_timeout(1000)

            # Clica no botão "Localizar Registro" e espera a resposta
            with page.expect_response("https://tjsolutions.com.br/painel/ncsyslog_v6/consultar", timeout=200000) as response_info:
                page.get_by_role("button", name="Localizar Registro").click()
                page.wait_for_load_state("networkidle", timeout=10000)
            response = response_info.value
            print(response)
            page.wait_for_timeout(10000)

            # Espera o botão " Excel" aparecer após a consulta
            with page.expect_download() as download3_info:
                page.get_by_role("button", name=" Excel").click()
            download = download3_info.value
            page.wait_for_timeout(10000)

            # Salvar o arquivo Excel na raiz da pasta do script
            current_directory = os.getcwd()
            saved_path = os.path.join(current_directory, "resultado.xlsx")
            download.save_as(saved_path)

            # ---------------------
            context.close()
            browser.close()
            logger.info("Arquivo Excel salvo com sucesso!")
            return {"message": "Consulta executada com sucesso!", "file": saved_path}
    except Exception as e:
        logger.error(f"Erro ao executar o script Playwright: {str(e)}")
        return {"error": str(e)}

def fetch_data(username):
    """
    Faz uma requisição GraphQL para buscar dados de um usuário específico.
    """
    url = os.getenv("API_URL")
    query = f"""
    query MyQuery {{
        mk01 {{
            mk_conexoes(where: {{username: {{_eq: "{username}"}}}}) {{
                mk_pessoa {{
                    codpessoa
                    nome_razaosocial
                    cpf
                    email
                    fone01
                    fone02
                    cd_revenda
                    cep
                    numero
                }}
                mk_logradouros {{
                    logradouro
                    mk_bairros {{
                        bairro
                        mk_cidades {{
                            cidade
                            mk_estado {{
                                siglaestado
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("API_AUTH_TOKEN")}'  # Se precisar de autenticação
    }

    data = {'query': query}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        logger.info(f"Dados recebidos para {username}")
        return response.json()  # Retornar o JSON recebido
    else:
        logger.error(f"Falha na requisição para {username}. Status code: {response.status_code}")
        logger.error(f"Erro: {response.text}")
        return None

def process_excel_file(file_path):
    """
    Processa o arquivo Excel gerado pela automação, faz requisições para cada usuário e salva o resultado em outro arquivo Excel.

    :param file_path: Caminho para o arquivo Excel gerado
    """
    # Carregar o arquivo Excel com os dados originais
    logger.info(f"Carregando o arquivo Excel: {file_path}")
    df_original = pd.read_excel(file_path, header=1)

    # Extrair os usernames da coluna 'Usuário'
    usernames = df_original['Usuário'].tolist()

    # Fazer a requisição POST para cada username e armazenar os resultados
    results = []

    for username in usernames:
        data = fetch_data(username)
        if data:  # Verificar se a resposta não é None
            results.append(data)

    # Converter a lista de respostas em um DataFrame do pandas
    if results:
        data_normalized = []

        for result in results:
            # Acessar o caminho correto para os dados
            mk01 = result.get('data', {}).get('mk01', {})
            mk_conexoes = mk01.get('mk_conexoes', [])
            if mk_conexoes:
                for conexao in mk_conexoes:
                    mk_pessoa = conexao.get('mk_pessoa', {})
                    if mk_pessoa:
                        data_normalized.append(mk_pessoa)  # Adicionar dados normalizados

        # Verificar se data_normalized contém dados
        if data_normalized:
            # Converter a lista de dicionários em um DataFrame
            df_convert = pd.DataFrame(data_normalized)

            # Salvar o DataFrame em um arquivo Excel
            output_file = "resposta_relatorio.xlsx"
            df_convert.to_excel(output_file, index=False)
            logger.info(f"Dados salvos em {output_file}")
            return output_file
        else:
            logger.warning("Nenhum dado normalizado foi encontrado.")
    else:
        logger.warning("Nenhum dado foi retornado.")

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

@app.get("/processar", summary="Processa o arquivo Excel gerado e retorna o resultado processado", response_description="Arquivo de resposta gerado")
def processar():
    """
    Processa o arquivo Excel gerado pela consulta e retorna o arquivo processado.
    """
    try:
        # Defina o caminho para o arquivo Excel gerado pela automação com Playwright
        excel_file_path = "resultado.xlsx"
        
        # Processar o arquivo Excel e obter o caminho do arquivo de resposta gerado
        output_file_path = process_excel_file(excel_file_path)
        
        if output_file_path:
            # Retornar o arquivo de resposta gerado
            return FileResponse(path=output_file_path, filename="resposta_relatorio.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            raise HTTPException(status_code=404, detail="Erro ao processar o arquivo ou nenhum dado foi encontrado.")
    except Exception as e:
        logger.error(f"Erro ao processar o arquivo: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar o arquivo.")