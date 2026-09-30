"""Unit tests for the SQL parser and directory scanner."""

import os
import tempfile
import pytest
from engine.parser import parse_sql_file, scan_directory


class TestParser:
    """Tests for parse_sql_file and scan_directory."""

    def test_parse_valid_sql_file(self):
        file_path = os.path.join("sample_sql", "ap01_select_star_basic.sql")
        findings, warnings = parse_sql_file(file_path)
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-01"
        assert len(warnings) == 0

    def test_parse_empty_file(self):
        file_path = os.path.join("sample_sql", "edge_empty.sql")
        findings, warnings = parse_sql_file(file_path)
        assert len(findings) == 0
        assert len(warnings) == 1
        assert "empty" in warnings[0].lower()

    def test_parse_malformed_file_isolation(self):
        """Malformed SQL must be caught and logged as warnings without crashing."""
        file_path = os.path.join("sample_sql", "edge_malformed.sql")
        findings, warnings = parse_sql_file(file_path)
        # Should not crash and return gracefully
        assert isinstance(findings, list)
        assert isinstance(warnings, list)
        assert warnings
        assert "parse error" in warnings[0].lower()

    def test_parse_preserves_valid_statements_around_malformed_statement(self, tmp_path):
        sql_file = tmp_path / "mixed.sql"
        sql_file.write_text(
            "SELECT * FROM orders;\n"
            "SELECT FROM WHERE ((( ;\n"
            "SELECT * FROM customers;\n",
            encoding="utf-8",
        )

        findings, warnings = parse_sql_file(str(sql_file))

        assert [finding.rule_id for finding in findings] == ["AP-01", "AP-01"]
        assert warnings

    def test_parse_comments_only_file(self):
        file_path = os.path.join("sample_sql", "edge_comments_only.sql")
        findings, warnings = parse_sql_file(file_path)
        assert len(findings) == 0

    def test_parse_nonexistent_file(self):
        findings, warnings = parse_sql_file("non_existent_file_12345.sql")
        assert len(findings) == 0
        assert len(warnings) == 1

    def test_scan_directory_sample_sql(self):
        findings, warnings = scan_directory("sample_sql")
        # Four rules run across the sample corpus: 5 AP-01, 4 AP-02,
        # 2 AP-03, and 4 AP-05 findings.
        assert len(findings) == 15
        # One warning is expected for each edge fixture: empty and malformed.
        assert len(warnings) == 2

        rule_counts = {}
        for f in findings:
            rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1

        assert rule_counts.get("AP-01") == 5
        assert rule_counts.get("AP-02") == 4
        assert rule_counts.get("AP-03") == 2
        assert rule_counts.get("AP-05") == 4

    def test_scan_directory_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            findings, warnings = scan_directory(tmpdir)
            assert len(findings) == 0
            assert len(warnings) == 1
            assert "no .sql files" in warnings[0].lower()
