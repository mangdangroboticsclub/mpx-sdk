"""mpx — consolidated MPX developer CLI.

Robot skills ("move" family, ex mpx-cli) and merchant web skills
("web" family, ex mpx-awa) in one global Python tool.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version

try:
    # Single source of truth: the version in pyproject.toml.  A literal here
    # drifted once already (0.1.0 while the package said 0.1.3) and made
    # `mpx --version` useless for telling two builds apart — which is the one
    # question an operator asks when a skill links against the wrong ABI.
    __version__ = _installed_version("mpx")
except PackageNotFoundError:  # running straight from a source tree
    __version__ = "0.0.0+source"
