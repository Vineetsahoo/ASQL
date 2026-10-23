-- Auto-generated valid query
WITH RankedOrders AS (SELECT id, customer_id, total_amount, ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY total_amount DESC) as rnk FROM orders WHERE status = 'pending') SELECT c.name, ro.total_amount FROM RankedOrders ro JOIN customers c ON ro.customer_id = c.id WHERE ro.rnk = 1;
