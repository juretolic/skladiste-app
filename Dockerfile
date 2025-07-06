FROM python:3.11-slim

WORKDIR /app

# Kopiranje requirements.txt
COPY requirements.txt .

# Instalacija dependencija
RUN pip install --no-cache-dir -r requirements.txt

# Kopiranje aplikacije
COPY app/ ./app/
COPY static/ ./static/

# Expose port
EXPOSE 8000

# Komanda za pokretanje
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 