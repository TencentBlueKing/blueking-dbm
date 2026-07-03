package reportslowlog

import (
	"bufio"
	"bytes"
	"flag"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ==================== parseTimeToTimestamp 测试 ====================

func TestParseTimeToTimestamp_RFC3339Nano(t *testing.T) {
	// 格式2: RFC3339Nano 带时区
	ts, err := parseTimeToTimestamp("2026-01-27T01:58:55.960323+08:00")
	if err != nil {
		t.Fatalf("解析 RFC3339Nano 带时区失败: %v", err)
	}
	// 2026-01-27T01:58:55+08:00 的 Unix 时间戳
	if ts != 1769450335 {
		t.Errorf("期望 1769450335, 实际 %d", ts)
	}
}

func TestParseTimeToTimestamp_RFC3339NanoUTC(t *testing.T) {
	// 格式3: RFC3339Nano UTC
	ts, err := parseTimeToTimestamp("2026-01-24T19:03:14.039913Z")
	if err != nil {
		t.Fatalf("解析 RFC3339Nano UTC 失败: %v", err)
	}
	// 2026-01-24T19:03:14Z 的 Unix 时间戳
	if ts != 1769281394 {
		t.Errorf("期望 1769281394, 实际 %d", ts)
	}
}

func TestParseTimeToTimestamp_OldFormat(t *testing.T) {
	// 格式1: "260127  2:05:24" (YYMMDD + 多个空格 + H:MM:SS)
	ts, err := parseTimeToTimestamp("260127  2:05:24")
	if err != nil {
		t.Fatalf("解析旧格式失败: %v", err)
	}
	// 只验证解析成功且时间戳合理（2026年范围内）
	if ts < 1769400000 || ts > 1769500000 {
		t.Errorf("时间戳 %d 不在预期范围内", ts)
	}
}

func TestParseTimeToTimestamp_InvalidFormat(t *testing.T) {
	_, err := parseTimeToTimestamp("invalid-time-string")
	if err == nil {
		t.Fatal("期望解析失败，但成功了")
	}
}

// ==================== collectSegFields 测试 ====================

func TestCollectSegFields_SchemaPattern(t *testing.T) {
	r := &SlowlogReport{}
	lines := [][]byte{
		[]byte("# Time: 2026-01-27T01:58:55.960323+08:00"),
		[]byte("# User@Host: root[root] @ localhost []  Id:     5"),
		[]byte("# Schema: testdb  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 1.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 0"),
	}

	f := r.collectSegFields(lines)
	if f.schema != "testdb" {
		t.Errorf("期望 Schema='testdb', 实际 '%s'", f.schema)
	}
}

func TestCollectSegFields_NoSchema(t *testing.T) {
	r := &SlowlogReport{}
	lines := [][]byte{
		[]byte("# Query_time: 1.000000  Lock_time: 0.000000"),
		[]byte("SET timestamp=1769450335;"),
		[]byte("SELECT 1;"),
	}

	f := r.collectSegFields(lines)
	if f.schema != "" {
		t.Errorf("不期望匹配到 Schema，但得到 '%s'", f.schema)
	}
}

// ==================== collectSegFields - usedDB 测试 ====================

func TestCatchUseDBBytes(t *testing.T) {
	r := &SlowlogReport{}
	tests := []struct {
		name     string
		lines    [][]byte
		expected string
	}{
		{
			name:     "普通 use db",
			lines:    [][]byte{[]byte("use mydb;")},
			expected: "mydb",
		},
		{
			name:     "带反引号的 use db",
			lines:    [][]byte{[]byte("use `my_database`;")},
			expected: "my_database",
		},
		{
			name:     "大写 USE",
			lines:    [][]byte{[]byte("USE production;")},
			expected: "production",
		},
		{
			name:     "无 use 语句",
			lines:    [][]byte{[]byte("SELECT 1;")},
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := r.collectSegFields(tt.lines)
			if f.usedDB != tt.expected {
				t.Errorf("期望 '%s', 实际 '%s'", tt.expected, f.usedDB)
			}
		})
	}
}

// ==================== collectSegFields - setTs 测试 ====================

func TestCatchSetTimestampBytes(t *testing.T) {
	r := &SlowlogReport{}
	tests := []struct {
		name      string
		lines     [][]byte
		wantFound bool
		wantTs    int64
	}{
		{
			name:      "正常 SET timestamp",
			lines:     [][]byte{[]byte("SET timestamp=1769450335;")},
			wantFound: true,
			wantTs:    1769450335,
		},
		{
			name:      "带空格的 SET timestamp",
			lines:     [][]byte{[]byte("SET timestamp = 1769450335 ;")},
			wantFound: true,
			wantTs:    1769450335,
		},
		{
			name:      "无 SET timestamp",
			lines:     [][]byte{[]byte("SELECT 1;")},
			wantFound: false,
			wantTs:    0,
		},
		{
			name: "多行中提取",
			lines: [][]byte{
				[]byte("# Query_time: 1.000000"),
				[]byte("SET timestamp=1700000000;"),
				[]byte("SELECT sleep(1);"),
			},
			wantFound: true,
			wantTs:    1700000000,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := r.collectSegFields(tt.lines)
			if f.hasSetTs != tt.wantFound {
				t.Errorf("found: 期望 %v, 实际 %v", tt.wantFound, f.hasSetTs)
			}
			if f.setTs != tt.wantTs {
				t.Errorf("ts: 期望 %d, 实际 %d", tt.wantTs, f.setTs)
			}
		})
	}
}

// ==================== collectSegFields - queryTime 测试 ====================

