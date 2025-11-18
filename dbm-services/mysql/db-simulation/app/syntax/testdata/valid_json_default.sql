-- 测试 JSON 字段有效默认值的 DDL 语句
-- 这些 SQL 应该被语法检查器标记为有效
USE test_db;
-- 有效1: JSON 字段使用 DEFAULT '[]'（空数组，有效）
CREATE TABLE valid_json_table_1 (
    id INT PRIMARY KEY,
    game_types JSON NOT NULL,
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
-- 有效2: JSON 字段使用 DEFAULT NULL（空值，有效）
CREATE TABLE valid_json_table_2 (
    id INT PRIMARY KEY,
    game_types JSON DEFAULT NULL,
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
-- 有效3: JSON 字段使用 DEFAULT '{}'（空对象，有效） 8.0 有效
CREATE TABLE valid_json_table_3 (
    id INT PRIMARY KEY,
    game_types JSON NOT NULL DEFAULT '{}',
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;