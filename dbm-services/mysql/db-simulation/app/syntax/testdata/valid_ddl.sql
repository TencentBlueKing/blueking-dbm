-- 测试正确的DDL语句

-- 创建数据库
CREATE DATABASE IF NOT EXISTS test_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- 使用数据库
USE test_db;

-- 创建表 - 包含主键、索引、外键
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status TINYINT DEFAULT 1,
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 创建订单表
CREATE TABLE orders (
    order_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_no VARCHAR(32) NOT NULL UNIQUE,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    order_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id),
    KEY idx_order_no (order_no),
    KEY idx_created_at (created_at),
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- ALTER TABLE 添加列
ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT NULL AFTER email;

-- ALTER TABLE 修改列
ALTER TABLE users MODIFY COLUMN username VARCHAR(100) NOT NULL;

-- ALTER TABLE 添加索引
ALTER TABLE users ADD INDEX idx_phone (phone);

-- ALTER TABLE 添加唯一索引
ALTER TABLE users ADD UNIQUE KEY uk_phone (phone);

-- ALTER TABLE 删除索引
ALTER TABLE users DROP INDEX idx_phone;

-- 创建带复合索引的表
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category_status (category_id, status),
    INDEX idx_price (price),
    FULLTEXT KEY ft_product_name (product_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

