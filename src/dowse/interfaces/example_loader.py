from pathlib import Path
from typing import ClassVar

from emp_agents.models import Message
from pydantic import BaseModel, Field, PrivateAttr


class ExampleLoader(BaseModel):
    _examples: list[list[Message]] = PrivateAttr(default_factory=list)
    examples: list[list[Message]] = Field(default_factory=list)
    _path: ClassVar[Path]

    @classmethod
    def load_examples(cls) -> None:
        import inspect

        stack = inspect.stack()

        parent_path = Path(__file__).parent

        caller_frame = None
        for frame_info in stack:
            filename = frame_info.filename
            if filename.startswith("<frozen"):
                continue
            if Path(filename).is_relative_to(parent_path):
                continue
            if "pydantic" not in filename:
                caller_frame = frame_info
                break

        assert caller_frame is not None
        cls._path = Path(caller_frame.filename).parent

        examples_path = cls._path / "examples.py"
        if examples_path.exists():
            from importlib.util import module_from_spec, spec_from_file_location

            spec = spec_from_file_location("examples", examples_path)
            if spec and spec.loader:
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "EXAMPLES"):
                    cls._examples = module.EXAMPLES
