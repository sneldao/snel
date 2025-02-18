from typing import Any

from dowse.interfaces import Executor

NoOpExecutor = Executor[Any, Any, None]()
