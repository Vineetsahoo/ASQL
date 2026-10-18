"""Auto-rewrite module: Alternative SQL solutions for anti-patterns.

Implements deterministic AST rewrites using sqlglot for:
- AP-01: SELECT * → explicit projection columns
- AP-02: Non-sargable functions → SARGable range/collation conditions
- AP-03: Cartesian joins → explicit INNER JOIN with ON conditions
- AP-04: Leading wildcards → indexed prefix searches
- AP-05: IN (SELECT ...) subqueries → correlated EXISTS semi-joins
- AP-06: UNION → UNION ALL (deduplication sort elimination)
"""

from functools import lru_cache
from typing import Optional, Dict, List, Tuple
import sqlglot
from sqlglot import expressions as exp


# Hardcoded schema map for the sample corpus.
# Maps table_name (lowercase) -> list of column names.
SCHEMA_MAP: Dict[str, List[str]] = {
    "orders": ["id", "customer_id", "order_date", "total_amount", "status"],
    "customers": ["id", "name", "email", "city", "created_at"],
    "products": ["id", "name", "price", "category", "stock_qty"],
    "order_items": ["id", "order_id", "product_id", "quantity", "unit_price"],
    "employees": ["id", "name", "department", "salary", "hire_date"],
    "departments": ["id", "name", "budget", "location"],
    "invoices": ["id", "order_id", "invoice_date", "amount", "paid"],
    "shipments": ["id", "order_id", "ship_date", "carrier", "tracking_no"],
}

# Known foreign key relationship pairs: (table_a, table_b) -> (left_col, right_col)
RELATIONSHIPS: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("orders", "customers"): ("orders.customer_id", "customers.id"),
    ("customers", "orders"): ("orders.customer_id", "customers.id"),
    ("order_items", "orders"): ("order_items.order_id", "orders.id"),
    ("orders", "order_items"): ("order_items.order_id", "orders.id"),
    ("order_items", "products"): ("order_items.product_id", "products.id"),
    ("products", "order_items"): ("order_items.product_id", "products.id"),
    ("employees", "departments"): ("employees.department", "departments.name"),
    ("departments", "employees"): ("employees.department", "departments.name"),
    ("invoices", "orders"): ("invoices.order_id", "orders.id"),
    ("orders", "invoices"): ("invoices.order_id", "orders.id"),
    ("shipments", "orders"): ("shipments.order_id", "orders.id"),
    ("orders", "shipments"): ("shipments.order_id", "orders.id"),
}


@lru_cache(maxsize=1024)
def rewrite_select_star(sql: str) -> Optional[str]:
    """Attempt to rewrite SELECT * to explicit column list.
    
    Uses the hardcoded SCHEMA_MAP to resolve table columns.
    Returns None if rewrite is not possible (unknown tables, complex queries).
    """
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    for select in ast.find_all(exp.Select):
        stars = [e for e in select.expressions if isinstance(e, exp.Star) or (isinstance(e, exp.Column) and isinstance(e.this, exp.Star))]
        if not stars:
            continue

        table_aliases = _extract_table_aliases(select)

        new_expressions = []
        for expr in select.expressions:
            if isinstance(expr, exp.Star):
                columns = _expand_star(table_aliases)
                if columns:
                    new_expressions.extend(columns)
                    modified = True
                else:
                    new_expressions.append(expr)
            elif isinstance(expr, exp.Column) and isinstance(expr.this, exp.Star):
                table_alias = expr.table
                table_name = table_aliases.get(table_alias, table_alias).lower()
                if table_name in SCHEMA_MAP:
                    for col_name in SCHEMA_MAP[table_name]:
                        col = exp.Column(
                            this=exp.to_identifier(col_name),
                            table=exp.to_identifier(table_alias) if table_alias else None,
                        )
                        new_expressions.append(col)
                    modified = True
                else:
                    new_expressions.append(expr)
            else:
                new_expressions.append(expr)

        if modified:
            select.set("expressions", new_expressions)

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


@lru_cache(maxsize=1024)
def rewrite_non_sargable(sql: str) -> Optional[str]:
    """Attempt to rewrite non-sargable functions in predicates into SARGable equivalents."""
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    # 1. YEAR(col) = YYYY -> col >= 'YYYY-01-01' AND col < 'YYYY+1-01-01'
    for eq in list(ast.find_all(exp.EQ)):
        left = eq.this
        right = eq.expression
        if isinstance(left, exp.Func):
            func_name = getattr(left, "name", None) or type(left).__name__.lower()
            if isinstance(func_name, str) and func_name.lower() == "year":
                if isinstance(right, exp.Literal) and right.this.isdigit():
                    yr = int(right.this)
                    col = left.this if hasattr(left, "this") else None
                    if col:
                        col_sql = col.sql()
                        new_pred = sqlglot.parse_one(
                            f"{col_sql} >= '{yr}-01-01' AND {col_sql} < '{yr + 1}-01-01'"
                        )
                        eq.replace(new_pred)
                        modified = True
                        continue

            # UPPER(col) = 'val' or LOWER(col) = 'val' or TRIM(col) = 'val'
            if isinstance(func_name, str) and func_name.lower() in ("upper", "lower", "trim", "ltrim", "rtrim"):
                col = left.this if hasattr(left, "this") else None
                if col and isinstance(right, exp.Literal):
                    col_sql = col.sql()
                    val_sql = right.sql()
                    new_pred = sqlglot.parse_one(f"{col_sql} = {val_sql} COLLATE NOCASE")
                    eq.replace(new_pred)
                    modified = True
                    continue

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


