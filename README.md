# SQL Anti-Pattern Detection Tool (MVP)

> **Core Objective (PRD v3):** Give the tool a folder of SQL files. It parses them into an AST, flags real anti-patterns with file and line numbers, and shows the results on the console and in structured report files (`findings.json` and `report.html`).

---

## 1. What Has Been Built

This project is a **Deterministic Abstract Syntax Tree (AST) Static Code Analysis Engine** (similar to ESLint, Pylint, or SonarQube for SQL). It does not require training data or a machine learning model; instead, it uses grammar-level parsing via `sqlglot` to achieve 100% precision with zero hallucinations.

### Architecture & Components

![Deterministic SQL Analysis Engine Architecture](Deterministic%20SQL%20Analysis%20Engine%20Architecture.png)

```
                ┌────────────────────────────────┐
                │        SQL Files (*.sql)       │
                └───────────────┬────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ 1. Parser Engine (engine/parser.py)                        │
  │    • Reads files, parses to AST using sqlglot              │
  │    • Graceful error isolation (skips malformed files)      │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ 2. Rule Detection Engine (engine/rules.py)                 │
  │    • AP-01 (SELECT_STAR): Flags SELECT *                   │
  │    • AP-02 (NON_SARGABLE_PREDICATE): Flags wrapped columns │
   │    • AP-03 (CARTESIAN_JOIN): Flags joins without ON/USING │
  │    • AP-05 (UNNECESSARY_SUBQUERY): Flags IN (SELECT ...)   │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ 3. Enrichment Phase                                        │
  │    • Rewriter (engine/rewriter.py): Safe SELECT * expansion│
  │    • Cost Proxy (engine/cost_proxy.py): SQLite EXPLAIN     │
  └─────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ 4. Output & Reporting (scan.py & engine/report.py)         │
  │    • Terminal Table: Formatted summary of all findings     │
  │    • findings.json: Schema-validated JSON output           │
  │    • report.html: Interactive visual HTML dashboard        │
  └────────────────────────────────────────────────────────────┘
```

### Entity-Relationship (E-R) Schema

![E-R Diagram](E-R%20Diagram.png)

### Key Modules

| Module | Path | Purpose |
|---|---|---|
| **Data Models** | `engine/models.py` | Defines `Finding` dataclass matching PRD v3 §4 schema. |
| **Parser** | `engine/parser.py` | AST parsing, multi-file traversal, error isolation. |
| **Rules Engine** | `engine/rules.py` | Detectors for **AP-01**, **AP-02**, **AP-03**, and **AP-05**. |
| **Rewriter** | `engine/rewriter.py` | AST-based query rewriter (expands `SELECT *`). |
| **Cost Proxy** | `engine/cost_proxy.py` | In-memory SQLite `EXPLAIN QUERY PLAN` runner. |
| **Report Generator** | `engine/report.py` | Static HTML dashboard builder with modern dark UI. |
| **CLI Runner** | `scan.py` | Command-line interface tying the pipeline together. |
| **Test Suite** | `tests/` | 48 comprehensive unit & integration tests. |
| **Sample Corpus** | `sample_sql/` | 18 SQL test fixtures (positive & negative controls). |

---

## 2. Implemented Anti-Pattern Rules

| Rule ID | Name | What it Catches | Negative Controls (What it Ignores) |
|---|---|---|---|
| **AP-01** | `SELECT_STAR` | Unbounded `SELECT *` in query projections | `COUNT(*)` and aggregate functions are ignored |
| **AP-02** | `NON_SARGABLE_PREDICATE` | Function calls wrapping column references in `WHERE`/`ON` (e.g., `UPPER(name)`, `YEAR(order_date)`) | Functions wrapping literal values (e.g., `WHERE name = UPPER('john')`) are ignored |
| **AP-03** | `CARTESIAN_JOIN` | Explicit `CROSS JOIN` and joins without `ON`/`USING` clauses | `NATURAL JOIN` and joins with an explicit join condition are ignored |
| **AP-05** | `UNNECESSARY_SUBQUERY` | `WHERE col IN (SELECT ...)` on single-table, unaggregated queries | `EXISTS` subqueries and queries using `GROUP BY`/`HAVING`/aggregates are ignored |

---

## 3. How to Run and Verify on Your Own

### Prerequisites
Make sure dependencies are installed:
```powershell
pip install -r requirements.txt
```

---

### Step 1: Run the Automated Test Suite
Run the full unit and integration test suite:
```powershell
python -m pytest -v
```
**Expected result:** All **48 tests pass** (`48 passed in ~1.6s`). This verifies:
- Error recovery on malformed/empty files.
- Accurate detection for all 4 rules.
- Negative controls (no false positives on `COUNT(*)` or literal wraps).
- Correct query rewriting for `SELECT *`.
- SQLite cost plan proxy evaluation.

---

### Step 2: Run the CLI Scanner on the Sample Corpus
Scan the 18 provided sample SQL files:
```powershell
python scan.py sample_sql/ --out findings.json --html report.html
```

**Expected console output:**
1. File-by-file progress with finding counts.
2. A non-fatal warning for `sample_sql\edge_malformed.sql` (demonstrating graceful error isolation).
3. A formatted console table listing all 15 detected anti-patterns:
   - 5 findings for **AP-01**
   - 4 findings for **AP-02**
   - 2 findings for **AP-03**
   - 4 findings for **AP-05**
4. Generation notices for `findings.json` and `report.html`.

---

### Step 3: Inspect the HTML Report in Your Browser
Open the generated visual dashboard:
```powershell
Start-Process report.html
```
*(Or double-click `report.html` in your file explorer.)*

**What to look for:**
- **Badges:** Color-coded rule badges (`AP-01` Red, `AP-02` Orange, `AP-05` Purple).
- **Cost Signals:** `FULL_SCAN_DETECTED` badges showing table scan risks.
- **Rewrites:** The **Suggested Rewrite** column showing `SELECT *` expanded into explicit column names based on the table schema.

---

### Step 4: Verify with Your Own Custom SQL Query

You can test how the tool analyzes brand-new SQL code:

1. Create a test file, e.g. `my_test.sql`:
   ```sql
   -- Test query with non-sargable predicate
   SELECT id, name FROM customers WHERE UPPER(city) = 'NEW YORK';
   ```

2. Create a folder `custom_test/` and place `my_test.sql` inside.
3. Run the scan:
   ```powershell
   python scan.py custom_test/ --out custom_findings.json --html custom_report.html
   ```
4. Confirm that the tool flags `AP-02 (NON_SARGABLE_PREDICATE)` on line 2 and warns about `UPPER(city)`.

---

## 4. Verification Checklist Against PRD v3

| PRD Success Criteria (§8) | Verified? | Notes |
|---|:---:|---|
| **1. Zero unhandled crashes** | ✅ | Scanner handles all exceptions and exits with code `0`. |
| **2. Correct positive & negative firing** | ✅ | `COUNT(*)` and literal wraps trigger 0 false positives. |
| **3. Validated JSON schema** | ✅ | `findings.json` adheres to all 10 required PRD fields. |
| **4. Visual HTML report** | ✅ | `report.html` renders a readable, responsive dark UI. |
| **5. Working auto-rewrite** | ✅ | `SELECT *` is rewritten to explicit column lists. |
| **6. Error isolation** | ✅ | `edge_malformed.sql` produces a warning without stopping the scan. |
