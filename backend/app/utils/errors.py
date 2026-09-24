"""
Custom Domain Exception Types
"""


class FarmerAssistException(Exception):
    """Base application exception."""
    pass


class OutOfDomainException(FarmerAssistException):
    """Raised when query is outside agriculture scope."""
    pass


class LowConfidenceException(FarmerAssistException):
    """Raised when intent classifier confidence is below threshold."""
    pass


class ModelUnavailableException(FarmerAssistException):
    """Raised when local model asset is missing or fails to load."""
    pass
