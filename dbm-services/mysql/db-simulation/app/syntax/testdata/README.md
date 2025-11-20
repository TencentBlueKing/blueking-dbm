# SQL语法检查测试数据

本目录包含用于测试 `TmysqlParseFile.Do()` 方法的SQL测试文件。

## 测试文件说明

### 正确语法的SQL文件

1. **valid_ddl.sql** - DDL语句测试
   - CREATE DATABASE
   - CREATE TABLE (包含主键、索引、外键)
   - ALTER TABLE (添加列、修改列、添加索引)

2. **valid_dml.sql** - DML语句测试
   - INSERT (单行、多行、INSERT SELECT)
   - UPDATE (单表、多表关联)
   - DELETE (带WHERE条件)
   - REPLACE

3. **valid_advanced.sql** - 高级功能测试
   - CREATE PROCEDURE (存储过程)
   - CREATE FUNCTION (自定义函数)
   - CREATE TRIGGER (触发器)
   - CREATE VIEW (视图)
   - CREATE EVENT (事件调度器)

### 错误语法的SQL文件

4. **invalid_syntax.sql** - 语法错误测试
   - 关键字拼写错误
   - 缺少必需的子句
   - 括号不匹配
   - 数据类型错误
   - 非法字符

### 高危和禁用命令测试

5. **high_risk_commands.sql** - 高危命令
   - DROP TABLE/DATABASE
   - RENAME TABLE
   - DROP INDEX
   - LOCK TABLES
   - ANALYZE TABLE
   - OPTIMIZE TABLE

6. **banned_commands.sql** - 禁用命令
   - GRANT/REVOKE
   - CREATE USER/DROP USER
   - KILL
   - RESET
   - SHUTDOWN

### 特殊场景测试

7. **spider_create_table.sql** - Spider特定测试
   - ENGINE=SPIDER 表定义
   - 分片键配置
   - PARTITION 分区表

8. **use_db_conflict.sql** - USE DATABASE冲突检测
   - 包含 USE database 语句
   - 用于测试多数据库执行场景下的冲突检测

9. **empty_file.sql** - 空文件测试
   - 仅包含注释的空SQL文件

10. **large_file.sql** - 大文件测试
    - 包含大量SQL语句
    - 用于性能和稳定性测试

## 运行测试

### 前置条件

1. **tmysqlparse 二进制文件**：需要在 `/tmysqlparse` 路径存在 tmysqlparse 工具
2. **规则配置文件**：需要 `rule.yaml` 和 `spider_rule.yaml` 文件

### 运行所有测试

```bash
# 完整集成测试 (需要 tmysqlparse)
go test -v ./app/syntax/...

# 仅运行单元测试 (跳过需要 tmysqlparse 的测试)
go test -v -short ./app/syntax/...

# 运行特定测试
go test -v ./app/syntax/... -run TestTmysqlParseFile_Do_ValidDDL

# 运行表驱动测试
go test -v ./app/syntax/... -run TestTmysqlParseFile_Do_TableDriven
```

### 测试覆盖率

```bash
go test -v -cover ./app/syntax/...
go test -coverprofile=coverage.out ./app/syntax/...
go tool cover -html=coverage.out
```

## 测试结构

测试使用以下模式：

1. **setupTestEnv()** - 初始化测试环境
   - 检查 tmysqlparse 是否存在
   - 创建临时工作目录
   - 返回清理函数

2. **copyTestFile()** - 复制测试文件到工作目录

3. **各个测试函数** - 针对不同场景的测试
   - 基础功能测试
   - 规则检测测试
   - 多版本测试
   - 高级功能测试
   - 边界测试

## 测试预期结果

### 正确的SQL
- `SyntaxFailInfos` 应为空
- 可能有 `RiskWarnings` (高危命令)
- 可能有 `BanWarnings` (禁用命令)

### 语法错误的SQL
- `SyntaxFailInfos` 应包含错误信息
- 每个错误包含行号、错误码和错误消息

### 高危命令
- `RiskWarnings` 应包含检测到的高危命令

### 禁用命令
- `BanWarnings` 应包含检测到的禁用命令

## 添加新的测试用例

1. 在 `testdata/` 目录下创建新的 SQL 文件
2. 在 `syntax_test.go` 中添加相应的测试函数
3. 使用 `setupTestEnv()` 和 `copyTestFile()` 辅助函数
4. 验证测试结果

## 注意事项

1. 测试需要 tmysqlparse 二进制文件支持
2. 使用 `-short` 标志可以跳过集成测试
3. 规则配置在包初始化时自动加载
4. 测试会创建临时目录并在测试后自动清理

