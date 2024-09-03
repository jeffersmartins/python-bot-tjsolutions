import os
import json
import logging
import requests
import pandas as pd

from playwright.sync_api import sync_playwright
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv


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
            browser = playwright.chromium.launch(headless=True)
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
            with page.expect_response("https://tjsolutions.com.br/painel/ncsyslog_v6/consultar", timeout=2000000) as response_info:
                page.get_by_role("button", name="Localizar Registro").click()
                page.wait_for_load_state("networkidle", timeout=10000)
            response = response_info.value
            print(response)
            page.wait_for_timeout(5000)

            # Espera o botão " Excel" aparecer após a consulta
            with page.expect_download() as download3_info:
                page.get_by_role("button", name=" Excel").click()
            download = download3_info.value
            page.wait_for_timeout(5000)

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
                username
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
                    complementoendereco
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
        return response.json()
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
    
    # Verifique as colunas carregadas
    logger.info(f"Colunas do DataFrame original: {df_original.columns.tolist()}")

    # Fazer a requisição POST para cada username e armazenar os resultados
    for index, row in df_original.iterrows():
        user = row['Usuário']
        data = fetch_data(user)
        
        if data:
            # Obter a lista de conexões
            mk_conexoes = data.get('data', {}).get('mk01', {}).get('mk_conexoes', [])
            
            # Encontrar a conexão correspondente ao usuário atual
            for connection_info in mk_conexoes:
                username = connection_info.get('username')
                
                if username == user:
                    # Extraia as informações relevantes dos dados retornados
                    pessoa_info = connection_info.get('mk_pessoa', {})
                    logradouro_info = connection_info.get('mk_logradouros', {})
                    bairro_info = logradouro_info.get('mk_bairros', {})
                    cidade_info = bairro_info.get('mk_cidades', {})
                    estado_info = cidade_info.get('mk_estado', {})

                    # Adicione os dados ao DataFrame original
                    df_original.at[index, 'Nome'] = pessoa_info.get('nome_razaosocial')
                    df_original.at[index, 'CPF'] = pessoa_info.get('cpf')
                    df_original.at[index, 'Email'] = pessoa_info.get('email')
                    df_original.at[index, 'Telefone 1'] = pessoa_info.get('fone01')
                    df_original.at[index, 'Telefone 2'] = pessoa_info.get('fone02')
                    df_original.at[index, 'CEP'] = pessoa_info.get('cep')
                    df_original.at[index, 'Número'] = pessoa_info.get('numero')
                    df_original.at[index, 'Complemento'] = pessoa_info.get('complementoendereco')
                    df_original.at[index, 'Logradouro'] = logradouro_info.get('logradouro')
                    df_original.at[index, 'Bairro'] = bairro_info.get('bairro')
                    df_original.at[index, 'Cidade'] = cidade_info.get('cidade')
                    df_original.at[index, 'Estado'] = estado_info.get('siglaestado')
                    break  # Saia do loop após encontrar a correspondência

    # Salvar o DataFrame atualizado em um novo arquivo Excel
    output_file_path = file_path.replace('.xlsx', '_processed.xlsx')
    df_original.to_excel(output_file_path, index=False)
    logger.info(f"Arquivo Excel processado salvo em: {output_file_path}")
    
    return output_file_path


@app.post("/consultar-ipv6", summary="Consulta no sistema", response_description="Resultado da consulta")
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


@app.get("/processar-ipv6", summary="Processa o arquivo Excel gerado e retorna o resultado processado", response_description="Arquivo de resposta gerado")
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
            return FileResponse(path=output_file_path, filename="resultado_processed.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            raise HTTPException(status_code=404, detail="Erro ao processar o arquivo ou nenhum dado foi encontrado.")
    except Exception as e:
        logger.error(f"Erro ao processar o arquivo: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar o arquivo.")