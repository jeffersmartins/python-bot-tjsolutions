# Use a imagem base recomendada pelo Playwright para Python
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copie os arquivos do projeto para o diretório de trabalho
COPY ./myproject /app/

# Instalar as dependências
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    playwright install --with-deps

# Expor a porta que o Django usará
EXPOSE 8000

# Comando padrão para rodar o servidor Django
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]