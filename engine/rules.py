"""Anti-pattern detection rules using sqlglot AST analysis.

Rules implemented (MVP scope per PRD v2 §4):
  AP-01: SELECT_STAR — SELECT * in projection (excluding COUNT(*))
  AP-02: NON_SARGABLE_PREDICATE — function wrapping a column in WHERE/ON
  AP-05: UNNECESSARY_SUBQUERY — WHERE col IN (SELECT ...) on non-aggregated subquery
"""

from typing import List, Tuple
from sqlglot import expressions as exp
from engine.models import Finding


def _get_node_line_col(node: exp.Expression) -> Tuple[int, int]:
    """Extract line and column numbers from node or its child tokens."""
    if hasattr(node, "meta") and node.meta.get("line"):
        return node.meta.get("line", 0), node.meta.get("col", 0)
    for child in node.walk():
        if hasattr(child, "meta") and child.meta.get("line"):
            return child.meta.get("line", 0), child.meta.get("col", 0)
    return 0, 0


class BaseRule:
    """Base class for all anti-pattern detection rules."""
    rule_id: str = ""
    rule_name: str = ""

    def detect(self, ast: exp.Expression, file_path: str) -> List[Finding]:
        raise NotImplementedError


class SelectStarRule(BaseRule):
    """AP-01: Detects SELECT * in query projections.
    
    Excludes COUNT(*) which is a valid and common pattern.
    """
    rule_id = "AP-01"
    rule_name = "SELECT_STAR"

    def detect(self, ast: exp.Expression, file_path: str) -> List[Finding]:
        findings = []
        query_sql = ast.sql(dialect="sqlite")

        for select in ast.find_all(exp.Select):
            for star_node in select.find_all(exp.Star):
                # Check if the Star is inside a COUNT or other aggregate function.
                # Walk up parents to see if it's an argument to Count/func.
                parent = star_node.parent
                is_in_aggregate = False
                while parent is not None:
                    if isinstance(parent, (exp.Count, exp.Anonymous)):
                        is_in_aggregate = True
                        break
                    # Stop walking up once we reach the Select node itself
                    if isinstance(parent, exp.Select):
                        break
                    parent = parent.parent

                if is_in_aggregate:
                    continue

                # Check the Star is a direct projection column (in select.expressions)
                # not something nested inside a subquery
                star_in_projection = False
                check_parent = star_node.parent
                while check_parent is not None:
                    if isinstance(check_parent, exp.Select):
                        if check_parent is select:
                            star_in_projection = True
                        break
                    check_parent = check_parent.parent

                if not star_in_projection:
                    continue

                # Get the SQL snippet for context
                snippet = select.sql(dialect="sqlite")
                # Truncate very long snippets
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."

                line, col = _get_node_line_col(star_node)

                findings.append(Finding(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    file=file_path,
                    line=line,
                    column=col,
                    snippet=snippet,
                    message="SELECT * used instead of explicit column list. "
                            "This fetches unnecessary data and breaks when schema changes.",
                    confidence=0.95,
                    query=query_sql,
                ))

        return findings


class NonSargablePredicateRule(BaseRule):
    """AP-02: Detects function calls wrapping column references in WHERE/JOIN ON.
    
    Examples: YEAR(col) = 2024, UPPER(col) = 'FOO', COALESCE(col, 0) > 5
    These prevent index usage.
    
    Negative control: function wrapping a literal (not a column) should NOT trigger.
    """
    rule_id = "AP-02"
    rule_name = "NON_SARGABLE_PREDICATE"

    # Common functions that, when wrapping a column, make predicates non-sargable
    WATCHED_FUNCTIONS = {
        "year", "month", "day", "date", "upper", "lower", "trim", "ltrim",
        "rtrim", "substring", "substr", "left", "right", "coalesce",
        "cast", "convert", "isnull", "ifnull", "nvl", "replace",
        "char_length", "length", "len", "abs", "round", "floor", "ceil",
        "datepart", "datediff", "dateadd", "extract",
    }

    def detect(self, ast: exp.Expression, file_path: str) -> List[Finding]:
        findings = []
        query_sql = ast.sql(dialect="sqlite")
        seen_locations = set()

        predicate_containers = []
        for where in ast.find_all(exp.Where):
            predicate_containers.append(where)
        for join in ast.find_all(exp.Join):
            on_clause = join.args.get("on")
            if on_clause:
                predicate_containers.append(on_clause)

        for container in predicate_containers:
            for func_node in container.walk():
                if not isinstance(func_node, exp.Func):
                    continue
                if isinstance(func_node, (exp.Select, exp.Where)):
                    continue

                func_name = self._function_name(func_node)
                if func_name is None:
                    continue

                if func_name in self.WATCHED_FUNCTIONS and self._has_column_argument(func_node):
                    self._add_finding(findings, func_node, file_path, func_name, query_sql, seen_locations)

        return findings

    def _function_name(self, func_node: exp.Expression) -> str:
        """Normalize sqlglot function names from anonymous and typed function subclasses."""
        if isinstance(func_node, exp.Anonymous):
            name = getattr(func_node, "name", None)
            if isinstance(name, str) and name.strip():
                return name.lower()
            if hasattr(func_node, "this") and isinstance(func_node.this, exp.Identifier):
                return func_node.this.name.lower()

        name = getattr(func_node, "name", None)
        if isinstance(name, str) and name.strip():
            return name.lower()

        sql_name = getattr(func_node, "sql_name", None)
        if callable(sql_name):
            sql_name = sql_name()
        if isinstance(sql_name, str) and sql_name.strip():
            return sql_name.lower()

        return type(func_node).__name__.lower()

    def _has_column_argument(self, func_node: exp.Expression) -> bool:
        """Check if any direct argument of the function is a Column reference."""
        for arg in func_node.iter_expressions():
            if any(isinstance(node, exp.Column) for node in arg.walk()):
                return True
        return False

    def _add_finding(self, findings: List[Finding], func_node: exp.Expression,
                     file_path: str, func_name: str, query_sql: str = None,
                     seen_locations: set = None):
        snippet = func_node.sql(dialect="sqlite")
        line, col = _get_node_line_col(func_node)

        if seen_locations is not None:
            location = (line, col, file_path)
            if location in seen_locations:
                return
            seen_locations.add(location)

        findings.append(Finding(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            file=file_path,
            line=line,
            column=col,
            snippet=snippet,
            message=f"Function {func_name.upper()}() wraps a column reference in a predicate. "
                    f"This prevents index usage (non-sargable). "
                    f"Consider rewriting to apply the function to the comparison value instead.",
            confidence=0.85,
            query=query_sql,
        ))


