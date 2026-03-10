"""Random username provider for anti-bot detection."""

import random
import string


def generate_random_username(prefix: str = "user", length: int = 8) -> str:
    """Generate a random username.

    Args:
        prefix: Optional prefix (e.g. 'user').
        length: Length of random suffix.

    Returns:
        Username like 'user_abc12xyz'.
    """
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(random.choices(chars, k=length))
    return f"{prefix}_{suffix}"


class UsernameProvider:
    """Provider for random usernames."""

    def __init__(self, prefix: str = "user", length: int = 8):
        self._prefix = prefix
        self._length = length

    def get(self) -> str:
        """Generate and return a random username."""
        return generate_random_username(prefix=self._prefix, length=self._length)
