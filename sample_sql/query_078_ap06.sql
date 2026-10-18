-- Query 078: Demonstrating AP-06 UNION without ALL with predicates
SELECT user_id, email, signup_date FROM web_users WHERE signup_date >= '2026-01-01'
UNION
SELECT user_id, email, signup_date FROM mobile_users WHERE signup_date >= '2026-01-01';
