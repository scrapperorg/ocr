"""Utility module for the application."""
from typing import Any, Dict, Set


def all_keys_but(dictionary: Dict[Any, Any], keys: Set[Any]) -> Dict[Any, Any]:
    """Utility to reduce dictionary to all keys but the ones specified."""
    return {k: v for k, v in dictionary.items() if k not in keys}
