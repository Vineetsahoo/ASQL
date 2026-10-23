"""Flagging System for SQL Anti-Pattern Engine.

Performs static anti-pattern marking, severity classification,
and alternative solution enrichment across all detected anti-patterns.
"""

from typing import List, Optional, Dict
from engine.models import Finding


# Severity classification matrix
RULE_SEVERITY: Dict[str, str] = {
    "AP-01": "HIGH",       # Unbounded SELECT * (unnecessary I/O, schema coupling)
    "AP-02": "HIGH",       # Non-Sargable Predicate (index suppression, table scan)
    "AP-03": "CRITICAL",   # Cartesian Join Hazard (exponential N x M row explosion)
    "AP-04": "CRITICAL",   # Leading Wildcard LIKE (unavoidable full table scan)
    "AP-05": "MEDIUM",     # Unnecessary Subquery (unoptimized subquery materialization)
    "AP-06": "LOW",        # UNION without ALL (redundant deduplication sort)
}

# Educational and architectural alternative solution rationales
ALTERNATIVE_SOLUTIONS: Dict[str, str] = {
    "AP-01": (
        "Enumerate explicit projection columns (e.g., SELECT id, customer_id, total_amount FROM orders). "
        "Wildcard projections force the engine to fetch all column data from disk, bypass covering index scans, "
        "waste memory and network throughput, and introduce breakage when table schemas change."
    ),
    "AP-02": (
        "Invert predicates so functions operate on constants/literals rather than column references (SARGable rewrite). "
        "For example, transform YEAR(order_date) = 2024 into date range order_date >= '2024-01-01' AND order_date < '2025-01-01'. "
        "For case-insensitivity, utilize case-insensitive collations (e.g. COLLATE NOCASE) or functional indexes."
    ),
    "AP-03": (
        "Supply explicit ON or USING join conditions linking primary and foreign keys (e.g., JOIN customers ON orders.customer_id = customers.id). "
        "Cartesian products generate N × M rows, causing severe temporary workfile spills, buffer pool thrashing, and memory crashes."
    ),
    "AP-04": (
        "Convert leading wildcard patterns (LIKE '%term') into prefix searches (LIKE 'term%') to leverage B-Tree index range scans. "
        "If full substring or fuzzy search is required, implement Full-Text Search (FTS), trigram indexes (e.g., pg_trgm), or inverted search indexes."
    ),
    "AP-05": (
        "Rewrite WHERE col IN (SELECT col FROM ...) as an explicit INNER JOIN or an EXISTS (...) semi-join. "
        "Correlated and unaggregated IN subqueries can force row-by-row re-evaluation or suboptimal materialization, "
        "whereas JOIN/EXISTS enables the optimizer to choose hash joins or index nested loops."
    ),
    "AP-06": (
        "Replace UNION with UNION ALL unless duplicate elimination is strictly required. "
        "UNION invokes an implicit DISTINCT operation requiring memory sorting or hashing across all input streams, "
        "which incurs high CPU and disk overhead."
    ),
}


def mark_sql(sql: str, findings: List[Finding]) -> str:
    """Inject syntax-valid SQL comments flagging each anti-pattern right at its location.
    
    Returns the annotated SQL string.
    """
    if not sql or not sql.strip():
        return sql

    lines = sql.splitlines()
    if not findings:
        return sql

    # Group findings by line number (1-indexed)
    line_findings: Dict[int, List[Finding]] = {}
    for f in findings:
        # If line is 0 or outside line bounds, anchor to line 1
        target_line = f.line if 1 <= f.line <= len(lines) else 1
        line_findings.setdefault(target_line, []).append(f)

    annotated_lines = []
    for line_idx, line_content in enumerate(lines, 1):
        if line_idx in line_findings:
            for f in line_findings[line_idx]:
                sev = RULE_SEVERITY.get(f.rule_id, "HIGH")
                marker = (
                    f"-- ============================================================================\n"
                    f"-- [FLAGGED: {f.rule_id} {f.rule_name}] | SEVERITY: {sev}\n"
                    f"-- ISSUE: {f.message}\n"
                    f"-- ALTERNATIVE: {ALTERNATIVE_SOLUTIONS.get(f.rule_id, 'Refactor query logic.')}\n"
                    f"-- ============================================================================"
                )
                annotated_lines.append(marker)
        annotated_lines.append(line_content)

    return "\n".join(annotated_lines)


def enrich_finding_with_flag(finding: Finding, query_sql: Optional[str] = None) -> None:
    """Enrich a Finding with severity, alternative solution text, and marked SQL."""
    finding.severity = RULE_SEVERITY.get(finding.rule_id, "HIGH")
    finding.alternative_solution = ALTERNATIVE_SOLUTIONS.get(
        finding.rule_id,
        "Refactor query using indexing and explicit relational algebra."
    )
    sql_to_mark = query_sql or finding.query or finding.snippet
    if sql_to_mark:
        finding.marked_sql = mark_sql(sql_to_mark, [finding])
