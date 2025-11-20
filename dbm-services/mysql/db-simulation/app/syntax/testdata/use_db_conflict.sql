-- 测试 USE DATABASE 冲突检测
-- 当用户在表单中输入了多个数据库作为变更对象时，SQL文件中不应该使用 USE 语句
-- 因为这可能导致SQL在错误的数据库上执行
-- 切换到数据库1
USE database1;
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50)
);
INSERT INTO users
VALUES (1, 'user1');
-- 切换到数据库2 - 这在多数据库执行场景下是危险的
USE database2;
CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100)
);
INSERT INTO products
VALUES (1, 'product1');
-- 再次切换
USE database3;
UPDATE users
SET username = 'updated_user'
WHERE id = 1;