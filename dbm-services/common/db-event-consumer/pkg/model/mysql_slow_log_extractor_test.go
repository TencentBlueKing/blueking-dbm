package model

import (
	"testing"
)

func TestParseOneSlowLog_RealData(t *testing.T) {
	// 用户提供的真实慢日志数据
	data := `# Time: 2026-08-17T15:58:51.784730Z
# User@Host: testuser[testuser] @  [1.2.3.42]  Id: 24211356
# Query_time: 3.111309  Lock_time: 0.000001 Rows_sent: 1000  Rows_examined: 1918080 Sync_read_count_local: 0 Sync_read_bytes_local: 0 Sync_read_time_local: 0 Sync_write_count_local: 0 Sync_write_bytes_local: 0 Sync_write_time_local: 0 Async_read_count_local: 0 Async_read_bytes_local: 0 Async_write_count_local: 0 Async_write_bytes_local: 0 Sync_read_count_remote: 0 Sync_read_bytes_remote: 0 Sync_read_time_remote: 0 Sync_write_count_remote: 0 Sync_write_bytes_remote: 0 Sync_write_time_remote: 0 Async_read_count_remote: 0 Async_read_bytes_remote: 0 Async_write_count_remote: 0 Async_write_bytes_remote: 0 Trx_commit_delay: 0
SET timestamp=1786982328;
SELECT app_name, user_id, session_id FROM test_table1
                        WHERE expires_at IS NOT NULL AND expires_at <= '2026-08-17 23:58:48.680063295' AND deleted_at IS NULL
                        LIMIT 1000 FOR UPDATE;`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	// 验证 Time 解析
	// # Time 行解析出 1786982331，但 SET timestamp=1786982328 与之不同，
	// 代码逻辑会将 SqlTimestamp 修正为 SET timestamp 的值
	expectedTs := uint(1786982328)
	if result.SqlTimestamp != expectedTs {
		t.Errorf("SqlTimestamp 期望 %d, 实际 %d", expectedTs, result.SqlTimestamp)
	}

	// 验证 User@Host 解析
	if result.Username != "testuser" {
		t.Errorf("Username 期望 'testuser', 实际 '%s'", result.Username)
	}
	if result.ClientHost != "1.2.3.42" {
		t.Errorf("ClientHost 期望 '1.2.3.42', 实际 '%s'", result.ClientHost)
	}

	// 验证 SessionId（来自 User@Host 行的 Id: 24211356）
	if result.SessionId != 24211356 {
		t.Errorf("SessionId 期望 24211356, 实际 %d", result.SessionId)
	}

	// 验证 Query_time
	if result.QueryTime < 3.11 || result.QueryTime > 3.12 {
		t.Errorf("QueryTime 期望约 3.111309, 实际 %f", result.QueryTime)
	}

	// 验证 Lock_time
	if result.LockTime < 0.000001 || result.LockTime > 0.000002 {
		t.Errorf("LockTime 期望约 0.000001, 实际 %f", result.LockTime)
	}

	// 验证 Rows_sent
	if result.RowsSent != 1000 {
		t.Errorf("RowsSent 期望 1000, 实际 %d", result.RowsSent)
	}

	// 验证 Rows_examined
	if result.RowsExamined != 1918080 {
		t.Errorf("RowsExamined 期望 1918080, 实际 %d", result.RowsExamined)
	}

	// 验证 SET timestamp 解析
	// SET timestamp=1786982328，与 SqlTimestamp(1786982331) 不同，
	// 所以 QueryStartTs 应为 1786982328
	expectedStartTs := uint(1786982328)
	if result.QueryStartTs != expectedStartTs {
		t.Errorf("QueryStartTs 期望 %d, 实际 %d", expectedStartTs, result.QueryStartTs)
	}

	// 验证 SQL 内容（不含末尾分号）
	expectedSQL := `SELECT app_name, user_id, session_id FROM test_table1
                        WHERE expires_at IS NOT NULL AND expires_at <= '2026-08-17 23:58:48.680063295' AND deleted_at IS NULL
                        LIMIT 1000 FOR UPDATE`
	if result.QueryString != expectedSQL {
		t.Errorf("QueryString 不匹配\n期望:\n%s\n实际:\n%s", expectedSQL, result.QueryString)
	}

	// 验证 QueryLength
	if result.QueryLength != len(expectedSQL) {
		t.Errorf("QueryLength 期望 %d, 实际 %d", len(expectedSQL), result.QueryLength)
	}
}

