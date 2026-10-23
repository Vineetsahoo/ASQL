# Test Coverage

## Current Baseline

The test suite currently contains 48 tests and passes with:

```powershell
python -m pytest -q
```

Latest measured result: **88% line coverage for `engine/`**, with 48 tests passing. The CLI integration tests execute `scan.py` in a subprocess, so its child-process lines are not included in this report.

## Generate Coverage

Install the declared dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the suite with a terminal report showing uncovered lines:

```powershell
python -m pytest --cov=engine --cov-report=term-missing -q
```

Generate an HTML report:

```powershell
python -m pytest --cov=engine --cov-report=html -q
Start-Process htmlcov/index.html
```

The generated `htmlcov/` directory is local build output and should not be committed.

## Covered Areas

| Area | Tests |
|---|---|
| SQL parsing and directory scanning | `tests/test_parser.py` |
| AP-01, AP-02, AP-03, and AP-05 detection | `tests/test_rules.py` |
| `SELECT *` rewriting and nested scope handling | `tests/test_rewriter.py` |
| SQLite cost-proxy signals and cache cleanup | `tests/test_cost_proxy.py` |
| Static HTML report generation | `tests/test_report.py` |
| End-to-end CLI output and error handling | `tests/test_integration.py` |

## Important Regression Cases

The suite includes coverage for:

- malformed SQL alongside valid statements in the same file
- empty and comments-only files
- negative controls such as `COUNT(*)`, literal-wrapped functions, `EXISTS`, and aggregate subqueries
- nested query table scoping during rewrites
- indexed, unindexed, invalid, and unknown-table cost-proxy queries
- cost-proxy cache invalidation during cleanup

## Remaining Coverage Gaps

- no measured minimum coverage threshold is enforced in CI
- no concurrency coverage for the process-global SQLite connection
- no property-based testing for arbitrary SQL input
- no benchmark coverage for large SQL directories or very large queries
