"""Data models for the SQL Anti-Pattern Detection engine."""

from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid


@dataclass
class Finding:
    """Represents a single anti-pattern detection finding.
    
    Matches the schema defined in PRD v2 §6.
    """
    rule_id: str
    rule_name: str
    file: str
    line: int
    column: int
    snippet: str
    message: str
    confidence: float = 1.0
    rewrite_sql: Optional[str] = None
    cost_signal: str = "NOT_EVALUATED"
    finding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: Optional[str] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Convert finding to a JSON-serializable dictionary."""
        d = asdict(self)
        d.pop("query", None)
        return d
