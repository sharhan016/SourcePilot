from enum import StrEnum


class WorkflowStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationStatus(StrEnum):
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


class RecommendationStatus(StrEnum):
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentType(StrEnum):
    RESEARCH = "research"
    VERIFICATION = "verification"
    EVALUATION = "evaluation"
    RECOMMENDATION = "recommendation"


STAGE_ORDER = ("research", "verification", "evaluation", "recommendation")

