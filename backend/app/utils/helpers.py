"""
Helper Utility Functions
"""
import uuid


def generate_uuid() -> str:
    """Generates standard UUID4 string."""
    return str(uuid.uuid4())
