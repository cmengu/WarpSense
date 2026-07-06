"""
analysis/ — the pure weld-analysis pipeline.

`analyze()` is the seam: frames in, report out. No DB, no FastAPI, no
persistence, no asyncio. See README.md for the invariant.
"""

from warpsense.analysis.pipeline import AnalysisResult, analyze

__all__ = ["AnalysisResult", "analyze"]
