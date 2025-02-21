from importlib.util import module_from_spec, spec_from_file_location
from typing import Any

from emp_agents.models import Message
from pydantic import Field

from .base import Loader


class ExampleLoader(Loader):
    examples: list[list[Message]] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        examples_path = self._path / "examples.py"
        if examples_path.exists():

            spec = spec_from_file_location("examples", examples_path)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "EXAMPLES"):
                    self.examples = module.EXAMPLES
