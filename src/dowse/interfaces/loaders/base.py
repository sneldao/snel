import inspect
from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr


class Loader(BaseModel):
    _path: Path = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        stack = inspect.stack()

        parent_path = Path(__file__).parent.parent

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
        self._path = Path(caller_frame.filename).parent
