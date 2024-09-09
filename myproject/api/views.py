from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from playwright.sync_api import sync_playwright

from django.http import FileResponse
from django.views.decorators.csrf import csrf_protect
from .serializers import HelloWorldSerializer, ConsultarIpv6Serializer

import os
import json
import logging
import requests
import pandas as pd

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@swagger_auto_schema(method='post', request_body=HelloWorldSerializer)
@api_view(['POST'])
def hello_world(request):
    serializer = HelloWorldSerializer(data=request.data)
    
    if serializer.is_valid():
        nome = serializer.validated_data.get('nome')
        return Response({'message': f'O {nome} é muito gay!'})
    
    return Response(serializer.errors, status=400)


@csrf_protect
@swagger_auto_schema(method='post', request_body=ConsultarIpv6Serializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def consultar_ipv6(request):
    serializer = ConsultarIpv6Serializer(data=request.data)
    
    if serializer.is_valid():
        date = serializer.validated_data.get("date")
        time = serializer.validated_data.get("time")
        ipv6 = serializer.validated_data.get("ipv6")

        logger.info(f"Date: {date}")
        logger.info(f"Time: {time}")
        logger.info(f"IPv6: {ipv6}")

        retorno = run_playwright_script(date, time, ipv6)
        if "error" in retorno:
            return Response({"detail": retorno["error"]}, status=400)
        return Response(retorno)
    else:
        return Response(serializer.errors, status=400)


@csrf_protect
@swagger_auto_schema(method='get')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relatorio_ipv6(request):
    try:
        file_path = "resultado.xlsx"
        output_file_path = process_excel_file(file_path)
        
        if os.path.exists(output_file_path):  # Verificar se o arquivo foi gerado
            response = FileResponse(open(output_file_path, 'rb'), as_attachment=True, filename="resultado_processed.xlsx")
            return response
        else:
            raise APIException("Erro ao processar o arquivo ou nenhum dado foi encontrado.")
    
    except Exception:  # Captura qualquer exceção
        logger.error("Erro ao processar o arquivo")
        raise APIException("Erro ao processar arquivo")
          

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

            # Submeter o formulário
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(1000)

            # Esperar que o login seja concluído
            page.goto("https://tjsolutions.com.br/painel/dashboard")
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
                page.wait_for_load_state("networkidle", timeout=2000000)
            response = response_info.value
            logger.info(f"Response: {response.text()}")

            # Espera o botão " Excel" aparecer após a consulta
            with page.expect_download() as download3_info:
                page.get_by_role("button", name=" Excel").click()
            download = download3_info.value

            # Salvar o arquivo Excel na raiz da pasta do script
            current_directory = os.getcwd()
            saved_path = os.path.join(current_directory, "resultado.xlsx")
            download.save_as(saved_path)

            # ---------------------
            context.close()  # Fecha o contexto do navegador
            browser.close()  # Fecha o navegador

            logger.info("Arquivo Excel salvo com sucesso!")
            return {"message": "Consulta executada com sucesso!", "file": saved_path}
    
    except Exception as e:
        logger.error(f"Erro ao executar o script Playwright: {str(e)}")
        return {"Erro ao executar o script Playwright"}


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
        logger.info(response.json())
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
    
    # Adicionar as novas colunas antes de iniciar o processamento
    novas_colunas = ['Nome', 'CPF', 'Email', 'Telefone 1', 'Telefone 2', 'CEP', 'Número', 'Complemento', 'Logradouro', 'Bairro', 'Cidade', 'Estado']
    for coluna in novas_colunas:
        df_original[coluna] = ''

    logger.info(f"Colunas após adição das novas colunas: {df_original.columns.tolist()}")

    # Fazer a requisição POST para cada username e armazenar os resultados
    for index, row in df_original.iterrows():
        user = row['Usuário']
        data = fetch_data(user)
        
        if data:
            # Obter a lista de conexões
            mk_conexoes = data.get('data', {}).get('mk01', {}).get('mk_conexoes', [])
            logger.info(mk_conexoes)
            
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
                    
                    # Verificar se os dados estão sendo retornados corretamente
                    logger.info(f"Dados extraídos para {user}: {pessoa_info}")

                    # Adicione os dados ao DataFrame original
                    df_original.at[index, 'Nome'] = pessoa_info.get('nome_razaosocial', '')
                    df_original.at[index, 'CPF'] = pessoa_info.get('cpf', '')
                    df_original.at[index, 'Email'] = pessoa_info.get('email', '')
                    df_original.at[index, 'Telefone 1'] = pessoa_info.get('fone01', '')
                    df_original.at[index, 'Telefone 2'] = pessoa_info.get('fone02', '')
                    df_original.at[index, 'CEP'] = pessoa_info.get('cep', '')
                    df_original.at[index, 'Número'] = pessoa_info.get('numero', '')
                    df_original.at[index, 'Complemento'] = pessoa_info.get('complementoendereco', '')
                    df_original.at[index, 'Logradouro'] = logradouro_info.get('logradouro', '')
                    df_original.at[index, 'Bairro'] = bairro_info.get('bairro', '')
                    df_original.at[index, 'Cidade'] = cidade_info.get('cidade', '')
                    df_original.at[index, 'Estado'] = estado_info.get('siglaestado', '')
                    break  # Saia do loop após encontrar a correspondência
                else:
                    logger.warning(f"Username não encontrado na resposta da API para {user}")
        else:
            logger.warning(f"Nenhum dado retornado da API para {user}")

    # Verificar se a coluna foi adicionada
    logger.info(f"Colunas após processamento: {df_original.head()}")
    
    # Salvar o arquivo
    try:
        output_file_path = file_path.replace('.xlsx', '_processed.xlsx')
        df_original.to_excel(output_file_path, index=False)
        logger.info(f"Arquivo Excel processado salvo em: {output_file_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar o arquivo: {e}")
        raise
    
    return output_file_path