from typing import List, Union
from commands.base import Command, CommandResult


class PromptCommand(Command):

    def name(self) -> str:
        return "prompt"

    def short_description(self) -> str:
        return "Send the contents of a file as a user message to the LLM"

    def description(self) -> str:
        return (
            "Usage: /prompt <file>\n"
            "  Reads the file, prints its contents, then sends it to the LLM as a user message."
        )

    def execute(self, arguments: List[str]) -> Union[str, CommandResult, None]:
        if not arguments:
            return "Usage: /prompt <file>"
        path = arguments[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return f"ERROR: could not read file: {e}"
        print(text)
        print()
        return CommandResult(user_message=text)
