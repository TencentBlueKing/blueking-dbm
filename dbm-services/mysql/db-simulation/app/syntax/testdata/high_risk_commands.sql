-- 测试高危命令

USE test_db;

-- DROP TABLE - 高危
DROP TABLE IF EXISTS old_table;

-- DROP DATABASE - 高危
DROP DATABASE IF EXISTS old_database;

-- RENAME TABLE - 高危
RENAME TABLE users TO users_backup;

-- DROP INDEX - 高危
DROP INDEX idx_email ON users;

-- LOCK TABLES - 高危
LOCK TABLES users WRITE, orders READ;
-- 操作
UNLOCK TABLES;

-- ANALYZE TABLE - 高危
ANALYZE TABLE users;

-- ANALYZE 多个表
ANALYZE TABLE users, orders, products;

-- OPTIMIZE TABLE - 高危
OPTIMIZE TABLE users;

-- ALTER TABLESPACE - 高危
ALTER TABLESPACE ts1 ADD DATAFILE 'file.ibd';

-- DROP VIEW - 高危
DROP VIEW IF EXISTS active_users;

-- DROP PROCEDURE - 高危
DROP PROCEDURE IF EXISTS GetUserOrders;

-- DROP FUNCTION - 高危
DROP FUNCTION IF EXISTS CalculateDiscount;

-- DROP TRIGGER - 高危
DROP TRIGGER IF EXISTS before_user_insert;

-- DROP EVENT - 高危
DROP EVENT IF EXISTS cleanup_old_orders;

-- DROP SERVER - 高危
DROP SERVER IF EXISTS remote_server;

-- 组合：先创建再删除（都应该被检测到）
CREATE TABLE temp_table (id INT);
DROP TABLE temp_table;

