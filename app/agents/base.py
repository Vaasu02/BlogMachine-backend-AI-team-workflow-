from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AgentResult:
    success: bool
    output: dict
    feedback: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    async def execute(self, input_data: dict) -> AgentResult:
        pass

    async def validate_output(self, output: dict) -> bool:
        return True
