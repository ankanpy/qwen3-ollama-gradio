import gradio as gr
import subprocess
import time

# import os # Not strictly needed in *this* version of app.py as no env vars are read

# --- Ollama Helper Functions ---


def check_ollama_running():
    """Checks if the Ollama service is accessible."""
    try:
        subprocess.run(["ollama", "ps"], check=True, capture_output=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_ollama_models():
    """Gets a list of locally available Ollama models."""
    # Removed the 'if not check_ollama_running(): return []'
    # because it's called after AVAILABLE_MODELS is determined,
    # and check_ollama_running is implicitly done by the initial AVAILABLE_MODELS load.
    # However, in a container, Ollama should be running.
    try:
        result = subprocess.run(["ollama", "list"], check=True, capture_output=True, text=True, timeout=10)
        models = []
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    models.append(parts[0])
        # Ensure models are sorted and unique for consistent dropdown
        return sorted(list(set(models)))
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Error in get_ollama_models: {e}")  # Added a print for debugging
        return []


# --- Core Logic ---

# Typing speed simulation
CHAR_DELAY = 0.02  # Adjust for desired speed (0.01 is fast, 0.05 is slower)


def reasoning_ollama_stream(model_name, prompt, mode):  # Renamed prompt_text back to prompt
    """
    Streams response from an Ollama model with simulated typing speed.
    """
    if not model_name:
        yield "Error: No model selected. Please choose a model."
        return
    if not prompt.strip():  # Using original 'prompt' variable name
        yield "Error: Prompt cannot be empty."
        return

    # This check is good for robustness, even in Docker.
    if not check_ollama_running():
        yield "Error: Ollama service does not seem to be running or accessible. Please start Ollama."
        return

    # This is a runtime check. The Dockerfile aims to pull models, but this confirms.
    available_models_runtime = get_ollama_models()
    if model_name not in available_models_runtime:
        yield f"Error: Model '{model_name}' selected, but not found by Ollama at runtime. Available: {available_models_runtime}. Please ensure it was pulled."
        return

    # Using original 'prompt' and 'mode'
    prompt_with_mode = f"{prompt.strip()} /{mode}"
    command = ["ollama", "run", model_name]

    displayed_response = ""
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        process.stdin.write(prompt_with_mode + "\n")
        process.stdin.close()

        for line_chunk in iter(process.stdout.readline, ""):
            if not line_chunk and process.poll() is not None:  # Check if process ended
                break
            for char in line_chunk:
                displayed_response += char
                yield displayed_response
                if char.strip():  # Only sleep for non-whitespace characters
                    time.sleep(CHAR_DELAY)

        process.stdout.close()
        return_code = process.wait(timeout=10)  # Added timeout to wait

        if return_code != 0:
            error_output = process.stderr.read()
            error_message = f"\n\n--- Ollama Error (code {return_code}) ---\n{error_output.strip()}"
            if displayed_response and not displayed_response.endswith(error_message):
                displayed_response += error_message
            elif not displayed_response:
                displayed_response = error_message.strip()
            yield displayed_response
            return

        if not displayed_response.strip() and return_code == 0:
            yield "Model returned an empty response."
        elif displayed_response:
            yield displayed_response

    except FileNotFoundError:
        yield "Error: 'ollama' command not found. Please ensure Ollama is installed and in your PATH (or Dockerfile is correct)."
    except subprocess.TimeoutExpired:  # Catch timeout from process.wait()
        yield "Error: Ollama process timed out while waiting for completion."
        if displayed_response:
            yield displayed_response
    except Exception as e:
        yield f"An unexpected error occurred: {str(e)}"
        if displayed_response:
            yield displayed_response


# --- Gradio UI ---

# This runs once when the script starts.
# In Docker, this will query the Ollama instance inside the container AFTER models are pulled by CMD.
AVAILABLE_MODELS = get_ollama_models()
QWEN_MODELS = [m for m in AVAILABLE_MODELS if "qwen" in m.lower()]
INITIAL_MODEL = None

# Prioritize qwen3:4b if available - This logic is from your original app.py
if "qwen3:4b" in AVAILABLE_MODELS:
    INITIAL_MODEL = "qwen3:4b"
elif QWEN_MODELS:
    INITIAL_MODEL = QWEN_MODELS[0]
elif AVAILABLE_MODELS:
    INITIAL_MODEL = AVAILABLE_MODELS[0]
# If no models, INITIAL_MODEL remains None, and dropdown will show "No models found..."

with gr.Blocks(title="Qwen3 x Ollama", theme=gr.themes.Soft()) as demo:
    gr.HTML(
        """
        <h1 style='text-align: center'>
        Qwen3 Reasoning with Ollama
        </h1>
    """
    )
    gr.HTML(
        """
        <h3 style='text-align: center'>
        <a href='https://opencv.org/university/' target='_blank'>OpenCV Courses</a> | <a href='https://github.com/OpenCV-University' target='_blank'>Github</a>
        </h3>
        """
    )
    gr.Markdown(
        """
        - Interact with a Qwen3 model hosted on Ollama.
        - Switch between `/think` and `/no_think` modes to explore the thinking process.
        - The response will stream with a simulated typing effect.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            model_selector = gr.Dropdown(
                label="Select Model",
                choices=AVAILABLE_MODELS if AVAILABLE_MODELS else ["No models found - check Ollama setup"],
                value=INITIAL_MODEL,
                interactive=True,
            )
            prompt_input = gr.Textbox(
                label="Enter your prompt",
                placeholder="e.g., Explain quantum entanglement in simple terms.",
                lines=5,
                elem_id="prompt-input",
            )
            mode_radio = gr.Radio(
                ["think", "no_think"],  # Kept original modes from your app.py
                label="Reasoning Mode",
                value="think",
                info="`/think` encourages step-by-step reasoning. `/no_think` aims for a direct answer.",
            )
            with gr.Row():
                submit_button = gr.Button("Generate Response", variant="primary")
                clear_button = gr.ClearButton()

        with gr.Column(scale=2):
            status_output = gr.Textbox(
                label="Status",
                interactive=False,
                lines=1,
                placeholder="Awaiting submission...",
                elem_id="status-output",
            )
            response_output = gr.Textbox(  # Kept as gr.Textbox as requested
                label="Model Response", lines=20, interactive=False, show_copy_button=True, elem_id="response-output"
            )

    def handle_submit_wrapper(model, prompt, mode):
        yield {status_output: "Processing... Preparing to stream response.", response_output: ""}

        final_chunk = ""
        # Using original variable names 'prompt' and 'mode' for reasoning_ollama_stream
        for chunk in reasoning_ollama_stream(model, prompt, mode):
            final_chunk = chunk
            yield {status_output: "Streaming response...", response_output: chunk}

        if "Error:" in final_chunk or "--- Ollama Error ---" in final_chunk:
            yield {status_output: "Completed with issues.", response_output: final_chunk}
        elif "Model returned an empty response." in final_chunk:
            yield {status_output: "Model returned an empty response.", response_output: final_chunk}
        elif not final_chunk.strip() and ("Error:" not in final_chunk and "--- Ollama Error ---" not in final_chunk):
            yield {status_output: "Completed, but no substantive output received.", response_output: ""}
        else:
            yield {status_output: "Response generated successfully!", response_output: final_chunk}

    submit_button.click(
        fn=handle_submit_wrapper,
        inputs=[model_selector, prompt_input, mode_radio],
        outputs=[status_output, response_output],
    )
    clear_button.add([prompt_input, response_output, status_output])

    # Example model determination logic from your original app.py
    # Note: This might select a model not actually available if AVAILABLE_MODELS is empty
    # and the fallback "qwen3:4b" is used.
    # A safer approach is to ensure example_model is from AVAILABLE_MODELS if possible.
    example_model_for_ui = INITIAL_MODEL
    if not example_model_for_ui and AVAILABLE_MODELS:
        example_model_for_ui = AVAILABLE_MODELS[0]
    elif not example_model_for_ui:  # Fallback if no models and INITIAL_MODEL is None
        example_model_for_ui = "qwen3:4b"  # Default example model

    gr.Examples(
        examples=[
            [example_model_for_ui, "What are the main pros and cons of using nuclear energy?", "think"],
            # Fallback for the second example if qwen3:4b isn't a primary choice
            [
                (
                    example_model_for_ui
                    if example_model_for_ui != "qwen3:4b"
                    else (INITIAL_MODEL if INITIAL_MODEL and INITIAL_MODEL != "qwen3:4b" else "qwen3:1.7b")
                ),
                "Write a short poem about a rainy day.",
                "no_think",
            ],
            [example_model_for_ui, "Plan a 3-day trip to Paris, focusing on historical sites.", "think"],
        ],
        inputs=[model_selector, prompt_input, mode_radio],
        outputs=[status_output, response_output],
        fn=handle_submit_wrapper,
        cache_examples=False,  # Cache examples can be True if inputs are static and fn is pure
    )
    gr.HTML(
        """
        <h3 style='text-align: center'>
        Developed with ❤️ by OpenCV
        </h3>
        """
    )

if __name__ == "__main__":
    print("--- Gradio App Starting ---")  # Simplified print
    print(f"Attempting to fetch Ollama models (initial load)... Result: {AVAILABLE_MODELS}")
    print(f"Initial model for UI (if any): {INITIAL_MODEL}")
    print(f"Gradio version: {gr.__version__}")
    print(f"---------------------------")

    # For local Docker testing, server_name="0.0.0.0" is important.
    # For Hugging Face Spaces, demo.launch() is usually enough as it handles proxying.
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Set to True if you need a public link for local testing (requires internet)
        # share=os.getenv("GRADIO_SHARE", "False").lower() == "true" # If using env var for share
    )
