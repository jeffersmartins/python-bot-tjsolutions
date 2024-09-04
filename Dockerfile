# Use a imagem base do Playwright
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Atualize a lista de pacotes e instale o pip
USER root
RUN apt-get update && apt-get install -y python3-pip

# Instale as dependências do sistema e o FastAPI
RUN pip install --upgrade pip \
    && pip install fastapi[all] pandas requests python-dotenv uvicorn openpyxl

# Instale o Playwright e os navegadores
RUN pip install playwright \
    && playwright install

# Crie um usuário não root e defina como o usuário atual
RUN useradd -ms /bin/bash playwrightuser

# Defina o diretório de trabalho
WORKDIR /home/playwrightuser/app

# Copie o arquivo .env e o script para o contêiner
COPY --chown=playwrightuser:playwrightuser main.py /home/playwrightuser/app/

# Defina as permissões adequadas para o diretório de trabalho
RUN chmod -R 755 /home/playwrightuser/app

# Defina a variável de ambiente para a porta que a aplicação irá rodar
ENV PORT=8000

# Exponha a porta que a aplicação irá rodar
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]