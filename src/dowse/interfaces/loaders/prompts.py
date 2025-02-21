from typing import Any

from .base import Loader


class PromptLoader(Loader):
    prompt: str | None = None

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        prompt_path = self._path / "PROMPT.txt"
        if prompt_path.exists():
            self.prompt = prompt_path.read_text()
