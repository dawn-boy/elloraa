import os
import sys

def patch_indextts():
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../repos/index-tts"))
    if not os.path.exists(repo_dir):
        print(f"Error: index-tts not found at {repo_dir}. Please clone it first.")
        sys.exit(1)

    # 1. Patch transformers_generation_utils.py
    gen_utils_path = os.path.join(repo_dir, "indextts/gpt/transformers_generation_utils.py")
    if os.path.exists(gen_utils_path):
        with open(gen_utils_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Patch QuantizedCacheConfig & OffloadedCache
        if "from transformers.cache_utils import (" in content and "QuantizedCacheConfig" in content:
            content = content.replace(
"""from transformers.cache_utils import (
    Cache,
    DynamicCache,
    EncoderDecoderCache,
    OffloadedCache,
    QuantizedCacheConfig,
    StaticCache,
)""",
"""from transformers.cache_utils import (
    Cache,
    DynamicCache,
    EncoderDecoderCache,
    StaticCache,
)
try:
    from transformers.cache_utils import OffloadedCache
except ImportError:
    OffloadedCache = None
try:
    from transformers.cache_utils import QuantizedCacheConfig
except ImportError:
    class QuantizedCacheConfig: pass"""
            )

        # Patch CandidateGenerator
        if "from transformers.generation.candidate_generator import (" in content:
            content = content.replace(
"""from transformers.generation.candidate_generator import (
    AssistedCandidateGenerator,
    AssistedCandidateGeneratorDifferentTokenizers,
    CandidateGenerator,
    PromptLookupCandidateGenerator,
    _crop_past_key_values,
    _prepare_attention_mask,
    _prepare_token_type_ids,
)""",
"""try:
    from transformers.generation.candidate_generator import (
        AssistedCandidateGenerator,
        AssistedCandidateGeneratorDifferentTokenizers,
        CandidateGenerator,
        PromptLookupCandidateGenerator,
        _crop_past_key_values,
        _prepare_attention_mask,
        _prepare_token_type_ids,
    )
except ImportError:
    AssistedCandidateGenerator = None
    AssistedCandidateGeneratorDifferentTokenizers = None
    CandidateGenerator = None
    PromptLookupCandidateGenerator = None
    def _crop_past_key_values(model, past_key_values, maximum_length):
        if past_key_values is None: return None
        if hasattr(past_key_values, "crop"):
            past_key_values.crop(maximum_length)
            return past_key_values
        if isinstance(past_key_values, tuple):
            return tuple(tuple(t[:, :, :maximum_length, :] if t is not None else None for t in layer) for layer in past_key_values)
        return past_key_values
    def _prepare_attention_mask(*args, **kwargs): return None
    def _prepare_token_type_ids(*args, **kwargs): return None"""
            )

        # Patch configuration_utils
        if "from transformers.generation.configuration_utils import (" in content and "NEED_SETUP_CACHE_CLASSES_MAPPING" in content:
            content = content.replace(
"""from transformers.generation.configuration_utils import (
    NEED_SETUP_CACHE_CLASSES_MAPPING,
    QUANT_BACKEND_CLASSES_MAPPING,
    GenerationConfig,
    GenerationMode,
)""",
"""try:
    from transformers.generation.configuration_utils import (
        NEED_SETUP_CACHE_CLASSES_MAPPING,
        QUANT_BACKEND_CLASSES_MAPPING,
        GenerationConfig,
        GenerationMode,
    )
except ImportError:
    from transformers.generation.configuration_utils import GenerationConfig, GenerationMode
    NEED_SETUP_CACHE_CLASSES_MAPPING = {}
    QUANT_BACKEND_CLASSES_MAPPING = {}"""
            )

        # Patch forced_decoder_ids
        if "if generation_config.forced_decoder_ids is not None:" in content:
            content = content.replace(
                "if generation_config.forced_decoder_ids is not None:",
                "if getattr(generation_config, 'forced_decoder_ids', None) is not None:"
            )

        with open(gen_utils_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched: {gen_utils_path}")

    # 2. Patch transformers_gpt2.py
    gpt2_path = os.path.join(repo_dir, "indextts/gpt/transformers_gpt2.py")
    if os.path.exists(gpt2_path):
        with open(gpt2_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "from transformers.modeling_utils import SequenceSummary" in content:
            content = content.replace(
                "from transformers.modeling_utils import SequenceSummary",
"""try:
    from transformers.modeling_utils import SequenceSummary
except ImportError:
    from .transformers_modeling_utils import SequenceSummary"""
            )

        with open(gpt2_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched: {gpt2_path}")

    print("Successfully patched index-tts to be compatible with latest transformers!")

if __name__ == "__main__":
    patch_indextts()
