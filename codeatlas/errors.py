class CodeAtlasError(Exception):
    """Expected operational error suitable for machine-readable CLI output."""


class ConfigurationError(CodeAtlasError):
    """Invalid or incomplete CodeAtlas configuration."""


class ParserUnavailableError(CodeAtlasError):
    """The configured deterministic parser is not available."""

