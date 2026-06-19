import os
from openai import OpenAI

# Will look for OPENAI_API_KEY in the environment
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

PATHS = {
    "scripts_dir": "assets/scripts",
    "manifests_dir": "outputs/manifests",
    "audio_dir": "outputs/audio",
    "voices_dir": "assets/voices"
}
