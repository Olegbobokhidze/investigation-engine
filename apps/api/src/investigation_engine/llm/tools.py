"""Tools the model can call, each defined by a Pydantic model of its arguments.

The same model gives the JSON schema sent to the LLM and validates what the LLM sends
back, so a tool's description and its parsing can't drift apart.
"""

from pydantic import BaseModel

from investigation_engine.llm.client import ToolCall


class Tool[Args: BaseModel]:
    def __init__(self, name: str, description: str, arguments: type[Args]) -> None:
        self.name = name
        self.description = description
        self._arguments = arguments

    def spec(self) -> dict[str, object]:
        """The tool definition in the chat completions API's format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._arguments.model_json_schema(),
            },
        }

    def parse(self, call: ToolCall) -> Args:
        """Validates the model's arguments; raises `pydantic.ValidationError` if they are wrong."""
        return self._arguments.model_validate_json(call.arguments)
