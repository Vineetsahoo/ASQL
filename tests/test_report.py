"""Unit tests for the HTML report generator."""

import os
import tempfile
import pytest
from engine.models import Finding
from engine.report import generate_html_report


class TestReportGenerator:
    """Tests for generate_html_report."""

    def test_generate_html_report_creates_file(self):
        findings = [
            Finding(
                rule_id="AP-01",
                rule_name="SELECT_STAR",
                file="sample_sql/test.sql",
                line=1,
                column=8,
                snippet="SELECT * FROM orders",
                message="SELECT * used instead of explicit column list.",
                confidence=0.95,
                rewrite_sql="SELECT id, amount FROM orders",
                cost_signal="FULL_SCAN_DETECTED",
            ),
            Finding(
                rule_id="AP-02",
                rule_name="NON_SARGABLE_PREDICATE",
                file="sample_sql/test2.sql",
                line=5,
                column=12,
                snippet="UPPER(name) = 'FOO'",
                message="Function UPPER() wraps column in predicate <unsafe>.",
                confidence=0.85,
                rewrite_sql=None,
                cost_signal="INDEX_USED",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_report.html")
            generate_html_report(findings, out_file)

            assert os.path.isfile(out_file)
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()

            assert "<!DOCTYPE html>" in content
            assert "SQL Anti-Pattern Detection Report" in content
            assert "Found <strong>2</strong> anti-pattern(s)" in content
            assert "AP-01" in content
            assert "AP-02" in content
            assert "FULL_SCAN_DETECTED" in content
            assert "INDEX_USED" in content
            assert "SELECT id, amount FROM orders" in content
            # Verify HTML escaping
            assert "<unsafe>" not in content
            assert "&lt;unsafe&gt;" in content

    def test_empty_findings_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "empty_report.html")
            generate_html_report([], out_file)
            assert os.path.isfile(out_file)
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Found <strong>0</strong> anti-pattern(s)" in content
