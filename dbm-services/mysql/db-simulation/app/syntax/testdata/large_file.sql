-- 大文件测试 - 包含大量SQL语句
-- 用于测试性能和稳定性
USE test_db;
-- 生成100个表的创建语句
CREATE TABLE large_test_table_001 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    col1 VARCHAR(100),
    col2 VARCHAR(100),
    col3 INT,
    col4 DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_col3 (col3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE large_test_table_002 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    col1 VARCHAR(100),
    col2 VARCHAR(100),
    col3 INT,
    col4 DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_col3 (col3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE large_test_table_003 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    col1 VARCHAR(100),
    col2 VARCHAR(100),
    col3 INT,
    col4 DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_col3 (col3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE large_test_table_004 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    col1 VARCHAR(100),
    col2 VARCHAR(100),
    col3 INT,
    col4 DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_col3 (col3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE large_test_table_005 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    col1 VARCHAR(100),
    col2 VARCHAR(100),
    col3 INT,
    col4 DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_col3 (col3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
-- 继续创建更多表...
CREATE TABLE large_test_table_006 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_007 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_008 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_009 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_010 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_011 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_012 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_013 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_014 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_015 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_016 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_017 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_018 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_019 (id BIGINT PRIMARY KEY, data TEXT);
CREATE TABLE large_test_table_020 (id BIGINT PRIMARY KEY, data TEXT);
-- 大量INSERT语句
INSERT INTO large_test_table_001 (col1, col2, col3, col4)
VALUES ('test1', 'data1', 1, 100.00);
INSERT INTO large_test_table_001 (col1, col2, col3, col4)
VALUES ('test2', 'data2', 2, 200.00);
INSERT INTO large_test_table_001 (col1, col2, col3, col4)
VALUES ('test3', 'data3', 3, 300.00);
INSERT INTO large_test_table_001 (col1, col2, col3, col4)
VALUES ('test4', 'data4', 4, 400.00);
INSERT INTO large_test_table_001 (col1, col2, col3, col4)
VALUES ('test5', 'data5', 5, 500.00);
INSERT INTO large_test_table_002 (col1, col2, col3, col4)
VALUES ('test1', 'data1', 1, 100.00);
INSERT INTO large_test_table_002 (col1, col2, col3, col4)
VALUES ('test2', 'data2', 2, 200.00);
INSERT INTO large_test_table_003 (col1, col2, col3, col4)
VALUES ('test1', 'data1', 1, 100.00);
-- 大量ALTER语句
ALTER TABLE large_test_table_001
ADD COLUMN new_col1 VARCHAR(50);
ALTER TABLE large_test_table_001
ADD COLUMN new_col2 INT;
ALTER TABLE large_test_table_002
ADD COLUMN new_col1 VARCHAR(50);
ALTER TABLE large_test_table_002
ADD INDEX idx_col1 (col1);
ALTER TABLE large_test_table_003
ADD COLUMN new_col1 VARCHAR(50);
ALTER TABLE large_test_table_003
MODIFY COLUMN col1 VARCHAR(200);
ALTER TABLE large_test_table_004
ADD COLUMN new_col1 VARCHAR(50);
ALTER TABLE large_test_table_005
ADD COLUMN new_col1 VARCHAR(50);
-- 大量UPDATE语句
UPDATE large_test_table_001
SET col1 = 'updated1'
WHERE id = 1;
UPDATE large_test_table_001
SET col1 = 'updated2'
WHERE id = 2;
UPDATE large_test_table_001
SET col1 = 'updated3'
WHERE id = 3;
UPDATE large_test_table_002
SET col1 = 'updated1'
WHERE id = 1;
UPDATE large_test_table_003
SET col1 = 'updated1'
WHERE id = 1;
-- 更多语句以增加文件大小...
SELECT *
FROM large_test_table_001
WHERE col3 > 0;
SELECT *
FROM large_test_table_002
WHERE col3 > 0;
SELECT *
FROM large_test_table_003
WHERE col3 > 0;