import os
import subprocess
import time
import signal
import requests
from openai import OpenAI
from src.config import client as openai_client

def check_server_health(port: int = 8000) -> str:
    # Returns the model name if healthy, else empty string
    try:
        resp = requests.get(f"http://localhost:{port}/v1/models", timeout=1)
        if resp.status_code == 200:
            data = resp.json()
            if data and "data" in data and len(data["data"]) > 0:
                return data["data"][0]["id"]
        return ""
    except requests.RequestException:
        return ""

def kill_vllm_on_port(port: int = 8000):
    print(f"[vLLM] Force killing any server on port {port}...")
    try:
        subprocess.run(["pkill", "-f", "vllm.entrypoints"], check=False)
        time.sleep(2)
    except Exception as e:
        pass

def start_vllm_server(model_path: str, port: int = 8000) -> subprocess.Popen:
    print(f"\n[vLLM] Starting local server for model: {model_path} on port {port}...")
    
    # We load the model in FP8.
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--port", str(port),
        "--dtype", "half",
        "--max-model-len", "24576",  # Increased to handle high density plans
        "--gpu-memory-utilization", "0.9"
    ]
    
    # Run the server in a new process group so we can clean it up cleanly
    log_file = open("vllm_server.log", "w")
    process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid
    )
    
    # Monitor health
    timeout = 1800  # 30 minutes loading time limit (quantization takes a while)
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if process died early
        ret = process.poll()
        if ret is not None:
            raise RuntimeError(f"vLLM server exited early with code {ret}. Check vllm_server.log")
            
        if check_server_health(port):
            print("[vLLM] Server is healthy and responding to requests!")
            return process
            
        # Log a dot every 5 seconds to show we are waiting
        time.sleep(5)
        print("[vLLM] Waiting for model to load and compile...", flush=True)
        
    process.terminate()
    raise TimeoutError(f"vLLM server did not become healthy within {timeout} seconds.")

def run_completion_with_lifecycle(
    model_name: str, 
    messages: list, 
    temperature: float = 0.7, 
    local: bool = False, 
    response_format: dict = None,
    keep_alive: bool = False
) -> str:
    port = 8000
    server_process = None
    
    try:
        if local:
            abs_model_path = os.path.abspath(model_name)
            # 1. Check if server is already running
            running_model = check_server_health(port)
            if running_model == abs_model_path:
                print(f"[vLLM] Reusing already running server on port {port} for {abs_model_path}")
            else:
                if running_model:
                    print(f"[vLLM] Server is running but loaded with {running_model}. We need {abs_model_path}. Restarting...")
                    kill_vllm_on_port(port)

                if not os.path.exists(abs_model_path):
                    raise FileNotFoundError(f"Local model path not found: {abs_model_path}")
                
                # Start vLLM server
                server_process = start_vllm_server(abs_model_path, port=port)
            
            # Use local client
            llm_client = OpenAI(base_url=f"http://localhost:{port}/v1", api_key="local-key")
            actual_model = abs_model_path
        else:
            # Fallback to OpenAI API
            if not openai_client:
                raise ValueError("OpenAI client not configured (OPENAI_API_KEY environment variable missing)")
            llm_client = openai_client
            # Map paths to standard OpenAI models
            actual_model = "gpt-4o"
            
        print(f"Executing completion request using model: {actual_model}...")
        
        # Build API kwargs
        kwargs = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        response = llm_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content
        
    finally:
        if local and not keep_alive:
            print("[vLLM] Shutting down local server...")
            kill_vllm_on_port(port)
            print("[vLLM] Server shutdown complete.")
