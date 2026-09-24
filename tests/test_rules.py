"""Unit tests for AST anti-pattern detection rules: AP-01, AP-02, AP-05."""

import pytest
import sqlglot
from engine.rules import SelectStarRule, NonSargablePredicateRule, UnnecessarySubqueryRule


class TestSelectStarRule:
    """Tests for AP-01: SELECT * detection."""

    @pytest.fixture
    def rule(self):
        return SelectStarRule()

    def test_basic_select_star(self, rule):
        sql = "SELECT * FROM orders WHERE status = 'pending';"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-01"
        assert findings[0].rule_name == "SELECT_STAR"
        assert findings[0].file == "test.sql"
        assert findings[0].line == 1
        assert "SELECT *" in findings[0].message

    def test_select_star_join(self, rule):
        sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id;"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-01"

    def test_select_star_in_subquery(self, rule):
        sql = "SELECT o.id FROM (SELECT * FROM orders WHERE status = 'shipped') o;"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-01"

    def test_count_star_negative_control(self, rule):
        """COUNT(*) must NOT trigger AP-01."""
        sql = "SELECT COUNT(*) FROM orders WHERE status = 'pending';"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_count_star_group_by_having_negative_control(self, rule):
        """COUNT(*) in projection and HAVING must NOT trigger AP-01."""
        sql = """
        SELECT customer_id, COUNT(*) as order_count
        FROM orders
        GROUP BY customer_id
        HAVING COUNT(*) > 5;
        """
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_explicit_columns_negative_control(self, rule):
        """Explicit column list must NOT trigger AP-01."""
        sql = "SELECT id, customer_id, order_date FROM orders;"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0


class TestNonSargablePredicateRule:
    """Tests for AP-02: Non-sargable predicate detection."""

    @pytest.fixture
    def rule(self):
        return NonSargablePredicateRule()

    def test_upper_in_where(self, rule):
        sql = "SELECT id, name FROM customers WHERE UPPER(name) = 'JOHN DOE';"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-02"
        assert "UPPER" in findings[0].message

    def test_trim_in_where(self, rule):
        sql = "SELECT id, name, email FROM customers WHERE TRIM(email) = 'test@example.com';"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-02"
        assert "TRIM" in findings[0].message

    def test_year_in_where(self, rule):
        sql = "SELECT id, order_date FROM orders WHERE YEAR(order_date) = 2024;"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-02"
        assert "YEAR" in findings[0].message

    def test_coalesce_in_join_on(self, rule):
        sql = """
        SELECT o.id, c.name
        FROM orders o
        JOIN customers c ON COALESCE(o.customer_id, 0) = c.id;
        """
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-02"
        assert "COALESCE" in findings[0].message

    def test_function_wrapping_literal_negative_control(self, rule):
        """Function applied to a literal value (not a column) must NOT trigger AP-02."""
        sql = "SELECT id, salary FROM employees WHERE salary > ROUND(50000.555, 2);"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_function_in_projection_negative_control(self, rule):
        """Function in projection list (SELECT) must NOT trigger AP-02."""
        sql = "SELECT id, UPPER(name) as upper_name FROM customers WHERE city = 'Boston';"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_direct_predicate_negative_control(self, rule):
        """Normal predicate without function wrapping must NOT trigger AP-02."""
        sql = "SELECT id, name FROM customers WHERE city = 'Boston' AND id > 10;"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0


class TestUnnecessarySubqueryRule:
    """Tests for AP-05: Unnecessary subquery detection."""

    @pytest.fixture
    def rule(self):
        return UnnecessarySubqueryRule()

    def test_basic_in_subquery(self, rule):
        sql = "SELECT id, name FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE status = 'pending');"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-05"
        assert findings[0].rule_name == "UNNECESSARY_SUBQUERY"
        assert "JOIN" in findings[0].message

    def test_complex_in_subquery(self, rule):
        sql = """
        SELECT c.name FROM customers c
        WHERE c.id IN (
            SELECT o.customer_id
            FROM orders o
            JOIN shipments s ON o.id = s.order_id
            WHERE s.carrier = 'FedEx'
        );
        """
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 1
        assert findings[0].rule_id == "AP-05"

    def test_exists_negative_control(self, rule):
        """EXISTS subqueries are the preferred pattern and must NOT trigger AP-05."""
        sql = """
        SELECT id, name FROM customers c
        WHERE EXISTS (
            SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.status = 'pending'
        );
        """
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_aggregated_subquery_group_by_negative_control(self, rule):
        """Subqueries with GROUP BY/HAVING aggregation must NOT trigger AP-05."""
        sql = """
        SELECT id, name FROM customers
        WHERE id IN (
            SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5
        );
        """
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_aggregate_function_subquery_negative_control(self, rule):
        """Subqueries with aggregate functions in projection must NOT trigger AP-05."""
        sql = "SELECT id FROM orders WHERE total_amount > (SELECT AVG(total_amount) FROM orders);"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0

    def test_in_literal_list_negative_control(self, rule):
        """IN with literal values must NOT trigger AP-05."""
        sql = "SELECT id, name FROM customers WHERE id IN (1, 2, 3, 4, 5);"
        ast = sqlglot.parse_one(sql)
        findings = rule.detect(ast, "test.sql")
        assert len(findings) == 0
