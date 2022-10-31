# https://docs.python-guide.org/writing/structure/
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import save_message  # noqa: F401 E402
