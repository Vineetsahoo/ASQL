"""Integration tests for the scan.py CLI entry point."""

import json
import os
import subprocess
import sys
import tempfile
import pytest


class TestCLIIntegration:
    """End-to-end tests for scan.py command line interface."""

    def test_cli_sample_sql_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_out = os.path.join(tmpdir, "findings.json")
            html_out = os.path.join(tmpdir, "report.html")

            cmd = [
                sys.executable,
                "scan.py",
                "sample_sql",
                "--out", json_out,
                "--html", html_out,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            assert result.returncode == 0, f"CLI failed with error:\n{result.stderr}"

            # Verify JSON file
            assert os.path.isfile(json_out), "JSON output file was not created"
            with open(json_out, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == 15

            # Check PRD v2 §6 schema fields on every finding
            required_keys = {
                "rule_id",
                "rule_name",
                "file",
                "line",
                "column",
                "snippet",
                "message",
                "confidence",
                "rewrite_sql",
                "cost_signal",
                "finding_id",
            }
            for finding in data:
                assert set(finding.keys()) == required_keys
                assert finding["line"] > 0, f"Expected valid line number in {finding}"

            # Verify AP-01 rewrites are present
            ap01_findings = [f for f in data if f["rule_id"] == "AP-01"]
            assert len(ap01_findings) == 5
            for f in ap01_findings:
                assert f["rewrite_sql"] is not None
                assert "orders" in f["rewrite_sql"] or "employees" in f["rewrite_sql"]

            # Verify HTML report
            assert os.path.isfile(html_out), "HTML output file was not created"
            with open(html_out, "r", encoding="utf-8") as f:
                html_text = f.read()
            assert "SQL Anti-Pattern Detection Report" in html_text
            assert "15" in html_text

    def test_cli_invalid_directory(self):
        cmd = [
            sys.executable,
            "scan.py",
            "non_existent_directory_xyz",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode != 0
        assert "not a valid directory" in result.stderr
