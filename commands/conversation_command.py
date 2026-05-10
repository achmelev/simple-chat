import re
from typing import List, Union
from commands.base import Command, CommandResult


def parse_conversation_file(text: str) -> list:
    messages = []
    # Split on opening role tags; content runs until the next tag or EOF.
    # Optional closing tags (e.g. </user>) are stripped from content if present.
    pattern = re.compile(r'<(system|user|assistant)>', re.IGNORECASE)
    parts = pattern.split(text)
    # After split with a capturing group: [pre, role1, content1, role2, content2, ...]
    i = 1
    while i + 1 <= len(parts) - 1:
        role = parts[i].lower()
        content = parts[i + 1]
        # Remove optional closing tag at end of content
        content = re.sub(r'\s*</' + role + r'>\s*$', '', content, flags=re.IGNORECASE).strip()
        if content:
            messages.append({"role": role, "content": content})
        i += 2
    return messages


class ConversationCommand(Command):

    def __init__(self, conversation: list, tool_registry):
        self._conversation = conversation
        self._tool_registry = tool_registry

    def name(self) -> str:
        return "conversation"

    def short_description(self) -> str:
        return "Load a conversation from a file and send it to the LLM"

    def description(self) -> str:
        return (
            "Usage: /conversation <file>\n"
            "  Clears the current conversation, loads messages from the file,\n"
            "  resets tools, and sends the conversation to the LLM.\n"
            "  File format: delimit messages with <system>, <user>, <assistant> tags.\n"
            "  The configured system prompt is discarded."
        )

    def execute(self, arguments: List[str]) -> Union[str, CommandResult, None]:
        if not arguments:
            return "Usage: /conversation <file>"
        path = arguments[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return f"ERROR: could not read file: {e}"

        messages = parse_conversation_file(text)
        if not messages:
            return "ERROR: no messages found in file (use <system>, <user>, <assistant> tags)"

        self._conversation.clear()
        self._conversation.extend(messages)
        self._tool_registry.reset()

        return CommandResult(output=f"Loaded {len(messages)} messages from '{path}'.", send_to_llm=True)
