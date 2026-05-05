class TextToAbletonError(Exception):
    """Base exception for all TextToAbleton custom errors."""
    pass

class AbletonProxyError(TextToAbletonError):
    """Raised when the MCP proxy fails to communicate with Ableton or returns a status error."""
    pass

class LLMGenerationError(TextToAbletonError):
    """Raised when the Gemini API encounters a hard failure or returns an empty response."""
    pass

class SchemaValidationError(TextToAbletonError):
    """Raised when JSON outputs from the LLM fail Pydantic validation."""
    pass

class ResourceNotFoundError(TextToAbletonError):
    """Raised when a specific requested resource (track, device, parameter) is not found."""
    pass
