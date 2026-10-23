"""Unit tests for the auto-rewriter module (AP-01 SELECT * -> explicit columns)."""

import pytest
from engine.rewriter import rewrite_select_star, SCHEMA_MAP


class TestRewriter:
    """Tests for rewrite_select_star."""

    def test_single_table_expansion(self):
        sql = "SELECT * FROM orders WHERE status = 'pending';"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        # All columns from orders must be present
        for col in SCHEMA_MAP["orders"]:
            assert col in rewritten
        assert "*" not in rewritten

    def test_join_expansion_with_aliases(self):
        sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        # Must have columns qualified with o. and c.
        assert "o.id" in rewritten
        assert "c.name" in rewritten
        assert "o.total_amount" in rewritten
        assert "c.email" in rewritten

    def test_order_by_and_limit_preserved(self):
        sql = "SELECT * FROM employees ORDER BY salary DESC LIMIT 10;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        assert "employees" in rewritten
        assert "ORDER BY" in rewritten
        assert "LIMIT 10" in rewritten
        for col in SCHEMA_MAP["employees"]:
            assert col in rewritten

    def test_subquery_expansion(self):
        sql = "SELECT o.id FROM (SELECT * FROM orders WHERE status = 'shipped') o WHERE o.total_amount > 100;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        for col in SCHEMA_MAP["orders"]:
            assert col in rewritten

    def test_nested_selects_keep_table_columns_scoped(self):
        sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id WHERE EXISTS (SELECT * FROM products p WHERE p.id = o.id);"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        assert "o.total_amount" in rewritten
        assert "c.email" in rewritten
        assert "p.price" not in rewritten

    def test_no_star_returns_none(self):
        sql = "SELECT id, name FROM customers WHERE city = 'Boston';"
        rewritten = rewrite_select_star(sql)
        assert rewritten is None

    def test_count_star_returns_none(self):
        sql = "SELECT COUNT(*) FROM orders WHERE status = 'pending';"
        rewritten = rewrite_select_star(sql)
        assert rewritten is None

    def test_unknown_table_returns_none(self):
        sql = "SELECT * FROM unknown_table_xyz WHERE id = 1;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is None

    def test_invalid_sql_returns_none(self):
        sql = "NOT A VALID SQL STATEMENT !!!"
        rewritten = rewrite_select_star(sql)
        assert rewritten is None

    def test_table_star_expansion(self):
        sql = "SELECT o.* FROM orders o;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        assert "o.id" in rewritten
        assert "o.customer_id" in rewritten

    def test_table_star_unknown_table(self):
        sql = "SELECT u.* FROM unknown_table u;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is None
        
    def test_table_star_mixed(self):
        sql = "SELECT o.*, u.* FROM orders o CROSS JOIN unknown_table u;"
        rewritten = rewrite_select_star(sql)
        assert rewritten is not None
        assert "o.id" in rewritten
        assert "u.*" in rewritten
