try:
    from code.core.client import AZURE_ENDPOINT, MODEL_REGISTRY, read_config_key
except ModuleNotFoundError:
    from core.client import AZURE_ENDPOINT, MODEL_REGISTRY, read_config_key
