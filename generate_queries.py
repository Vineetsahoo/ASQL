import os
import random

output_dir = r"c:\Users\vinee\Downloads\ASQL\sample_sql"

# Schemas available in the engine:
# orders: id, customer_id, order_date, total_amount, status
# customers: id, name, email, city, created_at
# products: id, name, price, category, stock_qty
# order_items: id, order_id, product_id, quantity, unit_price
# employees: id, name, department, salary, hire_date
# departments: id, name, budget, location
# invoices: id, order_id, invoice_date, amount, paid
# shipments: id, order_id, ship_date, carrier, tracking_no

# Complex Anti-pattern templates
templates_ap01 = [
    # AP-01 inside a CTE with multiple joins
    "WITH HighValueOrders AS (SELECT o.id, o.customer_id, o.total_amount FROM orders o WHERE o.total_amount > {amount}) SELECT * FROM HighValueOrders hvo LEFT JOIN customers c ON hvo.customer_id = c.id WHERE c.city = '{city}';",
    
    # AP-01 with window functions and deep nesting
    "SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER(PARTITION BY o.customer_id ORDER BY o.order_date DESC) as rn FROM orders o JOIN order_items oi ON o.id = oi.order_id WHERE oi.quantity > {qty}) ranked_orders WHERE ranked_orders.rn = 1;",
    
    # AP-01 with UNION and subqueries
    "SELECT * FROM employees WHERE department = '{dept}' UNION ALL SELECT * FROM employees WHERE salary > {salary} AND id IN (SELECT id FROM departments);",
]

templates_ap02 = [
    # AP-02 deeply nested functions in predicates
    "SELECT c.id, c.name FROM customers c JOIN orders o ON c.id = o.customer_id WHERE UPPER(TRIM(SUBSTR(c.name, 1, 5))) = '{name}' AND o.status = '{status}';",
    
    # AP-02 inside a having clause with complex math
    "SELECT department, SUM(salary) as total_salary FROM employees GROUP BY department HAVING SUM(salary) > {amount} AND YEAR(MAX(hire_date)) = {year};",
    
    # AP-02 in multiple OR conditions with COALESCE and nested queries
    "WITH DeptStats AS (SELECT department, count(*) as emp_count FROM employees GROUP BY department) SELECT e.name, d.emp_count FROM employees e JOIN DeptStats d ON e.department = d.department WHERE COALESCE(e.salary, 0) < {amount} OR UPPER(e.name) LIKE '%{name}%';",
    
    # AP-02 in JOIN condition
    "SELECT o.id, c.name FROM orders o INNER JOIN customers c ON UPPER(o.status) = UPPER(c.city) WHERE o.total_amount > {amount};"
]

templates_ap03 = [
    # AP-03 implicit cartesian join mixed with valid joins
    "SELECT o.id, c.name, p.name FROM orders o JOIN customers c ON o.customer_id = c.id, products p WHERE o.total_amount > {amount};",
    
    # AP-03 explicit CROSS JOIN in a CTE
    "WITH Matrix AS (SELECT c.id as cid, p.id as pid FROM customers c CROSS JOIN products p) SELECT m.*, o.total_amount FROM Matrix m LEFT JOIN orders o ON o.customer_id = m.cid AND o.total_amount > {amount};",
    
    # AP-03 missing ON clause disguised with other complex filters
    "SELECT e.name, d.name, d.location FROM employees e INNER JOIN departments d WHERE e.salary > {salary} AND d.budget > {amount};"
]

templates_ap05 = [
    # AP-05 nested subqueries with multiple layers
    "SELECT c.name, c.email FROM customers c WHERE c.id IN (SELECT o.customer_id FROM orders o WHERE o.id IN (SELECT oi.order_id FROM order_items oi WHERE oi.product_id IN (SELECT p.id FROM products p WHERE p.category = '{category}')));",
    
    # AP-05 inside a CTE joined with another table
    "WITH TargetCustomers AS (SELECT id, name FROM customers WHERE city = '{city}') SELECT tc.name FROM TargetCustomers tc WHERE tc.id IN (SELECT customer_id FROM orders WHERE total_amount > {amount});",
    
    # AP-05 with complex correlated logic (though AP-05 looks for non-aggregated subqueries generally)
    "SELECT p.name, p.price FROM products p WHERE p.category = '{category}' AND p.id IN (SELECT product_id FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE o.status = '{status}');"
]

# Valid complex query templates
templates_valid = [
    # Complex valid query with Window functions, CTEs, and explicit columns
    "WITH RankedOrders AS (SELECT id, customer_id, total_amount, ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY total_amount DESC) as rnk FROM orders WHERE status = '{status}') SELECT c.name, ro.total_amount FROM RankedOrders ro JOIN customers c ON ro.customer_id = c.id WHERE ro.rnk = 1;",
    
    # Valid aggregated EXISTS query
    "SELECT d.name, d.budget FROM departments d WHERE EXISTS (SELECT 1 FROM employees e WHERE e.department = d.id GROUP BY e.department HAVING AVG(e.salary) > {salary});",
    
    # Complex multi-join with aggregations
    "SELECT c.city, SUM(oi.quantity * oi.unit_price) as total_revenue FROM customers c INNER JOIN orders o ON c.id = o.customer_id INNER JOIN order_items oi ON o.id = oi.order_id WHERE o.order_date >= '2023-01-01' GROUP BY c.city HAVING SUM(oi.quantity * oi.unit_price) > {amount} ORDER BY total_revenue DESC LIMIT 5;"
]

values = {
    'status': ['pending', 'shipped', 'delivered', 'cancelled'],
    'city': ['Boston', 'New York', 'Seattle', 'Austin'],
    'category': ['Electronics', 'Books', 'Clothing', 'Home'],
    'dept': ['Engineering', 'Sales', 'HR', 'Marketing'],
    'name': ['JOHN', 'ALICE', 'BOB', 'SMITH'],
    'prefix': ['1Z9', 'TRK', 'SHP'],
    'carrier': ['FedEx', 'UPS', 'USPS', 'DHL'],
    'year': [2022, 2023, 2024],
    'amount': [50, 100, 500, 1000, 5000],
    'salary': [50000, 75000, 100000],
    'qty': [1, 5, 10, 50]
}

def generate_query(template):
    return template.format(
        status=random.choice(values['status']),
        city=random.choice(values['city']),
        category=random.choice(values['category']),
        dept=random.choice(values['dept']),
        name=random.choice(values['name']),
        prefix=random.choice(values['prefix']),
        carrier=random.choice(values['carrier']),
        year=random.choice(values['year']),
        amount=random.choice(values['amount']),
        salary=random.choice(values['salary']),
        qty=random.choice(values['qty'])
    )

categories = [
    ('ap01', templates_ap01),
    ('ap02', templates_ap02),
    ('ap03', templates_ap03),
    ('ap05', templates_ap05),
    ('valid', templates_valid)
]

for i in range(1, 76):
    cat_name, cat_templates = random.choice(categories)
    template = random.choice(cat_templates)
    query = generate_query(template)
    
    filename = f"query_{i:03d}_{cat_name}.sql"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        if cat_name == 'ap01':
            f.write(f"-- Auto-generated {cat_name} query\n")
        f.write(query + "\n")

print(f"Successfully generated 75 queries in {output_dir}")