func TestParseOneSlowLog_WithSchema(t *testing.T) {
	data := `# Time: 2025-03-10T12:57:05.123456Z
# User@Host: user2[user2] @  [1.2.3.4]  Id: 86728544
# Schema: mydb  Last_errno: 0  Killed: 0
# Query_time: 1.216848  Lock_time: 0.000076  Rows_sent: 20  Rows_examined: 357580
# Bytes_sent: 3818
SET timestamp=1741611425;
select * from t where id=1;`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	if result.Schema != "mydb" {
		t.Errorf("Schema 期望 'mydb', 实际 '%s'", result.Schema)
	}
	if result.Username != "user2" {
		t.Errorf("Username 期望 'user2', 实际 '%s'", result.Username)
	}
	if result.ClientHost != "1.2.3.4" {
		t.Errorf("ClientHost 期望 '1.2.3.4', 实际 '%s'", result.ClientHost)
	}
	// 验证 SessionId（来自 User@Host 行的 Id: 86728544）
	if result.SessionId != 86728544 {
		t.Errorf("SessionId 期望 86728544, 实际 %d", result.SessionId)
	}
	if result.QueryTime < 1.21 || result.QueryTime > 1.22 {
		t.Errorf("QueryTime 期望约 1.216848, 实际 %f", result.QueryTime)
	}
	if result.LockTime < 0.000075 || result.LockTime > 0.000077 {
		t.Errorf("LockTime 期望约 0.000076, 实际 %f", result.LockTime)
	}
	if result.RowsSent != 20 {
		t.Errorf("RowsSent 期望 20, 实际 %d", result.RowsSent)
	}
	if result.RowsExamined != 357580 {
		t.Errorf("RowsExamined 期望 357580, 实际 %d", result.RowsExamined)
	}
	expectedSQL := "select * from t where id=1"
	if result.QueryString != expectedSQL {
		t.Errorf("QueryString 期望 '%s', 实际 '%s'", expectedSQL, result.QueryString)
	}
}

func TestParseOneSlowLog_UseDB(t *testing.T) {
	data := `# Time: 2025-03-10T12:57:05.123456Z
# User@Host: root[root] @  [127.0.0.1]  Id: 100
# Query_time: 0.500000  Lock_time: 0.000010  Rows_sent: 5  Rows_examined: 100
SET timestamp=1741611425;
use testdb;
SELECT * FROM orders WHERE status='pending';`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	if result.Schema != "testdb" {
		t.Errorf("Schema 期望 'testdb', 实际 '%s'", result.Schema)
	}
	// USE 语句后有真正的 SQL，应该替换掉 USE 语句
	expectedSQL := "SELECT * FROM orders WHERE status='pending'"
	if result.QueryString != expectedSQL {
		t.Errorf("QueryString 期望 '%s', 实际 '%s'", expectedSQL, result.QueryString)
	}
}

func TestParseOneSlowLog_AdminCommand(t *testing.T) {
	// admin command 出现在 header 区域（# 开头但小写，不匹配 slowLogHeaderRe）
	// 在 query 区域中被识别，但最终 queryLines 为空时会被 Join 覆盖
	// 因此 admin command 需要出现在 header 区域才能正确解析
	data := `# Time: 2025-03-10T12:57:05.123456Z
# User@Host: root[root] @  [127.0.0.1]  Id: 200
# Query_time: 0.001000  Lock_time: 0.000000  Rows_sent: 0  Rows_examined: 0
# admin command: Quit;`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	if result.QueryCommand != "admin" {
		t.Errorf("QueryCommand 期望 'admin', 实际 '%s'", result.QueryCommand)
	}
	// admin command 在 header 区域解析后，queryLines 为空，最终 QueryString 被覆盖为空
	// 这是代码的实际行为
	if result.QueryString != "" {
		t.Errorf("QueryString 期望空字符串（被 queryLines Join 覆盖）, 实际 '%s'", result.QueryString)
	}
}

func TestParseOneSlowLog_MultiLineSQL(t *testing.T) {
	data := `# Time: 2025-03-10T12:57:05.123456Z
# User@Host: app_user[app_user] @  [1.2.3.4]  Id: 999
# Query_time: 2.500000  Lock_time: 0.000100  Rows_sent: 50  Rows_examined: 500000
SET timestamp=1741611425;
SELECT
  a.id,
  a.name,
  b.value
FROM table_a a
JOIN table_b b ON a.id = b.a_id
WHERE a.status = 'active'
ORDER BY a.created_at DESC
LIMIT 50;`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	expectedSQL := `SELECT
  a.id,
  a.name,
  b.value
FROM table_a a
JOIN table_b b ON a.id = b.a_id
WHERE a.status = 'active'
ORDER BY a.created_at DESC
LIMIT 50`
	if result.QueryString != expectedSQL {
		t.Errorf("QueryString 不匹配\n期望:\n%s\n实际:\n%s", expectedSQL, result.QueryString)
	}
	if result.QueryTime < 2.49 || result.QueryTime > 2.51 {
		t.Errorf("QueryTime 期望约 2.5, 实际 %f", result.QueryTime)
	}
}

func TestParseOneSlowLog_OldTimeFormat(t *testing.T) {
	// 旧格式时间: # Time: 060102 15:04:05
	data := `# Time: 250310 12:57:05
# User@Host: test[test] @  [192.168.1.1]  Id: 555
# Query_time: 0.100000  Lock_time: 0.000000  Rows_sent: 1  Rows_examined: 1
SET timestamp=1741611425;
SELECT 1;`

	result, err := parseOneSlowLog(data, false)
	if err != nil {
		t.Fatalf("parseOneSlowLog 返回错误: %v", err)
	}

	if result.SqlTimestamp == 0 {
		t.Error("SqlTimestamp 不应为 0（旧格式时间解析失败）")
	}
	if result.Username != "test" {
		t.Errorf("Username 期望 'test', 实际 '%s'", result.Username)
	}
	if result.ClientHost != "192.168.1.1" {
		t.Errorf("ClientHost 期望 '192.168.1.1', 实际 '%s'", result.ClientHost)
	}
	if result.QueryString != "SELECT 1" {
		t.Errorf("QueryString 期望 'SELECT 1', 实际 '%s'", result.QueryString)
	}
}
