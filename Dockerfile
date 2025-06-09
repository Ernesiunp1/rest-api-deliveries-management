FROM python:3.10-slim
LABEL authors="ernesto"

# Establece el directorio de trabajo
WORKDIR /app

# Copia e instala las dependencias
COPY ./requirements.txt /app/requirements.txt
#RUN apt-get update && apt-get install -y \
#    micro \
#    && pip install --no-cache-dir -r /app/requirements.txt



RUN apt-get update && apt-get install -y \
    build-essential \
    micro \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app


# Copia el resto de los archivos de la aplicación
COPY . /app

# Expone el puerto para FastAPI
EXPOSE 8000

# Usa un script de shell para iniciar el servicio FastAPI
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# asi levato el container
# sudo docker run -p 8007:80 --network tributo_kafka_anfler-network --name ts.dashboard  ts-dashboard