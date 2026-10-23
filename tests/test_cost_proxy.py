"""Unit tests for SQLite cost-proxy query plan evaluator."""

import pytest
from engine.cost_proxy import evaluate_cost_signal, close


@pytest.fixture(autouse=True)
def cleanup():
    yield
    close()


class TestCostProxy:
    """Tests for evaluate_cost_signal."""

    def test_index_used(self):
        # customers has an index on email
        sql = "SELECT id, email FROM customers WHERE email = 'test@example.com';"
        signal = evaluate_cost_signal(sql)
        assert signal == "INDEX_USED"

    def test_full_scan_unindexed_column(self):
        # orders has no index on status
        sql = "SELECT * FROM orders WHERE status = 'pending';"
        signal = evaluate_cost_signal(sql)
        assert signal == "FULL_SCAN_DETECTED"

    def test_full_scan_non_sargable_on_indexed_column(self):
        # email is indexed, but TRIM(email) prevents index usage
        sql = "SELECT id, name, email FROM customers WHERE TRIM(email) = 'test@example.com';"
        signal = evaluate_cost_signal(sql)
        assert signal == "FULL_SCAN_DETECTED"

    def test_full_scan_year_function(self):
        # order_date is indexed, but YEAR(order_date) wraps it
        sql = "SELECT id, order_date FROM orders WHERE YEAR(order_date) = 2024;"
        signal = evaluate_cost_signal(sql)
        assert signal == "FULL_SCAN_DETECTED"

    def test_not_evaluated_invalid_sql(self):
        sql = "THIS IS NOT VALID SQL !!!"
        signal = evaluate_cost_signal(sql)
        assert signal == "NOT_EVALUATED"

    def test_not_evaluated_unknown_table(self):
        sql = "SELECT * FROM non_existent_table WHERE id = 1;"
        signal = evaluate_cost_signal(sql)
        assert signal == "NOT_EVALUATED"

    def test_not_evaluated_fragment(self):
        # A predicate fragment that cannot be explained on its own
        sql = "UPPER(name) = 'FOO'"
        signal = evaluate_cost_signal(sql)
        assert signal == "NOT_EVALUATED"

    def test_close_clears_cached_results(self):
        evaluate_cost_signal("SELECT id FROM orders WHERE customer_id = 1;")
        assert evaluate_cost_signal.cache_info().currsize == 1

        close()

        assert evaluate_cost_signal.cache_info().currsize == 0
