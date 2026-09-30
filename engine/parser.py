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


def parse_sql_file(file_path: str) -> Tuple[List[Finding], List[str]]:
    """Parse a single SQL file and run all rules against it.
    
    Returns:
        Tuple of (findings, warnings). Warnings are non-fatal messages
        about parse errors or empty files.
    """
    findings = []
    warnings = []

    # Read file content
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sql_content = f.read()
    except (OSError, IOError) as e:
        warnings.append(f"Could not read {file_path}: {e}")
        return findings, warnings

    # Handle empty files
    stripped = sql_content.strip()
    if not stripped:
        warnings.append(f"Skipping empty file: {file_path}")
        return findings, warnings

    # Parse with sqlglot. Strict parsing keeps malformed files visible as warnings.
    try:
        statements = sqlglot.parse(sql_content, error_level=sqlglot.ErrorLevel.RAISE)
    except Exception as e:
        warnings.append(f"Parse error in {file_path}: {e}")
        statements = []

        # RAISE rejects the entire input when one statement is malformed. Retry
        # in warning mode, then strictly validate each recovered statement so
        # valid statements in the same file are still analyzed.
        sqlglot_logger = logging.getLogger("sqlglot")
        was_disabled = sqlglot_logger.disabled
        sqlglot_logger.disabled = True
        try:
            candidates = sqlglot.parse(sql_content, error_level=sqlglot.ErrorLevel.WARN)
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
                rule_findings = rule.detect(ast, file_path)
                findings.extend(rule_findings)
            except Exception as e:
                warnings.append(
                    f"Rule {rule.rule_id} failed on {file_path}: {e}"
                )

    return findings, warnings


def scan_directory(directory: str) -> Tuple[List[Finding], List[str]]:
    """Scan all .sql files in a directory tree.
    
    Returns:
        Tuple of (all_findings, all_warnings).
    """
    all_findings = []
    all_warnings = []
    sql_files = []

    # Collect all .sql files
    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if fname.lower().endswith(".sql"):
                sql_files.append(os.path.join(root, fname))

    if not sql_files:
        all_warnings.append(f"No .sql files found in {directory}")
        return all_findings, all_warnings

    # Process each file
    for file_path in sql_files:
        # Use relative path for cleaner output
        rel_path = os.path.relpath(file_path, start=os.getcwd())
        findings, warnings = parse_sql_file(file_path)

        # Update file paths to relative
        for f in findings:
            f.file = rel_path

        all_findings.extend(findings)
        all_warnings.extend(warnings)

        # Print progress
        status = f"  ✓ {rel_path}: {len(findings)} finding(s)"
        if warnings:
            status += f" ({len(warnings)} warning(s))"
        print(status, file=sys.stderr)

    return all_findings, all_warnings
