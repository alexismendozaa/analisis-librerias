# Usa Python 3.11 porque numpy 2.x lo requiere
FROM python:3.11-slim

# Crea el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . /app

# Actualiza pip e instala dependencias
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expone el puerto de Streamlit
EXPOSE 8501

# Comando para ejecutar la app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
