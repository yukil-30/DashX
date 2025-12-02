FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for llama-cpp-python
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .

# Install Python dependencies
# CMAKE_ARGS configures llama-cpp-python for CPU-only build (faster, smaller)
ENV CMAKE_ARGS="-DLLAMA_BLAS=OFF -DLLAMA_CUBLAS=OFF -DLLAMA_METAL=OFF"
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create models directory (will be mounted as volume)
RUN mkdir -p /models

# Environment variables
ENV MODEL_PATH=/models/model.gguf
ENV N_CTX=2048
ENV N_THREADS=4
ENV N_GPU_LAYERS=0
ENV STUB_MODE=false

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
