#!/usr/bin/env python3
"""SQL Anti-Pattern Detection Tool — CLI entry point.

Usage:
    python scan.py sample_sql/ --out findings.json --html report.html

Per PRD v2/v3: single command, walks folder for *.sql files, parses,
runs rules, applies the Flagging System (marking, severities, alternative solutions, rewrites),
runs cost-proxy, outputs console table + JSON + Web3 HTML dashboard.
"""

import argparse
import json
import os
import sys
from typing import List

# Ensure stdout and stderr handle UTF-8 / emojis on Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from engine.parser import scan_directory
from engine.models import Finding, ScannedQuery
from engine.flagger import enrich_finding_with_flag
from engine.rewriter import rewrite_sql_by_rule
from engine.cost_proxy import evaluate_cost_signal, close as close_cost_proxy
from engine.report import generate_html_report


def enrich_findings(findings: List[Finding]) -> None:
    """Post-process findings: apply Flagging System (severities, marked SQL, alternative solutions, rewrites, cost-proxy)."""
    for f in findings:
        # 1. Apply Flagging System metadata & annotations
        enrich_finding_with_flag(f)

        # 2. Attempt automated alternative solution rewrites across rules
        if f.rewrite_sql is None:
            try:
                sql_to_rewrite = f.query or f.snippet
                rewritten = rewrite_sql_by_rule(sql_to_rewrite, f.rule_id)
                if rewritten:
                    f.rewrite_sql = rewritten
            except Exception:
                pass  # Rewrite is optional — don't crash

        # 3. Attempt cost-proxy evaluation
        if f.cost_signal == "NOT_EVALUATED":
            try:
                sql_to_check = f.query or f.snippet
                if not sql_to_check.endswith("..."):
                    signal = evaluate_cost_signal(sql_to_check)
                    f.cost_signal = signal
            except Exception:
                pass  # Cost proxy is optional


def enrich_clean_queries(scanned_files: List[ScannedQuery]) -> None:
    """Evaluate cost signals for clean/passing queries."""
    for sq in scanned_files:
        if sq.status == "PASSED" and sq.cost_signal == "NOT_EVALUATED" and sq.sql.strip():
            try:
                sq.cost_signal = evaluate_cost_signal(sq.sql)
            except Exception:
                sq.cost_signal = "VERIFIED"


def print_console_table(findings: List[Finding], scanned_files: List[ScannedQuery] = None) -> None:
    """Print a plain text summary table to stdout."""
    total_files = len(scanned_files) if scanned_files else len(set(f.file for f in findings))
    clean_files = sum(1 for q in scanned_files if q.status == "PASSED") if scanned_files else 0

    if not findings:
        print("\n  ✅ Zero anti-patterns detected across scanned queries!\n")
        return

    # Column widths
    w_file = max(len(f.file) for f in findings)
    w_file = max(w_file, 4)
    w_rule = 7  # "AP-XX"
    w_sev = 8   # "SEVERITY"
    w_line = 5

    header = f"  {'#':>3}  {'File':<{w_file}}  {'Line':>{w_line}}  {'Rule':<{w_rule}}  {'Sev':<{w_sev}}  Message"
    separator = "  " + "-" * (len(header) + 20)

    print(f"\n{separator}")
    print(f"  🚩 FLAGGING SYSTEM SUMMARY ({len(findings)} anti-pattern(s) flagged across {total_files} files)")
    if clean_files:
        print(f"  ✨ Clean / Passing Queries: {clean_files} | Flagged Queries: {total_files - clean_files}")
    print(separator)
    print(header)
    print(separator)

    for i, f in enumerate(findings, 1):
        msg = f.message
        if len(msg) > 70:
            msg = msg[:67] + "..."
        sev = getattr(f, "severity", "HIGH")
        print(f"  {i:>3}  {f.file:<{w_file}}  {f.line:>{w_line}}  {f.rule_id:<{w_rule}}  {sev:<{w_sev}}  {msg}")

    print(separator)

    rewrites = sum(1 for f in findings if f.rewrite_sql)
    scans = sum(1 for f in findings if f.cost_signal == "FULL_SCAN_DETECTED")
    print(f"  💡 Alternative Solution Rewrites available: {rewrites}/{len(findings)}")
    print(f"  ⚠️  Full scans detected: {scans}")
    print(f"  📊 Cost-proxy evaluated: {sum(1 for f in findings if f.cost_signal != 'NOT_EVALUATED')}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SQL Anti-Pattern Detection & Flagging Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python scan.py sample_sql/ --out findings.json --html report.html"
    )
    parser.add_argument(
        "directory",
        help="Directory containing .sql files to scan",
    )
    parser.add_argument(
        "--out",
        default="findings.json",
        help="Output path for JSON findings (default: findings.json)",
    )
    parser.add_argument(
        "--html",
        default="report.html",
        help="Output path for HTML report (default: report.html)",
    )
    parser.add_argument(
        "--dialect",
        default="sqlite",
        help="SQL dialect to use for parsing (e.g. postgres, bigquery, snowflake, sqlite). Default: sqlite",
    )

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"\n🔍 Scanning SQL files in: {args.directory} (dialect: {args.dialect})\n", file=sys.stderr)

    # Parse and detect (with full scanned query tracking)
    findings, warnings, scanned_files = scan_directory(args.directory, dialect=args.dialect, return_scanned_files=True)

    # Print warnings
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)

    # Enrich findings with Flagging System (marking + severities + rewrites + cost proxy)
    print(f"\n🔧 Running Flagging System (marking + alternative solutions + cost proxy)...", file=sys.stderr)
    enrich_findings(findings)
    enrich_clean_queries(scanned_files)

    # Print console table
    print_console_table(findings, scanned_files)

    # Write JSON output
    try:
        findings_json = [f.to_dict() for f in findings]
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(findings_json, f, indent=2, ensure_ascii=False)
        print(f"  📄 JSON report written to: {args.out}", file=sys.stderr)
    except (OSError, IOError) as e:
        print(f"Error: Could not write JSON output: {e}", file=sys.stderr)
        sys.exit(1)

    # Write HTML report (including ALL scanned files)
    try:
        generate_html_report(findings, args.html, scanned_queries=scanned_files)
        print(f"  🌐 HTML report written to: {args.html} ({len(scanned_files)} queries included)", file=sys.stderr)
    except (OSError, IOError) as e:
        print(f"Error: Could not write HTML report: {e}", file=sys.stderr)
        sys.exit(1)

    # Cleanup
    close_cost_proxy()

    print(f"\n✅ Scan complete. {len(findings)} finding(s) across {len(scanned_files)} queries in {args.directory}\n",
          file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
