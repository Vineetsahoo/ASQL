"""Data models for the SQL Anti-Pattern Detection engine."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
import uuid


@dataclass
class Finding:
    """Represents a single anti-pattern detection finding.
    
    Matches the schema defined in PRD v2 §6 with Flagging System extensions.
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
    severity: str = "HIGH"
    alternative_solution: Optional[str] = None
    marked_sql: Optional[str] = field(default=None, repr=False)

    def to_dict(self, include_extra: bool = True) -> dict:
        """Convert finding to a JSON-serializable dictionary."""
        d = {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "snippet": self.snippet,
            "message": self.message,
            "confidence": self.confidence,
            "rewrite_sql": self.rewrite_sql,
            "cost_signal": self.cost_signal,
            "finding_id": self.finding_id,
        }
        if include_extra:
            d["severity"] = self.severity
            d["alternative_solution"] = self.alternative_solution
        return d


@dataclass
class ScannedQuery:
    """Represents a scanned SQL file/query for complete reporting across all files."""
    file: str
    status: str  # "FLAGGED", "PASSED", "WARNING"
    sql: str
    findings: List[Finding] = field(default_factory=list)
    marked_sql: Optional[str] = None
    cost_signal: str = "NOT_EVALUATED"
    warning: Optional[str] = None
    line_count: int = 1

