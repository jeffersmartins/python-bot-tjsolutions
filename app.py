# playwright_script.py
import os
import json
import pandas as pd
import requests
from playwright.sync_api import sync_playwright

def run_playwright_script(date: str, time: str, ipv6: str):
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


        def fetch_data(username):
            url = os.getenv("API_URL")
            
            # Consulta GraphQL com username dinâmico
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
                print(f"Dados recebidos para {username}")
                return response.json()  # Retornar o JSON recebido
            else:
                print(f"Falha na requisição para {username}. Status code: {response.status_code}")
                print("Erro:", response.text)
                return None

        # Carregar o arquivo Excel com os dados originais
        df_original = pd.read_excel("resultado.xlsx", header=1)

        # Extrair os usernames da coluna 'Usuário'
        usernames = df_original['Usuário'].tolist()

        # Fazer a requisição POST para cada username e armazenar os resultados
        results = []  # Inicializar como lista vazia

        for username in usernames:
            data = fetch_data(username)
            if data:  # Verificar se a resposta não é None
                results.append(data)

        # Converter a lista de respostas em um DataFrame do pandas
        if results:
            # Normalizar o JSON
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
                df_convert.to_excel("resposta_relatorio.xlsx", index=False)
                print("Dados salvos em resposta_relatorio.xlsx")
            else:
                print("Nenhum dado normalizado foi encontrado.")
            return ("Lista de resultados salva")
        else:
            print("Nenhum dado foi retornado.") 
            
            return {"message": "Consulta executada com sucesso!", "file": "resultado.xlsx"}