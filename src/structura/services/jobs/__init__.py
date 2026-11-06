"""The Job framework: the only way Structura does background work (docs/04 §2)."""

from .job import ErrorInfo, FunctionJob, Job, JobCancelled, JobContext, Lane
from .runner import JobHandle, JobRunner

__all__ = ["ErrorInfo", "FunctionJob", "Job", "JobCancelled", "JobContext", "JobHandle", "JobRunner", "Lane"]
