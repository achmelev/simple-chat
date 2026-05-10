from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class CommandResult:
    """Rich result from a command execution.

    output       -- text to print to the user (optional)
    user_message -- if set, injected into the conversation and sent to the LLM
    send_to_llm  -- if True (and no user_message), send the current conversation to the LLM immediately
    """
    output: Optional[str] = None
    user_message: Optional[str] = None
    send_to_llm: bool = False


class Command(ABC):

    @abstractmethod
    def name(self) -> str:
        """Command name, matched against the word after /"""
        pass

    @abstractmethod
    def short_description(self) -> str:
        """One-line description shown in command listings"""
        pass

    @abstractmethod
    def description(self) -> str:
        """Full description of the command and its arguments"""
        pass

    @abstractmethod
    def execute(self, arguments: List[str]) -> Union[str, CommandResult, None]:
        """Execute the command. Returns a string to print, a CommandResult, or None."""
        pass
