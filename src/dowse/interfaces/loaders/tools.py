from typing import Any, Callable

from emp_agents.models import GenericTool

from .base import Loader


class ToolsLoader(Loader):
    _tools: list[Callable | GenericTool] = []

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        tools_path = self._path / "tools.py"
        if tools_path.exists():
            from importlib.util import module_from_spec, spec_from_file_location

            spec = spec_from_file_location("tools", tools_path)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "TOOLS"):
                    self._tools = module.TOOLS
