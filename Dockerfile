# Imagen base oficial de Python
FROM python:3.11-slim

# Evitar preguntas durante instalación
ENV DEBIAN_FRONTEND=noninteractive

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos del proyecto
COPY . .

# Instalar librerías de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Exponer puerto si querés usar una API web (opcional)
# EXPOSE 8000

# Comando de ejecución principal (reemplazalo si querés otro)
CMD ["python", "main.py"]
