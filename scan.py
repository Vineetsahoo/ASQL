#!/usr/bin/env python3
"""SQL Anti-Pattern Detection Tool — CLI entry point.

Usage:
    python scan.py sample_sql/ --out findings.json --html report.html

Per PRD v2 §7: single command, walks folder for *.sql files, parses,
runs rules, attempts rewrites and cost-proxy, outputs console table + JSON + HTML.
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
from engine.models import Finding
from engine.rewriter import rewrite_select_star
from engine.cost_proxy import evaluate_cost_signal, close as close_cost_proxy
from engine.report import generate_html_report


def enrich_findings(findings: List[Finding]) -> None:
    """Post-process findings: attempt rewrites and cost-proxy evaluation."""
    for f in findings:
        # Attempt SELECT * rewrite for AP-01 findings
        if f.rule_id == "AP-01" and f.rewrite_sql is None:
            try:
                sql_to_rewrite = f.query or f.snippet
                rewritten = rewrite_select_star(sql_to_rewrite)
                if rewritten:
                    f.rewrite_sql = rewritten
            except Exception:
                pass  # Rewrite is optional — don't crash

        # Attempt cost-proxy evaluation
        if f.cost_signal == "NOT_EVALUATED":
            try:
                # Prefer full query if available, falling back to snippet
                sql_to_check = f.query or f.snippet
                # Remove trailing ... if snippet was truncated
                if sql_to_check.endswith("..."):
                    f.cost_signal = "NOT_EVALUATED"
                else:
                    signal = evaluate_cost_signal(sql_to_check)
                    f.cost_signal = signal
            except Exception:
                pass  # Cost proxy is optional


def print_console_table(findings: List[Finding]) -> None:
    """Print a plain text summary table to stdout."""
    if not findings:
        print("\n  ✅ No anti-patterns detected!\n")
        return

    # Column widths
    w_file = max(len(f.file) for f in findings)
    w_file = max(w_file, 4)  # minimum "File"
    w_rule = 7  # "AP-XX"
    w_line = 5

    header = f"  {'#':>3}  {'File':<{w_file}}  {'Line':>{w_line}}  {'Rule':<{w_rule}}  Message"
    separator = "  " + "-" * (len(header) + 20)

    print(f"\n{separator}")
    print(f"  📋 FINDINGS SUMMARY ({len(findings)} anti-pattern(s) detected)")
    print(separator)
    print(header)
    print(separator)

    for i, f in enumerate(findings, 1):
        msg = f.message
        if len(msg) > 80:
            msg = msg[:77] + "..."
        print(f"  {i:>3}  {f.file:<{w_file}}  {f.line:>{w_line}}  {f.rule_id:<{w_rule}}  {msg}")

    print(separator)

    # Show rewrite count
    rewrites = sum(1 for f in findings if f.rewrite_sql)
    scans = sum(1 for f in findings if f.cost_signal == "FULL_SCAN_DETECTED")
    print(f"  💡 Rewrites available: {rewrites}")
    print(f"  ⚠️  Full scans detected: {scans}")
    print(f"  📊 Cost-proxy evaluated: {sum(1 for f in findings if f.cost_signal != 'NOT_EVALUATED')}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SQL Anti-Pattern Detection Tool (MVP)",
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

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"\n🔍 Scanning SQL files in: {args.directory}\n", file=sys.stderr)

    # Parse and detect
    findings, warnings = scan_directory(args.directory)

    # Print warnings
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)

    # Enrich findings with rewrites and cost signals
    print(f"\n🔧 Enriching findings (rewrites + cost proxy)...", file=sys.stderr)
    enrich_findings(findings)

    # Print console table
    print_console_table(findings)

    # Write JSON output
    try:
        findings_json = [f.to_dict() for f in findings]
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(findings_json, f, indent=2, ensure_ascii=False)
        print(f"  📄 JSON report written to: {args.out}", file=sys.stderr)
    except (OSError, IOError) as e:
        print(f"Error: Could not write JSON output: {e}", file=sys.stderr)
        sys.exit(1)

    # Write HTML report
    try:
        generate_html_report(findings, args.html)
        print(f"  🌐 HTML report written to: {args.html}", file=sys.stderr)
    except (OSError, IOError) as e:
        print(f"Error: Could not write HTML report: {e}", file=sys.stderr)
        sys.exit(1)

    # Cleanup
    close_cost_proxy()

    print(f"\n✅ Scan complete. {len(findings)} finding(s) across {args.directory}\n",
          file=sys.stderr)

    # Exit 0 even if individual files had parse errors (those are warnings)
    sys.exit(0)


if __name__ == "__main__":
    main()