func TestCatchQueryTimeBytes(t *testing.T) {
	r := &SlowlogReport{}
	tests := []struct {
		name      string
		lines     [][]byte
		wantFound bool
		wantQt    float64
	}{
		{
			name:      "正常 Query_time",
			lines:     [][]byte{[]byte("# Query_time: 2.500000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 100")},
			wantFound: true,
			wantQt:    2.5,
		},
		{
			name:      "整数 Query_time",
			lines:     [][]byte{[]byte("# Query_time: 10.000000  Lock_time: 0.000000")},
			wantFound: true,
			wantQt:    10.0,
		},
		{
			name:      "无 Query_time",
			lines:     [][]byte{[]byte("# User@Host: root[root]")},
			wantFound: false,
			wantQt:    0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := r.collectSegFields(tt.lines)
			if f.hasQT != tt.wantFound {
				t.Errorf("found: 期望 %v, 实际 %v", tt.wantFound, f.hasQT)
			}
			if f.queryTime != tt.wantQt {
				t.Errorf("qt: 期望 %f, 实际 %f", tt.wantQt, f.queryTime)
			}
		})
	}
}

// ==================== collectSegFields - schema 测试 ====================

func TestGetSchemaFromSegBytes(t *testing.T) {
	r := &SlowlogReport{}

	// 有独立 Schema 行
	linesWithSchema := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []"),
		[]byte("# Schema: testdb  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 1.000000"),
	}
	f := r.collectSegFields(linesWithSchema)
	if f.schema != "testdb" {
		t.Errorf("期望从独立 Schema 行提取 'testdb', 实际 '%s'", f.schema)
	}

	// 无 Schema 行
	linesWithoutSchema := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []"),
		[]byte("# Query_time: 1.000000"),
		[]byte("SET timestamp=1700000000;"),
	}
	f = r.collectSegFields(linesWithoutSchema)
	if f.schema != "" {
		t.Errorf("期望无 Schema, 实际 '%s'", f.schema)
	}

	// 内联 Schema（在 Thread_id 行中）
	linesWithInlineSchema := [][]byte{
		[]byte("# User@Host: user2[user2] @  [1.1.1.1]"),
		[]byte("# Thread_id: 98343452  Schema: tesddb_631  QC_hit: No"),
		[]byte("# Query_time: 5.368769  Lock_time: 0.046386"),
	}
	f = r.collectSegFields(linesWithInlineSchema)
	if f.schema != "tesddb_631" {
		t.Errorf("期望从内联 Schema 提取 'tesddb_631', 实际 '%s'", f.schema)
	}
}

// ==================== buildSegLines 测试 ====================

func TestBuildSegLines(t *testing.T) {
	r := &SlowlogReport{}

	// 模拟往 segBuf 中追加数据
	r.segBuf = make([]byte, 0, 256)
	r.segRanges = nil

	lines := []string{"# Query_time: 1.0", "SET timestamp=100;", "SELECT 1;"}
	for _, l := range lines {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, []byte(l)...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(l)})
	}

	result := r.buildSegLines()
	if len(result) != 3 {
		t.Fatalf("期望 3 行, 实际 %d 行", len(result))
	}

	for i, l := range lines {
		if string(result[i]) != l {
			t.Errorf("第 %d 行: 期望 '%s', 实际 '%s'", i, l, string(result[i]))
		}
	}

	// 验证切片引用的是 segBuf 的底层数组（零拷贝）
	// 修改 segBuf 中的数据应该反映到 result 中
	r.segBuf[0] = 'X'
	if result[0][0] != 'X' {
		t.Error("buildSegLines 返回的切片应该引用 segBuf 的底层数组")
	}
}

// ==================== rewriteSegBytes 集成测试 ====================

func TestRewriteSegBytes_AddSchema(t *testing.T) {
	// 测试：当段中没有 Schema 行时，应在 Query_time 行前补充 Schema
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "mydb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-01-27T01:58:55.960323+08:00",
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
	}

	segLines := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []  Id:     5"),
		[]byte("# Query_time: 2.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 0"),
		[]byte("SET timestamp=1769450335;"),
		[]byte("SELECT sleep(2);"),
	}

	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	// 刷新并读取结果
	_ = r.writer.Flush()
	_ = f.Close()

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}

	output := string(content)

	// 验证输出包含 # Db_name: mydb  Query_start_ts: xxx（始终写入）
	if !strings.Contains(output, "# Db_name: mydb  Query_start_ts:") {
		t.Errorf("期望输出包含 '# Db_name: mydb  Query_start_ts:', 实际输出:\n%s", output)
	}

	// 验证 DB_name 行在注释块之后、SQL 之前
	dbNameIdx := strings.Index(output, "# Db_name: mydb")
	setTsIdx := strings.Index(output, "SET timestamp=")
	if dbNameIdx > setTsIdx {
		t.Error("DB_name 行应在 SET timestamp 之前")
	}
	// 验证 DB_name 行在 Query_time 之后（注释块最后一行之后）
	queryTimeIdx := strings.Index(output, "# Query_time:")
	if dbNameIdx < queryTimeIdx {
		t.Error("DB_name 行应在注释块最后一行之后")
	}
}

func TestRewriteSegBytes_WithExistingSchema(t *testing.T) {
	// 测试：当段中已有 Schema 行时，不应重复添加
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "mydb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-01-27T01:58:55.960323+08:00",
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
	}

	segLines := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []  Id:     5"),
		[]byte("# Schema: existingdb  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 2.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 0"),
		[]byte("SET timestamp=1769450335;"),
		[]byte("SELECT sleep(2);"),
	}

	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}

	output := string(content)

	// 验证输出包含 # Db_name: existingdb  Query_start_ts:（使用段内自带的 Schema）
	if !strings.Contains(output, "# Db_name: existingdb  Query_start_ts:") {
		t.Errorf("期望输出包含 '# Db_name: existingdb  Query_start_ts:', 实际输出:\n%s", output)
	}
}

