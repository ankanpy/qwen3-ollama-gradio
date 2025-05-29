# Gradio Ollama App 

This Gradio application allows interaction with multiple LLMs hosted by an Ollama instance running within the same Docker container. It uses the UI structure and logic as provided, with Ollama models streamed to a `gr.Textbox`.

## Features

- Select from various models pulled during the Docker build.
- Streaming output with a simulated typing effect to a `gr.Textbox`.
- Specific interaction modes (`/think`, `/no_think`) as per the original app.
- UI elements and branding as provided.

## Running Locally (with Docker)

1.  Ensure Docker Desktop is installed and running.
2.  Build the Docker image:
    ```bash
    docker build -t qwen3-ollama-gradio-app .
    ```
    To specify which models to pull during the build (space-separated):
    ```bash
    # Replace with models relevant to "qwen3" or other models you use
    docker build --build-arg OLLAMA_PULL_MODELS="qwen3:8b qwen3:4b-chat" -t qwen3-ollama-gradio-app .
    ```
    The default models are defined in the `Dockerfile`'s `ARG OLLAMA_PULL_MODELS`. Ensure `qwen3:8b` or other models used in examples are included if you want examples to work out-of-the-box.

3.  Run the Docker container:
    ```bash
    docker run -p 7860:7860 -it --rm qwen3-ollama-gradio-app
    ```
4.  Open your browser and navigate to `http://localhost:7860`.

## Customization

-   **Models:** Modify the `OLLAMA_PULL_MODELS` build argument or Space variable to include different Ollama models.
-   **Typing Speed:** Adjust `CHAR_DELAY` in `app.py`.
