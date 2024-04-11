FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutar scripts de Python
# RUN python create_queue_producer.py

# Iniciar la aplicación
CMD ["python", "api.py"]
