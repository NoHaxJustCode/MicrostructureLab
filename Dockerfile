FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY microstructurelab ./microstructurelab
COPY frontend ./frontend
COPY microstructurelab.py ./microstructurelab.py
EXPOSE 8000
CMD ["uvicorn", "microstructurelab.api:app", "--host", "0.0.0.0", "--port", "8000"]
