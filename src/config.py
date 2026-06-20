import os
from openai import OpenAI

# Will look for OPENAI_API_KEY in the environment
_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=_api_key) if _api_key else None

PATHS = {
    "scripts_dir": "assets/scripts",
    "manifests_dir": "outputs/manifests",
    "audio_dir": "outputs/audio",
    "voices_dir": "assets/voices"
}
