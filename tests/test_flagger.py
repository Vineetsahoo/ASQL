"""Unit tests for the SQL Anti-Pattern Flagging System."""

import pytest
from engine.models import Finding
from engine.flagger import (
    RULE_SEVERITY,
    ALTERNATIVE_SOLUTIONS,
    mark_sql,
    enrich_finding_with_flag,
)
from engine.rewriter import (
    rewrite_sql_by_rule,
    rewrite_non_sargable,
    rewrite_cartesian_join,
    rewrite_leading_wildcard,
    rewrite_unnecessary_subquery,
    rewrite_union_without_all,
)


class TestFlaggingSystem:
    """Tests for anti-pattern flagging, marking, and alternative solutions."""

    def test_rule_severity_coverage(self):
        expected_rules = ["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"]
        for rule_id in expected_rules:
            assert rule_id in RULE_SEVERITY
            assert RULE_SEVERITY[rule_id] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_alternative_solutions_coverage(self):
        expected_rules = ["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"]
        for rule_id in expected_rules:
            assert rule_id in ALTERNATIVE_SOLUTIONS
            sol = ALTERNATIVE_SOLUTIONS[rule_id]
            assert isinstance(sol, str)
            assert len(sol) > 30

    def test_mark_sql_single_finding(self):
        sql = "SELECT id, name FROM customers WHERE UPPER(name) = 'JOHN';"
        f = Finding(
            rule_id="AP-02",
            rule_name="NON_SARGABLE_PREDICATE",
            file="test.sql",
            line=1,
            column=37,
            snippet="UPPER(name) = 'JOHN'",
            message="Function UPPER() wraps a column reference in a predicate.",
        )
        marked = mark_sql(sql, [f])
        assert "[FLAGGED: AP-02 NON_SARGABLE_PREDICATE]" in marked
        assert "SEVERITY: HIGH" in marked
        assert "ALTERNATIVE:" in marked
        assert "SELECT id, name FROM customers" in marked

    def test_mark_sql_empty_or_no_findings(self):
        sql = "SELECT id FROM orders;"
        assert mark_sql(sql, []) == sql
        assert mark_sql("", []) == ""

    def test_enrich_finding_with_flag(self):
        f = Finding(
            rule_id="AP-03",
            rule_name="CARTESIAN_JOIN",
            file="cartesian.sql",
            line=1,
            column=10,
            snippet="CROSS JOIN products",
            message="Cartesian join hazard.",
            query="SELECT * FROM orders CROSS JOIN products;",
        )
        enrich_finding_with_flag(f)
        assert f.severity == "CRITICAL"
        assert f.alternative_solution is not None
        assert "Cartesian products" in f.alternative_solution
        assert f.marked_sql is not None
        assert "[FLAGGED: AP-03 CARTESIAN_JOIN]" in f.marked_sql

    def test_rewrite_ap02_non_sargable_year(self):
        sql = "SELECT id FROM orders WHERE YEAR(order_date) = 2024;"
        rewritten = rewrite_non_sargable(sql)
        assert rewritten is not None
        assert "order_date >= '2024-01-01'" in rewritten
        assert "order_date < '2025-01-01'" in rewritten

    def test_rewrite_ap02_non_sargable_upper(self):
        sql = "SELECT id FROM customers WHERE UPPER(name) = 'ALICE';"
        rewritten = rewrite_non_sargable(sql)
        assert rewritten is not None
        assert "COLLATE NOCASE" in rewritten

    def test_rewrite_ap03_cartesian_join(self):
        sql = "SELECT * FROM orders o CROSS JOIN customers c;"
        rewritten = rewrite_cartesian_join(sql)
        assert rewritten is not None
        assert "INNER JOIN" in rewritten
        assert "customer_id = customers.id" in rewritten

    def test_rewrite_ap04_leading_wildcard(self):
        sql = "SELECT id FROM customers WHERE name LIKE '%smith';"
        rewritten = rewrite_leading_wildcard(sql)
        assert rewritten is not None
        assert "LIKE 'smith%'" in rewritten

    def test_rewrite_ap05_unnecessary_subquery(self):
        sql = "SELECT c.id FROM customers c WHERE c.id IN (SELECT o.customer_id FROM orders o WHERE o.status = 'pending');"
        rewritten = rewrite_unnecessary_subquery(sql)
        assert rewritten is not None
        assert "EXISTS" in rewritten
        assert "customer_id = c.id" in rewritten

    def test_rewrite_ap06_union_without_all(self):
        sql = "SELECT id FROM orders UNION SELECT id FROM invoices;"
        rewritten = rewrite_union_without_all(sql)
        assert rewritten is not None
        assert "UNION ALL" in rewritten

    def test_rewrite_sql_by_rule_dispatcher(self):
        sql_union = "SELECT id FROM a UNION SELECT id FROM b;"
        assert rewrite_sql_by_rule(sql_union, "AP-06") is not None
        assert "UNION ALL" in rewrite_sql_by_rule(sql_union, "AP-06")
        assert rewrite_sql_by_rule(sql_union, "UNKNOWN") is None
