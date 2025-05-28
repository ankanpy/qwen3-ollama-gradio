# 1. Base Image
FROM python:3.11-slim

# Set the volume for Ollama data
# This is where Ollama will store its models and data
# VOLUME /root/.ollama

# 2. Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV OLLAMA_HOST="0.0.0.0:11434"

# 3. Set Working Directory
WORKDIR /app

# 4. Install System Dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# 6. Copy Application Requirements
COPY requirements.txt .

# 7. Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copy Your Application Code
COPY app.py .
COPY startup.sh .

# 9. Define Models to Pull (as an Argument with a default list)
ARG OLLAMA_PULL_MODELS="qwen3:4b qwen3:1.7b qwen3:0.6b" # Default models if not overridden

# Make the ARG available as an ENVironment variable for startup.sh
ENV OLLAMA_PULL_MODELS=${OLLAMA_PULL_MODELS} 

# 10. Expose Ports
EXPOSE 11434
EXPOSE 7860

# 11. Entrypoint/Startup Script - NOW USING EXEC FORM FOR THE SCRIPT
# CMD ["./startup.sh"] # <-- CHANGE TO THIS
ENTRYPOINT ["./startup.sh"]