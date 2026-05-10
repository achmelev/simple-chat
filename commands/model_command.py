from typing import List, Union
from commands.base import Command, CommandResult


class ModelCommand(Command):

    def __init__(self, cfg: dict):
        self._cfg = cfg

    def name(self) -> str:
        return "model"

    def short_description(self) -> str:
        return "List available models or switch to a different model"

    def description(self) -> str:
        return (
            "Usage: /model [model_id]\n"
            "  Without arguments: lists all models available from the configured provider.\n"
            "  With a model id: switches to that model if it is available.\n"
            "  The current model is marked with *."
        )

    def execute(self, arguments: List[str]) -> Union[str, CommandResult, None]:
        models = self._fetch_models()
        if isinstance(models, str):
            return models

        if not arguments:
            current = self._cfg.get("model", "")
            lines = [f"  {'* ' if m == current else '  '}{m}" for m in sorted(models)]
            return "\n".join(lines)

        target = arguments[0]
        if target not in models:
            return f"Unknown model: {target}"
        self._cfg["model"] = target
        return f"Model set to {target}"

    def _fetch_models(self):
        try:
            import httpx
            from openai import OpenAI
            client = OpenAI(
                base_url=self._cfg["llm_url"].rstrip("/"),
                api_key=self._cfg["api_key"],
                http_client=httpx.Client(verify=self._cfg.get("ssl_verify", True)),
            )
            return {m.id for m in client.models.list().data}
        except Exception as e:
            return f"ERROR: could not fetch models: {e}"
