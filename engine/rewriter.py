"""Auto-rewrite module: SELECT * → explicit column list.

Uses a hardcoded schema map (no real DB introspection) per PRD v2 §3.
Only AP-01 rewrite is implemented for the MVP.
"""

from functools import lru_cache
from typing import Optional, Dict, List
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
        stars = [e for e in select.expressions if isinstance(e, exp.Star)]
        if not stars:
            continue

        # Build alias->table mapping from FROM and JOINs
        table_aliases = _extract_table_aliases(select)

        # Determine which tables to expand
        new_expressions = []
        for expr in select.expressions:
            if isinstance(expr, exp.Star):
                # Expand * using all tables in FROM/JOIN
                columns = _expand_star(table_aliases)
                if columns:
                    new_expressions.extend(columns)
                    modified = True
                else:
                    # Can't resolve — keep original
                    new_expressions.append(expr)
            elif isinstance(expr, exp.Column) and isinstance(expr.this, exp.Star):
                # table.* pattern
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
