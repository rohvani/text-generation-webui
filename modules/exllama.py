import sys
from pathlib import Path

sys.path.insert(0, str(Path("repositories/exllama")))

from modules.logging_colors import logger
from repositories.exllama.generator import ExLlamaGenerator
from repositories.exllama.model import ExLlama, ExLlamaCache, ExLlamaConfig
from repositories.exllama.tokenizer import ExLlamaTokenizer

import modules.shared as shared


class ExllamaModel:
    def __init__(self):
        pass

    @classmethod
    def from_pretrained(self, path_to_model):

        path_to_model = Path("models") / Path(path_to_model)
        tokenizer_model_path = path_to_model / "tokenizer.model"
        model_config_path = path_to_model / "config.json"

        # Find the model checkpoint
        model_path = None
        for ext in ['.safetensors', '.pt', '.bin']:
            found = list(path_to_model.glob(f"*{ext}"))
            if len(found) > 0:
                if len(found) > 1:
                    logger.warning(f'More than one {ext} model has been found. The last one will be selected. It could be wrong.')

                model_path = found[-1]
                break

        config = ExLlamaConfig(str(model_config_path))
        config.model_path = str(model_path)
        config.max_seq_len = 2048

        if (shared.args.gpu_split):
            config.set_auto_map(shared.args.gpu_split)
            config.gpu_peer_fix = True

        model = ExLlama(config)
        tokenizer = ExLlamaTokenizer(str(tokenizer_model_path))
        cache = ExLlamaCache(model)

        result = self()
        result.config = config
        result.model = model
        result.cache = cache
        result.tokenizer = tokenizer
        return result, result


    def generate(self, context="", token_count=20, temperature=1, top_p=1, top_k=50, repetition_penalty=None, alpha_frequency=0.1, alpha_presence=0.1, token_ban=None, token_stop=None, callback=None):
        generator = ExLlamaGenerator(self.model, self.tokenizer, self.cache)
        generator.settings.temperature = temperature
        generator.settings.top_p = top_p
        generator.settings.top_k = top_k
        # generator.settings.typical = typical_p

#        with torch.no_grad():
        text = generator.generate_simple(context, max_new_tokens = token_count)
        # print(text)
        return text.replace(context, "")


    def generate_with_streaming(self, context="", token_count=20, temperature=1, top_p=1, top_k=50, repetition_penalty=None, alpha_frequency=0.1, alpha_presence=0.1, token_ban=None, token_stop=None, callback=None):
        generator = ExLlamaGenerator(self.model, self.tokenizer, self.cache)
        generator.settings.temperature = temperature
        generator.settings.top_p = top_p
        generator.settings.top_k = top_k
        # generator.settings.typical = typical_p

        generator.end_beam_search()
        ids = generator.tokenizer.encode(context)
        generator.gen_begin(ids)
        initial_len = generator.sequence[0].shape[0]
        for i in range(token_count):
            token = generator.gen_single_token()
            yield(generator.tokenizer.decode(generator.sequence[0][initial_len:]))
            if token.item() == generator.tokenizer.eos_token_id: break


    def encode(self, string, **kwargs):
        return self.tokenizer.encode(string)
