-- AP-02 Negative Control: Function wrapping a LITERAL, not a column
-- This should NOT trigger AP-02
SELECT id, name, salary
FROM employees
WHERE salary > ROUND(50000.555, 2);

-- Also: function in SELECT projection (not in WHERE) should not trigger
SELECT id, UPPER(name) as upper_name
FROM customers
WHERE city = 'Boston';