func TestRewriteSegBytes_UseDBUpdatesCurrentDB(t *testing.T) {
	// 测试：use db 语句应更新 currentDB
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "olddb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
	}

	segLines := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []"),
		[]byte("# Query_time: 0.100000  Lock_time: 0.000000 Rows_sent: 0  Rows_examined: 0"),
		[]byte("use newdb;"),
	}

	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	// 验证 currentDB 已更新
	if r.currentDB != "newdb" {
		t.Errorf("期望 currentDB='newdb', 实际 '%s'", r.currentDB)
	}

	// 持久化状态到磁盘
	if err := r.persistState(); err != nil {
		t.Fatal(err)
	}

	// 验证持久化到磁盘
	content, err := os.ReadFile(dbRegFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "newdb" {
		t.Errorf("磁盘上期望 'newdb', 实际 '%s'", string(content))
	}
}

func TestRewriteSegBytes_QueryStartTs(t *testing.T) {
	// 测试：Query_start_ts = SET timestamp - Query_time
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	// commentHeadTime 与 SET timestamp 相同，说明 # Time 是当前记录的
	r := &SlowlogReport{
		currentDB:                  "testdb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-01-27T01:58:55.960323+08:00", // Unix: 1769450335
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
	}

	segLines := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []"),
		[]byte("# Schema: testdb  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 5.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 0"),
		[]byte("SET timestamp=1769450335;"),
		[]byte("SELECT sleep(5);"),
	}

	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}

	output := string(content)

	// DB_name testdb Query_start_ts: 1769450330 (= 1769450335 - 5)
	if !strings.Contains(output, "# Db_name: testdb  Query_start_ts: 1769450330") {
		t.Errorf("期望包含 '# Db_name: testdb  Query_start_ts: 1769450330', 实际输出:\n%s", output)
	}
}

func TestRewriteSegBytes_DifferentTimestamp(t *testing.T) {
	// 测试：commentHeadTime 与 SET timestamp 不同时的处理
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	// commentHeadTime 是之前记录的（不同于 SET timestamp）
	r := &SlowlogReport{
		currentDB:                  "testdb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-01-27T01:58:55.960323+08:00", // Unix: 1769450335
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
	}

	// SET timestamp 与 commentHeadTime 不同
	segLines := [][]byte{
		[]byte("# User@Host: root[root] @ localhost []"),
		[]byte("# Schema: testdb  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 3.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 0"),
		[]byte("SET timestamp=1769450400;"),
		[]byte("SELECT sleep(3);"),
	}

	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}

	output := string(content)

	// commentHeadTime(1769450335) != setTs(1769450400) → queryStartTs = setTs = 1769450400
	if !strings.Contains(output, "# Db_name: testdb  Query_start_ts: 1769450400") {
		t.Errorf("期望包含 '# Db_name: testdb  Query_start_ts: 1769450400', 实际输出:\n%s", output)
	}
}

// ==================== collectSegFields - timeStr 测试 ====================

func TestCatchCommentHeadTimeBytes(t *testing.T) {
	r := &SlowlogReport{}
	tests := []struct {
		name      string
		lines     [][]byte
		wantFound bool
		wantTime  string
	}{
		{
			name:      "RFC3339Nano 格式",
			lines:     [][]byte{[]byte("# Time: 2026-01-27T01:58:55.960323+08:00")},
			wantFound: true,
			wantTime:  "2026-01-27T01:58:55.960323+08:00",
		},
		{
			name:      "旧格式",
			lines:     [][]byte{[]byte("# Time: 260127  2:05:24")},
			wantFound: true,
			wantTime:  "260127  2:05:24",
		},
		{
			name:      "无 Time 行",
			lines:     [][]byte{[]byte("# Query_time: 1.0")},
			wantFound: false,
			wantTime:  "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := r.collectSegFields(tt.lines)
			if f.hasTime != tt.wantFound {
				t.Errorf("found: 期望 %v, 实际 %v", tt.wantFound, f.hasTime)
			}
			if f.timeStr != tt.wantTime {
				t.Errorf("time: 期望 '%s', 实际 '%s'", tt.wantTime, f.timeStr)
			}
		})
	}
}

// ==================== 完整段处理流程测试 ====================

