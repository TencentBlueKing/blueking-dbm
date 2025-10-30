-- 测试语法错误的SQL语句

USE test_db;

-- 错误1: 关键字拼写错误
CREAT TABLE bad_table (
    id INT PRIMARY KEY
);

-- 错误2: 缺少必需的子句 (缺少列定义)
CREATE TABLE empty_table ();

-- 错误3: 括号不匹配
CREATE TABLE unmatched_paren (
    id INT,
    name VARCHAR(50
);

-- 错误4: 数据类型错误
CREATE TABLE wrong_type (
    id INTEGER,
    name VARCHARR(50)
);

-- 错误5: 缺少逗号分隔符
CREATE TABLE missing_comma (
    id INT
    name VARCHAR(50)
);

-- 错误6: 非法字符
CREATE TABLE illegal_char (
    id INT,
    name@ VARCHAR(50)
);

-- 错误7: ALTER TABLE 语法错误 - 缺少列名
ALTER TABLE users ADD COLUMN VARCHAR(50);

-- 错误8: UPDATE 语法错误 - 缺少SET
UPDATE users WHERE id = 1;

-- 错误9: SELECT 语法错误 - FROM 在 WHERE 之后
SELECT * WHERE id = 1 FROM users;

-- 错误10: INSERT 语法错误 - 列数和值数量不匹配会在运行时错误，但这里测试明显的语法错误
INSERT INTO users (username, email) VALUES ('test');

-- 错误11: 非法的表名（纯数字开头）
CREATE TABLE 123_table (
    id INT
);

-- 错误12: JOIN 语法错误
SELECT * FROM users INNER orders ON users.id = orders.user_id;

-- 错误13: 缺少 END
DELIMITER //
CREATE PROCEDURE bad_proc()
BEGIN
    SELECT 1;
//
DELIMITER ;

