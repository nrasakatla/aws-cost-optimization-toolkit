"""Provider registry imports.

Keeping these imports here (rather than in base.py) avoids circular imports and
lets the live boto3 modules be registered only when explicitly imported.
"""

from . import (
    base,  # noqa: F401
    sample,  # noqa: F401
)