func TestFullSegmentProcessing(t *testing.T) {
	// 模拟完整的段处理流程：从 scanner.Bytes() 到 rewriteSegBytes
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
		segBuf:                     make([]byte, 0, 64*1024),
	}

	// 模拟 scanner 读取的原始行数据
	rawLines := [][]byte{
		[]byte("# Time: 2026-01-27T01:58:55.960323+08:00"),
		[]byte("# User@Host: root[root] @ localhost []  Id:     5"),
		[]byte("# Query_time: 2.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 100"),
		[]byte("use testdb;"),
		[]byte("SET timestamp=1769450335;"),
		[]byte("SELECT * FROM users WHERE id = 1;"),
	}

	// 模拟追加到 segBuf
	for _, line := range rawLines {
		trimmed := bytes.TrimSpace(line)
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, trimmed...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(trimmed)})
	}

	// 构建 segLines 并处理
	segLines := r.buildSegLines()
	err = r.rewriteSegBytes(segLines)
	if err != nil {
		t.Fatalf("rewriteSegBytes 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}

	output := string(content)

	// 验证 currentDB 被更新
	if r.currentDB != "testdb" {
		t.Errorf("期望 currentDB='testdb', 实际 '%s'", r.currentDB)
	}

	// 验证 commentHeadTime 被更新
	if r.commentHeadTime != "2026-01-27T01:58:55.960323+08:00" {
		t.Errorf("期望 commentHeadTime 被更新")
	}

	// 验证输出包含 # Db_name: testdb  Query_start_ts:
	if !strings.Contains(output, "# Db_name: testdb  Query_start_ts:") {
		t.Errorf("期望输出包含 '# Db_name: testdb  Query_start_ts:', 实际输出:\n%s", output)
	}

	// 验证输出包含原始 SQL
	if !strings.Contains(output, "SELECT * FROM users WHERE id = 1;") {
		t.Error("期望输出包含原始 SQL")
	}
}

// ==================== 轮转逻辑测试 ====================

func TestRotateIfNeeded(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		logFilePath:  logFile,
		logFile:      f,
		writer:       bufio.NewWriterSize(f, 4096),
		writtenBytes: maxLogFileSize + 1, // 超过阈值
	}

	err = r.rotateIfNeeded()
	if err != nil {
		t.Fatalf("rotateIfNeeded 失败: %v", err)
	}

	// 验证轮转后 writtenBytes 重置
	if r.writtenBytes != 0 {
		t.Errorf("轮转后 writtenBytes 应为 0, 实际 %d", r.writtenBytes)
	}

	// 验证备份文件存在
	backupPath := logFile + ".1"
	if _, err := os.Stat(backupPath); os.IsNotExist(err) {
		t.Error("期望备份文件存在")
	}

	// 验证新文件可写
	_, err = r.writer.WriteString("test after rotate\n")
	if err != nil {
		t.Errorf("轮转后写入失败: %v", err)
	}

	// 清理
	_ = r.writer.Flush()
	_ = r.logFile.Close()
}

func TestRotateIfNeeded_NoRotate(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		logFilePath:  logFile,
		logFile:      f,
		writer:       bufio.NewWriterSize(f, 4096),
		writtenBytes: 1024, // 远小于阈值
	}

	err = r.rotateIfNeeded()
	if err != nil {
		t.Fatalf("rotateIfNeeded 失败: %v", err)
	}

	// 不应轮转
	if r.writtenBytes != 1024 {
		t.Errorf("不应轮转, writtenBytes 应保持 1024, 实际 %d", r.writtenBytes)
	}

	_ = f.Close()
}

// ==================== segBuf 复用验证 ====================

func TestSegBufReuse(t *testing.T) {
	r := &SlowlogReport{
		segBuf: make([]byte, 0, 64*1024),
	}

	// 第一段
	lines1 := []string{"line1_aaaa", "line2_bbbb"}
	for _, l := range lines1 {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, []byte(l)...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(l)})
	}

	// 记录底层数组指针
	bufPtr := &r.segBuf[:1][0]

	// 重置（模拟段结束）
	r.segRanges = r.segRanges[:0]
	r.segBuf = r.segBuf[:0]

	// 第二段
	lines2 := []string{"line3_cccc", "line4_dddd"}
	for _, l := range lines2 {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, []byte(l)...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(l)})
	}

	// 验证底层数组被复用（指针相同）
	newBufPtr := &r.segBuf[:1][0]
	if bufPtr != newBufPtr {
		t.Error("segBuf 底层数组应被复用，但发生了重新分配")
	}

	// 验证数据正确
	result := r.buildSegLines()
	if string(result[0]) != "line3_cccc" || string(result[1]) != "line4_dddd" {
		t.Errorf("数据不正确: %s, %s", string(result[0]), string(result[1]))
	}
}

// updateGolden 控制是否更新 golden 文件
var updateGolden = flag.Bool("update", false, "更新 golden 文件")

// ==================== 基于 slow-query-test.txt 样例文件的集成测试 ====================