class UnnecessarySubqueryRule(BaseRule):
    """AP-05: Detects WHERE col IN (SELECT ...) on single, non-aggregated subqueries.
    
    These can typically be rewritten as JOINs for better performance.
    
    Negative controls:
    - EXISTS subqueries should NOT trigger (already using the better pattern)
    - Subqueries with aggregation (GROUP BY, HAVING, aggregate functions) should NOT trigger
    """
    rule_id = "AP-05"
    rule_name = "UNNECESSARY_SUBQUERY"

    def detect(self, ast: exp.Expression, file_path: str) -> List[Finding]:
        findings = []
        query_sql = ast.sql(dialect="sqlite")

        for in_node in ast.find_all(exp.In):
            # Check if the right side is a subquery (Select inside a Subquery)
            query_arg = in_node.args.get("query")
            if query_arg is None:
                continue

            # Find the actual select statement
            subquery_select = None
            if isinstance(query_arg, exp.Subquery):
                subquery_select = query_arg.find(exp.Select)
            elif isinstance(query_arg, exp.Select):
                subquery_select = query_arg

            if subquery_select is None:
                continue

            # Skip if the subquery uses aggregation — that's a valid use of IN
            if self._has_aggregation(subquery_select):
                continue

            # Skip if the subquery selects more than one column
            if len(subquery_select.expressions) != 1:
                continue

            snippet = in_node.sql(dialect="sqlite")
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."

            line, col = _get_node_line_col(in_node)

            findings.append(Finding(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                file=file_path,
                line=line,
                column=col,
                snippet=snippet,
                message="WHERE ... IN (SELECT ...) with a non-aggregated subquery. "
                        "Consider rewriting as a JOIN for better performance.",
                confidence=0.80,
                query=query_sql,
            ))

        return findings

    def _has_aggregation(self, select: exp.Select) -> bool:
        """Check if a SELECT uses aggregation (GROUP BY, HAVING, or aggregate functions)."""
        # Check for GROUP BY
        if select.args.get("group"):
            return True
        # Check for HAVING
        if select.args.get("having"):
            return True
        # Check for aggregate functions in projection
        aggregate_types = (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)
        for expr in select.expressions:
            if isinstance(expr, aggregate_types) or expr.find(*aggregate_types):
                return True
        return False


class CartesianJoinRule(BaseRule):
    """AP-03: Detects Cartesian Join hazards.
    
    Finds explicit CROSS JOINs or JOINs lacking ON/USING clauses.
    """
    rule_id = "AP-03"
    rule_name = "CARTESIAN_JOIN"

    def detect(self, ast: exp.Expression, file_path: str) -> List[Finding]:
        findings = []
        query_sql = ast.sql(dialect="sqlite")

        for join in ast.find_all(exp.Join):
            kind = (join.args.get("kind") or "").upper()
            method = (join.args.get("method") or "").upper()
            on_clause = join.args.get("on")
            using_clause = join.args.get("using")
            
            if kind == "CROSS" or (not on_clause and not using_clause and method != "NATURAL"):
                snippet = join.sql(dialect="sqlite")
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                    
                line, col = _get_node_line_col(join)
                findings.append(Finding(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    file=file_path,
                    line=line,
                    column=col,
                    snippet=snippet,
                    message="Cartesian join hazard detected (missing ON/USING clause or explicit CROSS JOIN). "
                            "This can cause exponential row explosion and severe performance degradation.",
                    confidence=0.90,
                    query=query_sql,
                ))

        return findings


# Registry of all rules — used by the parser to run all rules
ALL_RULES: List[BaseRule] = [
    SelectStarRule(),
    NonSargablePredicateRule(),
    UnnecessarySubqueryRule(),
    CartesianJoinRule(),
]
