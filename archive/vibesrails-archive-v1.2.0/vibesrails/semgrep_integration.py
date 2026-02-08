"""Semgrep integration helpers -- re-exports for test discoverability."""

from vibesrails.result_merger import ResultMerger, UnifiedResult
from vibesrails.semgrep_adapter import SemgrepAdapter, SemgrepResult

__all__ = ["SemgrepAdapter", "SemgrepResult", "ResultMerger", "UnifiedResult"]
