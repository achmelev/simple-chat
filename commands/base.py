from abc import ABC, abstractmethod
from typing import List


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
    def execute(self, arguments: List[str]) -> str:
        """Execute the command with the given positional arguments. Returns a message to display, or None."""
        pass
