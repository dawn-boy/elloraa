import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config import PATHS
from src.stages.stage0a_planner import generate_plan
from src.stages.stage0b_formatter import compile_plan_to_manifest
from src.manifest import BeatsManifest

def run_director_pass(script_path: str, output_manifest_name: str = "manifest.json", local: bool = False) -> BeatsManifest:
    print("=" * 60)
    print("STARTING STAGE 0: DIRECTOR PASS (SPLIT ARCHITECTURE)")
    print(f"Mode: {'LOCAL (vLLM FP8)' if local else 'CLOUD (OpenAI API)'}")
    print("=" * 60)
    
    # Step 1: Generate structured plan (Planner - R1-Distill-32B / GPT-4o)
    plan_name = "director_plan.md"
    print("\n>>> Phase 0A: Creative Planning...")
    plan_path = generate_plan(script_path, output_name=plan_name, local=local)
    
    # Step 2: Compile to JSON manifest (Formatter - Qwen3-32B / GPT-4o)
    print("\n>>> Phase 0B: Schema Compilation...")
    manifest_path = compile_plan_to_manifest(plan_path, output_name=output_manifest_name, local=local)
    
    if not manifest_path:
        print("\n[Director Pass] Error: Failed to generate/validate manifest.")
        return None
        
    print("\n" + "=" * 60)
    print("DIRECTOR PASS COMPLETED SUCCESSFULLY")
    print(f"Manifest written to: {manifest_path}")
    print("=" * 60)
    
    # Load and return the validated BeatsManifest object
    return BeatsManifest.load_from_file(manifest_path)

if __name__ == "__main__":
    script_p = os.path.join(PATHS["scripts_dir"], "script.md")
    use_local = "--local" in sys.argv
    run_director_pass(script_p, local=use_local)
