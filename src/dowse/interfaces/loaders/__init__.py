from .base import Loader
from .examples import ExampleLoader
from .prompts import PromptLoader
from .tools import ToolsLoader


class Loaders(ExampleLoader, PromptLoader, ToolsLoader):
    pass


__all__ = ["Loader", "ExampleLoader", "PromptLoader", "ToolsLoader", "Loaders"]
