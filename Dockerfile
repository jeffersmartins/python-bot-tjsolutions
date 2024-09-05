# Use a imagem base do Playwright
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Atualize a lista de pacotes e instale o pip
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instale o Django e outras dependências
RUN pip install --upgrade pip \
    && pip install django djangorestframework psycopg2-binary pandas openpyxl python-dotenv

# Crie um usuário não root e defina como o usuário atual
RUN useradd -ms /bin/bash djangouser

# Defina o diretório de trabalho
WORKDIR /home/djangouser/app

# Copie o arquivo requirements.txt e o projeto para o contêiner
COPY --chown=djangouser:djangouser requirements.txt /home/djangouser/app/
COPY --chown=djangouser:djangouser . /home/djangouser/app/

# Instale as dependências do projeto
RUN pip install -r requirements.txt

# Defina as permissões adequadas para o diretório de trabalho
RUN chmod -R 755 /home/djangouser/app

# Defina a variável de ambiente para a porta que a aplicação irá rodar
ENV PORT=8000

# Exponha a porta que a aplicação irá rodar
EXPOSE 8000

# Comando para rodar as migrações e iniciar o servidor Django
CMD ["sh", "-c", "python python_bot_tjsolutions/manage.py migrate && python python_bot_tjsolutions/manage.py runserver 0.0.0.0:8000"]
