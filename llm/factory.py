from llm.openai_client import OpenAIChatClient
from llm.openai_legacy_completions_client import OpenAILegacyCompletionsClient

_CLIENTS = {
    "chat_completions": OpenAIChatClient,
    "legacy_completions": OpenAILegacyCompletionsClient,
}


def create_llm_client(cfg):
    """Instantiate the LLMClient selected by the config's `api_type` key (default: chat_completions)."""
    api_type = cfg.get("api_type", "chat_completions")
    client_cls = _CLIENTS.get(api_type)
    if client_cls is None:
        raise ValueError(f"Unknown api_type '{api_type}'. Valid values: {', '.join(_CLIENTS)}")
    return client_cls()
