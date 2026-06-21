import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.llm_client import run_completion_with_lifecycle

def main():
    print("="*60)
    print(">>> AI DOCUMENTARY PROMPT LAB <<<")
    print("="*60)
    
    config_path = os.path.join(os.path.dirname(__file__), "lab_config.json")
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return
        
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        return
        
    passes = config.get("passes", [])
    
    if not passes:
        print("No passes defined in config.")
        return
        
    print(f"Loaded configuration with {len(passes)} passes.")
    
    model_name = "repos/DeepSeek-R1-Distill-Qwen-32B-FP8"
    pass_outputs = []
    
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    for idx, pass_cfg in enumerate(passes):
        p_num = pass_cfg.get("pass_number", idx + 1)
        
        # Resolve paths relative to project root
        sys_prompt_path = pass_cfg.get("system_prompt", "")
        if sys_prompt_path: sys_prompt_path = os.path.join(PROJECT_ROOT, sys_prompt_path)
            
        user_prompt_path = pass_cfg.get("user_prompt", "")
        if user_prompt_path and user_prompt_path.upper() != "PREV":
            user_prompt_path = os.path.join(PROJECT_ROOT, user_prompt_path)
            
        output_file_path = pass_cfg.get("output_file", f"src/testing/outputs/pass{p_num}.md")
        if output_file_path: output_file_path = os.path.join(PROJECT_ROOT, output_file_path)
        
        print(f"\n--- Pass {p_num} Setup ---")
        
        # Read sys prompt
        try:
            with open(sys_prompt_path, 'r') as f:
                sys_prompt = f.read()
        except Exception as e:
            print(f"Error reading {sys_prompt_path}: {e}")
            break
            
        # Read user prompt
        if user_prompt_path.upper() == 'PREV' and len(pass_outputs) > 0:
            user_prompt = pass_outputs[-1]
            print(f"Chaining output from Pass {p_num-1} ({len(user_prompt)} chars) into Pass {p_num}!")
        else:
            try:
                with open(user_prompt_path, 'r') as f:
                    user_prompt = f.read()
            except Exception as e:
                print(f"Error reading {user_prompt_path}: {e}")
                break
                
        print(f"Running Pass {p_num} on DeepSeek-R1...")
        
        # Force keep_alive=True for all passes
        try:
            output = run_completion_with_lifecycle(
                model_name=model_name,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,
                local=True,
                keep_alive=True 
            )
        except Exception as e:
            print(f"An error occurred during generation: {e}")
            break
        
        pass_outputs.append(output)
        
        # Ensure the directory for the output file exists
        out_dir = os.path.dirname(os.path.abspath(output_file_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        
        with open(output_file_path, "w") as f:
            f.write(output)
            
        print(f"Pass {p_num} complete! Output instantly saved to: {output_file_path}")
        
    print("\nExperiment complete! vLLM server is still running in the background.")
    print("You can update lab_config.json and run this script again instantly!")

if __name__ == "__main__":
    main()
