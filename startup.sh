#!/bin/bash
# startup.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "Starting Ollama server in the background..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$! # Get PID of the backgrounded ollama serve

echo "Waiting for Ollama to be ready (http://127.0.0.1:11434)..."
timeout_seconds=120
start_time=$(date +%s)
while ! curl -s --fail -o /dev/null http://127.0.0.1:11434; do
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ "$elapsed_time" -ge "$timeout_seconds" ]; then
        echo "Ollama failed to start within $timeout_seconds seconds. Check /tmp/ollama.log."
        cat /tmp/ollama.log
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
echo "Ollama server started successfully."

# OLLAMA_PULL_MODELS will be passed as an environment variable from Dockerfile
echo "Models to pull from ENV: ${OLLAMA_PULL_MODELS}"

for model_name in ${OLLAMA_PULL_MODELS}; do
    echo "Pulling model: ${model_name} (this may take several minutes)..."
    ollama pull "${model_name}"
    if [ $? -eq 0 ]; then
        echo "Model ${model_name} pulled successfully."
    else
        echo "Failed to pull model ${model_name}. Check logs or model name."
    fi
done

# Define a function to clean up (stop Ollama) when the script exits
cleanup() {
    echo "Caught signal, shutting down Ollama (PID: $OLLAMA_PID)..."
    if kill -0 $OLLAMA_PID > /dev/null 2>&1; then # Check if process exists
        kill $OLLAMA_PID
        wait $OLLAMA_PID # Wait for Ollama to actually terminate
        echo "Ollama shut down."
    else
        echo "Ollama process (PID: $OLLAMA_PID) not found or already stopped."
    fi
}

# Trap signals to call the cleanup function
# SIGINT is Ctrl+C, SIGTERM is `docker stop`
trap cleanup SIGINT SIGTERM

echo "Starting Gradio application (python app.py)..."
# Run python app.py in the foreground. It will now be PID 1 (or close to it)
# relative to this script, and signals will be handled by this script.
python app.py &
PYTHON_APP_PID=$!

wait $PYTHON_APP_PID # Wait for the python app to exit
# After python app exits, perform cleanup (this will also be called by trap)
cleanup
echo "Gradio application exited."