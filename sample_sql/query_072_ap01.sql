-- Auto-generated ap01 query
SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER(PARTITION BY o.customer_id ORDER BY o.order_date DESC) as rn FROM orders o JOIN order_items oi ON o.id = oi.order_id WHERE oi.quantity > 5) ranked_orders WHERE ranked_orders.rn = 1;
