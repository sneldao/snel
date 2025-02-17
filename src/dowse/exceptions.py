class ToolException(Exception):
    pass


class TokenNotFoundError(ToolException):
    pass


class PreprocessorError(Exception):
    pass
