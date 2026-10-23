"""Parser wrapper: reads SQL files, builds ASTs, runs rules, collects findings.

Handles errors gracefully per PRD v2 §10:
- Malformed SQL files are logged and skipped (not fatal)
- Empty files are logged and skipped
- Parse failures on one file don't crash the pipeline
"""

import os
import sys
import logging
from typing import List, Tuple
import sqlglot
from engine.models import Finding
from engine.rules import ALL_RULES


def _read_file_safe(file_path: str) -> Tuple[str, Optional[str]]:
    """Read file content with multi-encoding fallback (UTF-8, UTF-16, Latin-1)."""
    encodings = ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
                # If there are null bytes, wrong encoding was used
                if "\x00" not in content:
                    return content, None
        except (UnicodeError, UnicodeDecodeError, OSError):
            continue

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except (OSError, IOError) as e:
        return "", str(e)


def parse_sql_file(file_path: str, dialect: str = "sqlite", return_content: bool = False):
    """Parse a single SQL file and run all rules against it.
    
    Returns:
        Tuple of (findings, warnings) or (findings, warnings, content) if return_content=True.
    """
    findings = []
    warnings = []

    sql_content, read_err = _read_file_safe(file_path)
    if read_err:
        warnings.append(f"Could not read {file_path}: {read_err}")
        return (findings, warnings, sql_content) if return_content else (findings, warnings)

    # Handle empty files
    stripped = sql_content.strip()
    if not stripped:
        warnings.append(f"Skipping empty file: {file_path}")
        return (findings, warnings, sql_content) if return_content else (findings, warnings)

    # Parse with sqlglot. Strict parsing keeps malformed files visible as warnings.
    try:
        statements = sqlglot.parse(sql_content, read=dialect, error_level=sqlglot.ErrorLevel.RAISE)
    except Exception as e:
        warnings.append(f"Parse error in {file_path} (dialect={dialect}): {e}")
        statements = []

        # Retry in warning mode to salvage valid statements
        sqlglot_logger = logging.getLogger("sqlglot")
        was_disabled = sqlglot_logger.disabled
        sqlglot_logger.disabled = True
        try:
            candidates = sqlglot.parse(sql_content, read=dialect, error_level=sqlglot.ErrorLevel.WARN)
        except Exception:
            candidates = []
        finally:
            sqlglot_logger.disabled = was_disabled

        for candidate in candidates:
            if candidate is None:
                continue
            try:
                statements.append(
                    sqlglot.parse_one(
                        candidate.sql(),
                        read=dialect,
                        error_level=sqlglot.ErrorLevel.RAISE,
                    )
                )
            except Exception:
                continue

    # Run all rules against each parsed statement
    for ast in statements:
        if ast is None:
            continue
        for rule in ALL_RULES:
            try:
                rule_findings = rule.detect(ast, file_path, dialect=dialect)
                findings.extend(rule_findings)
            except Exception as e:
                warnings.append(
                    f"Rule {rule.rule_id} failed on {file_path}: {e}"
                )

    if return_content:
        return findings, warnings, sql_content
    return findings, warnings


def scan_directory(directory: str, dialect: str = "sqlite", return_scanned_files: bool = False):
    """Scan all .sql files in a directory tree.
    
    Returns:
        (all_findings, all_warnings) or (all_findings, all_warnings, all_scanned_files)
    """
    from engine.models import ScannedQuery

    all_findings = []
    all_warnings = []
    all_scanned_files: List[ScannedQuery] = []
    sql_files = []

    # Collect all .sql files
    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if fname.lower().endswith(".sql"):
                sql_files.append(os.path.join(root, fname))

    if not sql_files:
        all_warnings.append(f"No .sql files found in {directory}")
        if return_scanned_files:
            return all_findings, all_warnings, all_scanned_files
        return all_findings, all_warnings

    # Process each file
    for file_path in sql_files:
        rel_path = os.path.relpath(file_path, start=os.getcwd())
        findings, warnings, sql_content = parse_sql_file(file_path, dialect=dialect, return_content=True)

        # Update file paths to relative
        for f in findings:
            f.file = rel_path

        all_findings.extend(findings)
        all_warnings.extend(warnings)

        # Determine scanned query status
        if warnings and not findings and not sql_content.strip():
            status = "WARNING"
            warning_msg = "; ".join(warnings)
        elif warnings and not findings:
            status = "WARNING"
            warning_msg = "; ".join(warnings)
        elif findings:
            status = "FLAGGED"
            warning_msg = None
        else:
            status = "PASSED"
            warning_msg = None

        all_scanned_files.append(ScannedQuery(
            file=rel_path,
            status=status,
            sql=sql_content,
            findings=findings,
            warning=warning_msg,
            line_count=len(sql_content.splitlines()) or 1,
        ))

        # Print progress
        status_msg = f"  ✓ {rel_path}: {len(findings)} finding(s)"
        if warnings:
            status_msg += f" ({len(warnings)} warning(s))"
        print(status_msg, file=sys.stderr)

    if return_scanned_files:
        return all_findings, all_warnings, all_scanned_files
    return all_findings, all_warnings

