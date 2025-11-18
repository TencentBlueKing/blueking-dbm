-- 测试 JSON 字段非法格式的 DDL 语句
-- 这些 SQL 包含语法错误的 JSON 字符串，应该被检测为无效
USE test_db;
-- 错误1: JSON 字段使用无效的 JSON 对象格式（缺少引号）
CREATE TABLE invalid_json_format_1 (
    id INT PRIMARY KEY,
    config JSON NOT NULL DEFAULT '' COMMENT '配置'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
-- 错误2: ALTER TABLE 添加 JSON 字段使用无效格式
ALTER TABLE users
ADD COLUMN user_config JSON NOT NULL DEFAULT 'null' COMMENT '用户配置';
-- 错误3: ALTER TABLE 添加 JSON 字段使用不完整格式
ALTER TABLE users
ADD COLUMN user_data JSON NOT NULL DEFAULT '' COMMENT '用户数据';