@lru_cache(maxsize=1024)
def rewrite_cartesian_join(sql: str) -> Optional[str]:
    """Attempt to rewrite CROSS JOIN or joins missing ON into explicit INNER JOIN with keys."""
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    for join in ast.find_all(exp.Join):
        kind = (join.args.get("kind") or "").upper()
        on_clause = join.args.get("on")
        using_clause = join.args.get("using")
        method = (join.args.get("method") or "").upper()

        if kind == "CROSS" or (not on_clause and not using_clause and method != "NATURAL"):
            right_table = join.this
            rname = right_table.name.lower() if isinstance(right_table, exp.Table) else str(right_table).lower()
            
            sel = join.find_ancestor(exp.Select)
            left_table = sel.find(exp.Table) if sel else None
            lname = left_table.name.lower() if (left_table and hasattr(left_table, "name")) else "table_a"

            pair = (lname, rname)
            if pair in RELATIONSHIPS:
                c1, c2 = RELATIONSHIPS[pair]
                join.set("kind", "INNER")
                join.set("on", sqlglot.parse_one(f"{c1} = {c2}"))
                modified = True
            else:
                join.set("kind", "INNER")
                join.set("on", sqlglot.parse_one(f"{lname}.id = {rname}.{lname}_id"))
                modified = True

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


@lru_cache(maxsize=1024)
def rewrite_leading_wildcard(sql: str) -> Optional[str]:
    """Attempt to rewrite leading wildcard LIKE predicates into prefix searches."""
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    for like_node in ast.find_all(exp.Like, exp.ILike):
        expr = like_node.args.get("expression")
        if isinstance(expr, exp.Literal) and expr.args.get("is_string"):
            val = expr.this
            if val.startswith("%") or val.startswith("_"):
                prefix_val = val.lstrip("%_")
                if not prefix_val.endswith("%"):
                    prefix_val += "%"
                like_node.set("expression", exp.Literal.string(prefix_val))
                modified = True

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


@lru_cache(maxsize=1024)
def rewrite_unnecessary_subquery(sql: str) -> Optional[str]:
    """Attempt to rewrite WHERE col IN (SELECT ...) into an EXISTS (...) semi-join."""
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    for in_node in list(ast.find_all(exp.In)):
        left_col = in_node.this
        query_arg = in_node.args.get("query")
        if query_arg is None:
            continue

        subquery = query_arg.this if isinstance(query_arg, exp.Subquery) else query_arg
        if isinstance(subquery, exp.Select):
            sub = subquery.copy()
            if len(sub.expressions) == 1:
                sub_col = sub.expressions[0]
                sub.set("expressions", [exp.Literal.number(1)])
                corr = exp.EQ(this=sub_col.copy(), expression=left_col.copy())
                sub.where(corr, copy=False)
                in_node.replace(exp.Exists(this=sub))
                modified = True

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


@lru_cache(maxsize=1024)
def rewrite_union_without_all(sql: str) -> Optional[str]:
    """Attempt to rewrite UNION into UNION ALL."""
    try:
        statements = sqlglot.parse(sql)
    except Exception:
        return None

    if not statements or statements[0] is None:
        return None

    ast = statements[0]
    modified = False

    for union in ast.find_all(exp.Union):
        if union.args.get("distinct", False):
            union.set("distinct", False)
            modified = True

    if modified:
        return ast.sql(dialect="sqlite", pretty=True)
    return None


def rewrite_sql_by_rule(sql: str, rule_id: str) -> Optional[str]:
    """Unified dispatcher to rewrite a query based on rule_id."""
    if not sql:
        return None

    if rule_id == "AP-01":
        return rewrite_select_star(sql)
    elif rule_id == "AP-02":
        return rewrite_non_sargable(sql)
    elif rule_id == "AP-03":
        return rewrite_cartesian_join(sql)
    elif rule_id == "AP-04":
        return rewrite_leading_wildcard(sql)
    elif rule_id == "AP-05":
        return rewrite_unnecessary_subquery(sql)
    elif rule_id == "AP-06":
        return rewrite_union_without_all(sql)
    return None


def _extract_table_aliases(ast: exp.Expression) -> Dict[str, str]:
    """Extract alias->table_name mapping from FROM and JOIN clauses."""
    aliases = {}
    for table in ast.find_all(exp.Table):
        parent = table.parent
        while parent is not None and not isinstance(parent, exp.Select):
            parent = parent.parent
        if parent is not ast:
            continue
        table_name = table.name
        alias = table.alias
        if alias:
            aliases[alias] = table_name
        else:
            aliases[table_name] = table_name
    return aliases


def _expand_star(table_aliases: Dict[str, str]) -> List[exp.Expression]:
    """Expand * into explicit column references for all known tables."""
    columns = []
    for alias, table_name in table_aliases.items():
        tname = table_name.lower()
        if tname not in SCHEMA_MAP:
            return []  # Can't fully resolve — abort
        for col_name in SCHEMA_MAP[tname]:
            prefix = alias if len(table_aliases) > 1 else None
            col = exp.Column(
                this=exp.to_identifier(col_name),
                table=exp.to_identifier(prefix) if prefix else None,
            )
            columns.append(col)
    return columns
