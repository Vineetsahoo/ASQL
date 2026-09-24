-- AP-02 Positive: SUBSTRING/TRIM wrapping column in WHERE
SELECT id, name, email
FROM customers
WHERE TRIM(email) = 'test@example.com';
