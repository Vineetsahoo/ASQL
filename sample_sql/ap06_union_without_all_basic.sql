-- Anti-Pattern AP-06: UNION without ALL
-- Triggers implicit sort and row deduplication
SELECT id, name, department FROM employees WHERE department = 'Engineering'
UNION
SELECT id, name, department FROM employees WHERE department = 'Product';