func TestProcessSlowQueryTestFile(t *testing.T) {
	// 读取样例文件
	testDataPath := filepath.Join(".", "slow-query-test.txt")
	inputData, err := os.ReadFile(testDataPath)
	if err != nil {
		t.Fatalf("读取测试样例文件失败: %v", err)
	}

	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 256*1024),
		writtenBytes:               0,
		segBuf:                     make([]byte, 0, 64*1024),
		firstBodyLineIdx:           -1,
	}

	// 模拟 Run() 中的 scanner 逻辑（使用新的 parseLine + resetSeg + rewriteSeg API）
	scanner := bufio.NewScanner(bytes.NewReader(inputData))
	scanner.Buffer(make([]byte, 64*1024), 100*1024*1024)

	var segReady bool
	var inSegment bool
	for scanner.Scan() {
		rawLine := scanner.Bytes()
		line := bytes.TrimSpace(rawLine)

		// 段结束判断
		if segReady && isSegmentStartLine(line) {
			if err := r.rewriteSeg(); err != nil {
				t.Fatalf("rewriteSeg 失败: %v", err)
			}
			r.resetSeg()
			segReady = false
			inSegment = false
		}

		// 仅在段外跳过文件头信息行
		if !inSegment {
			if isSkippableSlowlogHeaderLine(line) || isBlankLine(line) {
				continue
			}
		}

		if isSegmentStartLine(line) {
			inSegment = true
		}

		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, rawLine...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(rawLine)})

		// 同步解析该行
		r.parseLine(line)

		// 记录第一个非 # 行的索引
		firstByte := firstNonSpaceByte(rawLine)
		if r.firstBodyLineIdx < 0 && firstByte != 0 && firstByte != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}

		if !isBlankLine(rawLine) {
			segReady = lineEndsWithSemicolon(rawLine)
		}
	}
	// 处理残留段（仅当 segReady 时）
	if len(r.segRanges) > 0 && segReady {
		if err := r.rewriteSeg(); err != nil {
			t.Fatalf("处理残留段失败: %v", err)
		}
	}

	// 持久化状态
	if err := r.persistState(); err != nil {
		t.Fatalf("persistState 失败: %v", err)
	}

	_ = r.writer.Flush()
	_ = f.Close()

	// 读取输出结果
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}
	output := string(content)

	// golden file 比较
	goldenPath := filepath.Join(".", "slow-query-test-rewrite.txt")
	if *updateGolden {
		// 更新 golden 文件
		err = os.WriteFile(goldenPath, content, 0644)
		if err != nil {
			t.Fatalf("更新 golden 文件失败: %v", err)
		}
		t.Logf("golden 文件已更新: %s", goldenPath)
	} else {
		// 与 golden 文件比较
		goldenData, err := os.ReadFile(goldenPath)
		if err == nil {
			if !bytes.Equal(content, goldenData) {
				// 输出前 500 字节的差异帮助定位
				t.Errorf("输出与 golden 文件不匹配。实际输出前500字节:\n%s", string(content[:min(500, len(content))]))
			}
		} else {
			t.Logf("golden 文件不存在，跳过比较（使用 -update 生成）: %v", err)
		}
	}

	t.Logf("=== 输出结果 ===\n%s", output)

	// ========== 分段说明 ==========
	// 修复后的分段逻辑：段结束不仅看分号，还要看下一行是否以 # 开头。
	// 因此 "use dbtest3;" 和 "use tesddb_639;" 不再导致段提前分割，
	// 所有 8 个慢查询段都是完整的，每个段都包含 # Query_time + SET timestamp。
	// 段1: RFC3339Nano+08:00, Schema已有, use dbtest3 → Query_start_ts = 1782921620 - 17 = 1782921603
	// 段2: RFC3339Nano+08:00, Schema已有 → Query_start_ts = 1782923058 - 256 = 1782922802
	// 段3: RFC3339Nano+08:00, Schema已有 → Query_start_ts = 1782923667 - 232 = 1782923435
	// 段4: UTC格式, 无Schema需补充 → Query_start_ts = 1782970740 - 1 = 1782970739
	// 段5: UTC格式, 无Schema需补充 → Query_start_ts = 1782970741 - 1 = 1782970740
	// 段6: UTC格式, 无Schema需补充 → Query_start_ts = 1782970742 - 1 = 1782970741
	// 段7: 旧格式时间, use tesddb_639 → Query_start_ts = 1782921305 - 5 = 1782921300
	// 段8: 旧格式时间, SQL中含 "# adfb;" 行（不应被误判为新段开头）
	//      → Query_start_ts = 1782977115 - 5 = 1782977110

	// ========== 验证段1: Query_start_ts 计算 ==========
	// Query_time: 17.501662, SET timestamp=1782921620
	// Query_start_ts = 1782921620 - int64(17.501662) = 1782921620 - 17 = 1782921603
	if !strings.Contains(output, "# Db_name: dbtest3  Query_start_ts: 1782921603  Session_id: 622265227") {
		t.Error("段1: 期望包含 '# Db_name: dbtest3  Query_start_ts: 1782921603  Session_id: 622265227'")
	}

	// ========== 验证段2: Query_start_ts 计算 ==========
	// Query_time: 256.054094, SET timestamp=1782923058
	// Query_start_ts = 1782923058 - int64(256.054094) = 1782923058 - 256 = 1782922802
	if !strings.Contains(output, "Query_start_ts: 1782922802") {
		t.Error("段2: 期望包含 'Query_start_ts: 1782922802'")
	}

	// ========== 验证段3: Query_start_ts 计算 ==========
	// Query_time: 232.440966, SET timestamp=1782923667
	// Query_start_ts = 1782923667 - 232 = 1782923435
	if !strings.Contains(output, "Query_start_ts: 1782923435") {
		t.Error("段3: 期望包含 'Query_start_ts: 1782923435'")
	}

	// ========== 验证段4(UTC格式): DB_name 补充 ==========
	// # Time: 2026-07-02T05:39:01.741743Z (无 Schema 行)
	// 应补充 DB_name dbtest3（从 use dbtest3 继承）
	utcSegIdx := strings.Index(output, "# Query_time: 1.168021")
	if utcSegIdx >= 0 {
		utcSegRegion := output[utcSegIdx:min(len(output), utcSegIdx+1200)]
		if !strings.Contains(utcSegRegion, "# Db_name: dbtest3  Query_start_ts:") {
			t.Errorf("段4(UTC格式): 期望包含 '# Db_name: dbtest3  Query_start_ts:', 实际区域:\n%s", utcSegRegion)
		}
	} else {
		t.Error("未找到 UTC 格式段 (Query_time: 1.168021)")
	}

	// ========== 验证段4: Query_start_ts 计算 ==========
	// Query_time: 1.168021, SET timestamp=1782970740
	// # Time: 2026-07-02T05:39:01.741743Z (UTC, ts=1782970741) != setTs(1782970740)
	// commentTs != setTs → queryStartTs = setTs = 1782970740
	if !strings.Contains(output, "Query_start_ts: 1782970740") {
		t.Error("段4: 期望包含 'Query_start_ts: 1782970740'")
	}

	// ========== 验证段7: Query_start_ts 计算 ==========
	// Query_time: 5.368769, SET timestamp=1782921305
	// Query_start_ts = 1782921305 - 5 = 1782921300
	if !strings.Contains(output, "Query_start_ts: 1782921300") {
		t.Error("段7: 期望包含 'Query_start_ts: 1782921300'")
	}

	// ========== 验证段8: SQL中含 # 开头行不被误判为新段 ==========
	// 段8 的 SQL: select sleep(10) from ... where master_server_id='
	//            # adfb;' or master_server_id!="";
	// "# adfb;" 行以 # 开头且以分号结尾，segReady=true，但下一行是 "# Time:" 才触发段分割
	// # Time: 260701 23:55:05 (ts=1782921305) != setTs(1782977115)
	// commentTs != setTs → queryStartTs = setTs = 1782977115
	if !strings.Contains(output, "# Db_name: tesddb_631  Query_start_ts: 1782977115  Session_id: 98343452") {
		t.Error("段8: 期望包含 '# Db_name: tesddb_631  Query_start_ts: 1782977115  Session_id: 98343452'")
	}
	// 段7和段8都有 Thread_id: 98343452，应各自在 DB_name 行中输出 Session_id
	sessionIdCount := strings.Count(output, "Session_id: 98343452")
	if sessionIdCount != 2 {
		t.Errorf("段7+段8: 期望 2 个 'Session_id: 98343452', 实际 %d 个", sessionIdCount)
	}
	// 验证段8的 SQL 内容完整（包含跨行的 SQL 和 # 开头的内容）
	if !strings.Contains(output, `master_server_id='`) {
		t.Error("段8: 期望输出包含 SQL 片段 master_server_id='")
	}
	if !strings.Contains(output, `# adfb;' or master_server_id!="";`) {
		t.Error("段8: 期望输出包含 SQL 中的 '# adfb;' 行（不应被截断）")
	}
	// 验证段8使用段内自带的 Schema: tesddb_631（在 Thread_id 行中）
	if !strings.Contains(output, "# Db_name: tesddb_631  Query_start_ts: 1782977115  Session_id: 98343452") {
		t.Error("段8: 期望包含 '# Db_name: tesddb_631  Query_start_ts: 1782977115  Session_id: 98343452'")
	}
	// 验证段8的 DB_name 行在 SET timestamp 之前（注释块末尾）
	seg8DbIdx := strings.Index(output, "# Db_name: tesddb_631  Query_start_ts: 1782977115  Session_id: 98343452")
	seg8SetTsIdx := strings.LastIndex(output, "SET timestamp=1782977115;")
	if seg8DbIdx > seg8SetTsIdx {
		t.Error("段8: DB_name 行应在 SET timestamp 之前")
	}

	// ========== 验证 use db 更新了 currentDB ==========
	// 段10 有 use infodba_schema，段12 也有 use infodba_schema
	if r.currentDB != "infodba_schema" {
		t.Errorf("期望最终 currentDB='infodba_schema', 实际 '%s'", r.currentDB)
	}

	// ========== 验证 commentHeadTime 被更新为最后一个 # Time 行 ==========
	// 段12 的 # Time 是 "2026-07-02T09:10:59.020164Z"
	if r.commentHeadTime != "2026-07-02T09:10:59.020164Z" {
		t.Errorf("期望最终 commentHeadTime='2026-07-02T09:10:59.020164Z', 实际 '%s'", r.commentHeadTime)
	}

	// ========== 验证 Query_start_ts 总数 ==========
	// 段1-12 各1个 = 12 个（手写 parser 能正确解析段12末尾有特殊字符的 SET timestamp）
	queryStartTsCount := strings.Count(output, "Query_start_ts:")
	if queryStartTsCount != 12 {
		t.Errorf("期望 12 个 Query_start_ts, 实际 %d 个", queryStartTsCount)
	}

	// ========== 验证 Session_id 总数（在 DB_name 同一行中） ==========
	// 段1-8 各1个 + 段6(Id:7532525) + 段12(Id:17661313) = 9 个（段9-11 没有 Id/Thread_id）
	sessionIdTotalCount := strings.Count(output, "Session_id:")
	if sessionIdTotalCount != 9 {
		t.Errorf("期望 9 个 Session_id, 实际 %d 个", sessionIdTotalCount)
	}

	// ========== 验证段9: 独立分段后有 Db_name 注入行 ==========
	// 段9 继承 currentDB="tesddb_639"（段7的use），commentTs==setTs，Query_start_ts=1782983348-2=1782983346
	if !strings.Contains(output, "# Db_name: tesddb_639  Query_start_ts: 1782983346") {
		t.Error("段9: 期望包含 '# Db_name: tesddb_639  Query_start_ts: 1782983346'")
	}

	// ========== 验证 Session_id 和 DB_name 在同一行 ==========
	if !strings.Contains(output, "# Db_name: dbtest3  Query_start_ts: 1782921603  Session_id: 622265227") {
		t.Error("Session_id 应和 DB_name 在同一行")
	}

	// ========== 验证 SQL 内容完整性 ==========
	if !strings.Contains(output, "select sleep(10);") {
		t.Error("期望输出包含 'select sleep(10);'")
	}
	if !strings.Contains(output, "order by FIELD(status,") {
		t.Error("期望输出包含多行 SQL 的 order by 部分")
	}

	// ========== 验证段1 已有 Schema 不重复添加 ==========
	// 段1 包含 "# Schema: dbtest3  Last_errno: 0"，不应额外添加 # Schema 行
	// 但会有一行 # Db_name: dbtest3  Query_start_ts: xxx
	seg1Start := strings.Index(output, "# User@Host: user3[user3] @  [1.2.3.4]  Id: 622265227")
	seg1End := strings.Index(output, "order by FIELD(status,")
	if seg1Start >= 0 && seg1End >= 0 {
		seg1 := output[seg1Start : seg1End+50]
		// 段内原有的 # Schema: dbtest3 保留
		if !strings.Contains(seg1, "# Schema: dbtest3") {
			t.Error("段1: 期望保留原有的 '# Schema: dbtest3'")
		}
	}

	// ========== 验证段1 的 use db 语句保留在段内 ==========
	if seg1End >= 0 {
		seg1Full := output[0:seg1End]
		if !strings.Contains(seg1Full, "use dbtest3;") {
			t.Error("段1: 期望 'use dbtest3;' 保留在段1内")
		}
	}

	// ========== 验证持久化文件 ==========
	dbContent, err := os.ReadFile(dbRegFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(dbContent) != "infodba_schema" {
		t.Errorf("磁盘 currentDB 期望 'infodba_schema', 实际 '%s'", string(dbContent))
	}

	timeContent, err := os.ReadFile(timeRegFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(timeContent) != "2026-07-02T09:10:59.020164Z" {
		t.Errorf("磁盘 commentHeadTime 期望 '2026-07-02T09:10:59.020164Z', 实际 '%s'", string(timeContent))
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ==================== ReformatSeg 测试 ====================

func TestReformatSeg_Basic(t *testing.T) {
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "mydb",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-07-02T00:00:20.581596+08:00",
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
		segBuf:                     make([]byte, 0, 64*1024),
		firstBodyLineIdx:           -1,
	}

	// 模拟段数据
	rawLines := [][]byte{
		[]byte("# Time: 2026-07-02T00:00:20.581596+08:00"),
		[]byte("# User@Host: user3[user3] @  [1.2.3.4]  Id: 622265227"),
		[]byte("# Schema: dbtest3  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 17.501662  Lock_time: 0.000423  Rows_sent: 12  Rows_examined: 49798517"),
		[]byte("use dbtest3;"),
		[]byte("SET timestamp=1782921620;"),
		[]byte("select * from users where id = 1;"),
	}

	for _, line := range rawLines {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, line...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(line)})
		r.parseLine(line)
		if r.firstBodyLineIdx < 0 && len(line) > 0 && line[0] != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}
	}

	result, err := r.ReformatSeg()
	if err != nil {
		t.Fatalf("ReformatSeg 失败: %v", err)
	}

	t.Logf("输出:\n%s", result)

	// 验证输出以 "# {" 开头
	if !strings.HasPrefix(result, "# {") {
		t.Errorf("期望输出以 '# {' 开头, 实际: %s", result[:min(50, len(result))])
	}

	// 验证包含 db_name
	if !strings.Contains(result, `"db_name":"dbtest3"`) {
		t.Error("期望包含 db_name:dbtest3")
	}

	// 验证包含 query_start_ts
	if !strings.Contains(result, `"query_start_ts":"1782921603"`) {
		t.Error("期望包含 query_start_ts:1782921603")
	}

	// 验证包含 session_id
	if !strings.Contains(result, `"session_id":"622265227"`) {
		t.Error("期望包含 session_id:622265227")
	}

	// 验证包含 Time（原始 key 名保留大写）
	if !strings.Contains(result, `"Time":"2026-07-02T00:00:20.581596+08:00"`) {
		t.Error("期望包含 Time 字段")
	}

	// 验证包含 Query_time（原始 key 名）
	if !strings.Contains(result, `"Query_time":"17.501662"`) {
		t.Error("期望包含 Query_time 字段")
	}

	// 验证包含 Lock_time 等其他原始注释字段
	if !strings.Contains(result, `"Lock_time":"0.000423"`) {
		t.Error("期望包含 Lock_time 字段")
	}
	if !strings.Contains(result, `"Schema":"dbtest3"`) {
		t.Error("期望包含 Schema 字段")
	}

	// 验证 SQL body 不包含 use 和 SET timestamp
	if strings.Contains(result, "use dbtest3;") {
		t.Error("SQL body 不应包含 use dbtest3;")
	}
	if strings.Contains(result, "SET timestamp=") {
		t.Error("SQL body 不应包含 SET timestamp=")
	}

	// 验证 SQL body 包含实际 SQL
	if !strings.Contains(result, "select * from users where id = 1;") {
		t.Error("期望 SQL body 包含实际 SQL")
	}

	_ = f.Close()
}

