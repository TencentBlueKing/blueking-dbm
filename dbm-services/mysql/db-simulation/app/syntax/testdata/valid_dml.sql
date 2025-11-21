-- 测试正确的DML语句
USE test_db;
-- INSERT 语句
INSERT INTO users (username, email, phone, status)
VALUES (
        'testuser1',
        'test1@example.com',
        '13800138000',
        1
    );
INSERT INTO users (username, email, phone, status)
VALUES (
        'testuser2',
        'test2@example.com',
        '13800138001',
        1
    ),
    (
        'testuser3',
        'test3@example.com',
        '13800138002',
        1
    ),
    (
        'testuser4',
        'test4@example.com',
        '13800138003',
        0
    );
-- INSERT SELECT
INSERT INTO users (username, email, status)
SELECT CONCAT('user_', id),
    CONCAT('email_', id, '@test.com'),
    1
FROM users
WHERE id < 10;
-- UPDATE 语句 - 带WHERE条件
UPDATE users
SET status = 0,
    updated_at = NOW()
WHERE username = 'testuser1';
UPDATE users
SET email = CONCAT(username, '@newdomain.com')
WHERE status = 1
    AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
-- UPDATE 多表关联
UPDATE users u
    INNER JOIN orders o ON u.id = o.user_id
SET u.status = 2
WHERE o.order_status = 'completed'
    AND o.created_at > DATE_SUB(NOW(), INTERVAL 7 DAY);
-- DELETE 语句 - 带WHERE条件
DELETE FROM users
WHERE status = 0
    AND created_at < DATE_SUB(NOW(), INTERVAL 365 DAY);
DELETE FROM orders
WHERE order_status = 'cancelled'
    AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
LIMIT 1000;
-- SELECT 语句（虽然不是DML，但也测试一下）
SELECT *
FROM users
WHERE status = 1;
SELECT u.username,
    COUNT(o.order_id) as order_count,
    SUM(o.total_amount) as total_spent
FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
WHERE u.status = 1
GROUP BY u.id,
    u.username
HAVING order_count > 0
ORDER BY total_spent DESC
LIMIT 100;
-- REPLACE 语句
REPLACE INTO users (id, username, email, status)
VALUES (1, 'testuser1', 'newemail@example.com', 1);