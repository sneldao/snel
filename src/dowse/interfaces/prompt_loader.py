from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel


class PromptLoader(BaseModel):
    prompt: str | None = None
    _path: ClassVar[Path]
    _prompt: ClassVar[str | None] = None

    @classmethod
    def load_prompt(cls) -> None:
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

        prompt_path = cls._path / "PROMPT.txt"
        if prompt_path.exists():
            cls._prompt = prompt_path.read_text()
