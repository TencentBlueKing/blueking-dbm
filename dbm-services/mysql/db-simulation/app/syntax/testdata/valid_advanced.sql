-- 测试高级功能：存储过程、函数、触发器、视图、事件

USE test_db;

-- 创建存储过程
DELIMITER //
CREATE PROCEDURE GetUserOrders(IN userId INT)
BEGIN
    SELECT o.order_id, o.order_no, o.total_amount, o.order_status
    FROM orders o
    WHERE o.user_id = userId
    ORDER BY o.created_at DESC;
END//
DELIMITER ;

-- 创建带输出参数的存储过程
DELIMITER //
CREATE PROCEDURE GetUserStats(IN userId INT, OUT orderCount INT, OUT totalAmount DECIMAL(10,2))
BEGIN
    SELECT COUNT(*), IFNULL(SUM(total_amount), 0)
    INTO orderCount, totalAmount
    FROM orders
    WHERE user_id = userId;
END//
DELIMITER ;

-- 创建函数
DELIMITER //
CREATE FUNCTION CalculateDiscount(amount DECIMAL(10,2)) 
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    DECLARE discount DECIMAL(10,2);
    IF amount > 1000 THEN
        SET discount = amount * 0.1;
    ELSEIF amount > 500 THEN
        SET discount = amount * 0.05;
    ELSE
        SET discount = 0;
    END IF;
    RETURN discount;
END//
DELIMITER ;

-- 创建触发器 - BEFORE INSERT
DELIMITER //
CREATE TRIGGER before_user_insert 
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF NEW.username IS NULL OR NEW.username = '' THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Username cannot be empty';
    END IF;
END//
DELIMITER ;

-- 创建触发器 - AFTER UPDATE
DELIMITER //
CREATE TRIGGER after_order_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.order_status != NEW.order_status THEN
        INSERT INTO order_status_log (order_id, old_status, new_status, changed_at)
        VALUES (NEW.order_id, OLD.order_status, NEW.order_status, NOW());
    END IF;
END//
DELIMITER ;

-- 创建视图
CREATE VIEW active_users AS
SELECT id, username, email, phone, created_at
FROM users
WHERE status = 1;

-- 创建带JOIN的视图
CREATE VIEW user_order_summary AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    COUNT(o.order_id) as total_orders,
    IFNULL(SUM(o.total_amount), 0) as total_amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.status = 1
GROUP BY u.id, u.username, u.email;

-- 创建事件
CREATE EVENT IF NOT EXISTS cleanup_old_orders
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
DELETE FROM orders 
WHERE order_status = 'cancelled' 
AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
LIMIT 1000;

-- 创建另一个事件 - 每小时执行
CREATE EVENT IF NOT EXISTS update_user_stats
ON SCHEDULE EVERY 1 HOUR
STARTS CURRENT_TIMESTAMP
DO
UPDATE user_statistics us
INNER JOIN (
    SELECT user_id, COUNT(*) as cnt, SUM(total_amount) as amt
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY user_id
) o ON us.user_id = o.user_id
SET us.order_count = o.cnt, us.total_spent = o.amt;

