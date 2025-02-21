from importlib.util import module_from_spec, spec_from_file_location
from typing import Any, Callable

from pydantic import Field

from .base import Loader


class ToolsLoader(Loader):
    tools: list[Callable] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        tools_path = self._path / "tools.py"
        if tools_path.exists():

            spec = spec_from_file_location("tools", tools_path)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "TOOLS"):
                    self.tools = module.TOOLS
