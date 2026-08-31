"""A single shared slowapi Limiter instance.

This lives in its own tiny module (rather than in main.py) so that both
main.py (which registers it on the app and adds its exception handler) and
the auth router (which applies the `@limiter.limit(...)` decorator to
individual routes) can import it without main.py and the router importing
each other.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate-limit by the caller's IP address.
limiter = Limiter(key_func=get_remote_address)
