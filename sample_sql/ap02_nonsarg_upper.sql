-- AP-02 Positive: UPPER() wrapping a column in WHERE
SELECT id, name, email
FROM customers
WHERE UPPER(name) = 'JOHN DOE';
