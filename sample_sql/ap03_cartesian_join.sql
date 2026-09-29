-- AP-03: Cartesian Join Hazard (missing ON clause)
SELECT * 
FROM orders o
JOIN customers c;

-- AP-03: Explicit CROSS JOIN
SELECT a.id, b.id
FROM table_a a
CROSS JOIN table_b b;
