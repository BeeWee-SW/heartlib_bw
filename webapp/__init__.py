"""HeartMuLa Studio — a local web UI for the HeartMuLa music generation model.

The package deliberately avoids importing ``torch`` or ``heartlib`` at module
level.  The server must be able to start (and serve a helpful setup screen) on
a machine where neither the dependencies nor the checkpoints are present yet.
"""

__version__ = "1.0.0"
