-- Auto-generated ap05 query
SELECT name FROM products WHERE id IN (SELECT product_id FROM order_items WHERE quantity > 50);
