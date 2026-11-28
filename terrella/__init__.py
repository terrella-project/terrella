"""Terrella: a homelab-scale personal AI stack.

The ``terrella`` command provisions and manages the stack from one validated
``terrella.yaml`` (ADR-0001, ADR-0006). The commands land through the M1
milestone; see ROADMAP.md.
"""

# The only place the version is written: pyproject.toml reads it at build time
# (tool.hatch.version), and `terrella --version` prints it.
__version__ = "0.1.0.dev0"
