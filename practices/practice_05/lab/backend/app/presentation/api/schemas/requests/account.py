from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

UsernamePrefix = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=100,
    ),
]
