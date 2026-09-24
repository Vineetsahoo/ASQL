-- AP-02 Positive: YEAR() wrapping a column in WHERE
SELECT id, order_date, total_amount
FROM orders
WHERE YEAR(order_date) = 2024;