func TestReformatSeg_MultiLineSQL(t *testing.T) {
	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		commentHeadTime:            "2026-07-02T07:25:45.877115Z",
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 4096),
		writtenBytes:               0,
		segBuf:                     make([]byte, 0, 64*1024),
		firstBodyLineIdx:           -1,
	}

	// 模拟含多行 SQL 和 # 开头行的段
	rawLines := [][]byte{
		[]byte("# Time: 2026-07-02T07:25:45.877115Z"),
		[]byte("# User@Host: user2[user2] @  [1.1.1.1]"),
		[]byte("# Thread_id: 98343452  Schema: tesddb_631  QC_hit: No"),
		[]byte("# Query_time: 5.368769  Lock_time: 0.046386  Rows_sent: 0  Rows_examined: 0"),
		[]byte("SET timestamp=1782977115;"),
		[]byte("select sleep(10) from infodba_schema.master_slave_heartbeat where master_server_id='"),
		[]byte("# adfb;' or master_server_id!=\"\";"),
	}

	for _, line := range rawLines {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, line...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(line)})
		r.parseLine(line)
		if r.firstBodyLineIdx < 0 && len(line) > 0 && line[0] != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}
	}

	result, err := r.ReformatSeg()
	if err != nil {
		t.Fatalf("ReformatSeg 失败: %v", err)
	}

	t.Logf("输出:\n%s", result)

	// 验证 JSON header
	if !strings.Contains(result, `"db_name":"tesddb_631"`) {
		t.Error("期望包含 db_name:tesddb_631")
	}
	if !strings.Contains(result, `"session_id":"98343452"`) {
		t.Error("期望包含 session_id:98343452")
	}

	// 验证多行 SQL 保留（包含 # 开头的 SQL 行）
	if !strings.Contains(result, "select sleep(10) from infodba_schema.master_slave_heartbeat") {
		t.Error("期望包含 SQL 第一行")
	}
	if !strings.Contains(result, `# adfb;' or master_server_id!="";`) {
		t.Error("期望包含 SQL 中以 # 开头的行（不应被过滤）")
	}

	_ = f.Close()
}

