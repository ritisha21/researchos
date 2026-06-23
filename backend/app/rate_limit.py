"""
app/rate_limit.py
───────────────────
Shared slowapi Limiter instance.

This lives in its own module (not in main.py) specifically to avoid a
circular import: routes need to import `limiter` to decorate their
endpoints, but main.py imports the routes themselves. Routes importing
from main.py would create a cycle; importing from this standalone module
does not.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)