// ==================== 基于 slow-query-test.txt 的 Reformat 集成测试 ====================

func TestReformatProcessSlowQueryTestFile(t *testing.T) {
	// 读取样例文件
	testDataPath := filepath.Join(".", "slow-query-test.txt")
	inputData, err := os.ReadFile(testDataPath)
	if err != nil {
		t.Fatalf("读取测试样例文件失败: %v", err)
	}

	tmpDir := t.TempDir()
	dbRegFile := filepath.Join(tmpDir, "current_db.reg")
	timeRegFile := filepath.Join(tmpDir, "comment_head_time.reg")
	logFile := filepath.Join(tmpDir, "test_slowlog.log")

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}

	r := &SlowlogReport{
		currentDB:                  "",
		currentDBRegFilePath:       dbRegFile,
		commentHeadTimeRegFilePath: timeRegFile,
		logFilePath:                logFile,
		logFile:                    f,
		writer:                     bufio.NewWriterSize(f, 256*1024),
		writtenBytes:               0,
		segBuf:                     make([]byte, 0, 64*1024),
		firstBodyLineIdx:           -1,
	}

	// 模拟 Run() 中的 scanner 逻辑，使用 ReformatSegToWriter 替代 rewriteSeg
	scanner := bufio.NewScanner(bytes.NewReader(inputData))
	scanner.Buffer(make([]byte, 64*1024), 100*1024*1024)

	var segReady bool
	var inSegment bool
	for scanner.Scan() {
		rawLine := scanner.Bytes()
		line := bytes.TrimSpace(rawLine)

		if segReady && isSegmentStartLine(line) {
			if err := r.ReformatSegToWriter(); err != nil {
				t.Fatalf("ReformatSegToWriter 失败: %v", err)
			}
			r.resetSeg()
			segReady = false
			inSegment = false
		}

		if !inSegment {
			if isSkippableSlowlogHeaderLine(line) || isBlankLine(line) {
				continue
			}
		}

		if isSegmentStartLine(line) {
			inSegment = true
		}

		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, rawLine...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(rawLine)})
		r.parseLine(line)
		firstByte := firstNonSpaceByte(rawLine)
		if r.firstBodyLineIdx < 0 && firstByte != 0 && firstByte != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}

		if !isBlankLine(rawLine) {
			segReady = lineEndsWithSemicolon(rawLine)
		}
	}
	// 处理残留段
	if len(r.segRanges) > 0 && segReady {
		if err := r.ReformatSegToWriter(); err != nil {
			t.Fatalf("处理残留段失败: %v", err)
		}
	}

	_ = r.writer.Flush()
	_ = f.Close()

	// 读取输出结果
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Fatal(err)
	}
	output := string(content)

	// golden file 比较
	goldenPath := filepath.Join(".", "slow-query-test-reformat.txt")
	if *updateGolden {
		err = os.WriteFile(goldenPath, content, 0644)
		if err != nil {
			t.Fatalf("更新 reformat golden 文件失败: %v", err)
		}
		t.Logf("reformat golden 文件已更新: %s", goldenPath)
	} else {
		goldenData, err := os.ReadFile(goldenPath)
		if err == nil {
			if !bytes.Equal(content, goldenData) {
				t.Errorf("输出与 reformat golden 文件不匹配。实际输出前500字节:\n%s", string(content[:min(500, len(content))]))
			}
		} else {
			t.Logf("reformat golden 文件不存在，跳过比较（使用 -update 生成）: %v", err)
		}
	}

	t.Logf("=== Reformat 输出结果 ===\n%s", output)

	// 验证每段都以 "# {" 开头
	lines := strings.Split(strings.TrimSpace(output), "\n")
	jsonHeaderCount := 0
	for _, l := range lines {
		if strings.HasPrefix(l, "# {") {
			jsonHeaderCount++
		}
	}
	if jsonHeaderCount != 12 {
		t.Errorf("期望 12 个 JSON header 行, 实际 %d 个", jsonHeaderCount)
	}

	// 验证不包含旧格式的 # Db_name: 行
	if strings.Contains(output, "# Db_name:") {
		t.Error("Reformat 输出不应包含旧格式的 '# Db_name:' 行")
	}

	// 验证不包含 # Time: 等原始注释行（已被 JSON 替代）
	if strings.Contains(output, "# Time:") {
		t.Error("Reformat 输出不应包含原始 '# Time:' 行")
	}
	if strings.Contains(output, "# User@Host:") {
		t.Error("Reformat 输出不应包含原始 '# User@Host:' 行")
	}
	if strings.Contains(output, "# Query_time:") {
		t.Error("Reformat 输出不应包含原始 '# Query_time:' 行")
	}

	// 验证 SQL body 不包含 SET timestamp=
	if strings.Contains(output, "SET timestamp=") {
		t.Error("Reformat 输出的 SQL body 不应包含 'SET timestamp='")
	}

	// 验证 SQL 内容完整
	if !strings.Contains(output, "select sleep(10);") {
		t.Error("期望输出包含 'select sleep(10);'")
	}
	if !strings.Contains(output, "order by FIELD(status,") {
		t.Error("期望输出包含多行 SQL 的 order by 部分")
	}
	// 验证含 # 开头的 SQL 行被保留
	if !strings.Contains(output, `# adfb;' or master_server_id!="";`) {
		t.Error("期望输出包含 SQL 中的 '# adfb;' 行")
	}
}
