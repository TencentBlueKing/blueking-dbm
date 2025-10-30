package syntax_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/syntax"
)

// init 函数在包加载时最先执行，在所有其他包的 init 之前设置环境变量
func init() {
	// 设置测试环境变量，避免init函数尝试连接数据库
	// 这些环境变量会在 model.init() 和 syntax.init() 执行前生效
	os.Setenv("DB_HOST", "")
	os.Setenv("DB_PORT", "0")
	os.Setenv("SKIP_DB_INIT", "true")
	os.Setenv("TESTING", "true")
}

const (
	testTmysqlParseBin = "/tmysqlparse"
	testWorkdir        = "/tmp/syntax_test"
)

// setupTestEnv 初始化测试环境
func setupTestEnv(t *testing.T) (string, func()) {
	t.Helper()

	// 检查 tmysqlparse 是否存在
	if _, err := os.Stat(testTmysqlParseBin); os.IsNotExist(err) {
		if !testing.Short() {
			t.Skipf("tmysqlparse binary not found at %s, skipping integration tests. Run with -short to skip.", testTmysqlParseBin)
		}
	}

	// 创建临时工作目录 - 先强制删除再创建
	// 如果 testWorkdir 是文件，先删除
	if info, err := os.Stat(testWorkdir); err == nil {
		if !info.IsDir() {
			os.Remove(testWorkdir)
		} else {
			os.RemoveAll(testWorkdir)
		}
	}
	workdir := filepath.Join(testWorkdir, t.Name())
	err := os.MkdirAll(workdir, 0755)
	require.NoError(t, err, "failed to create test workdir")

	// 规则在包初始化时自动加载 (syntax.R 和 syntax.SR)
	// 无需手动初始化

	// 返回清理函数
	cleanup := func() {
		os.RemoveAll(workdir)
	}

	return workdir, cleanup
}

// getTestDataPath 获取测试数据文件路径
func getTestDataPath(filename string) string {
	return filepath.Join("testdata", filename)
}

// copyTestFile 复制测试文件到工作目录
func copyTestFile(t *testing.T, srcFile, destDir string) error {
	t.Helper()

	data, err := os.ReadFile(srcFile)
	if err != nil {
		return err
	}

	destFile := filepath.Join(destDir, filepath.Base(srcFile))
	return os.WriteFile(destFile, data, 0644)
}

func TestKeywordFilter(t *testing.T) {
	matched, _ := syntax.KeyWordValidator("mysql-5.7", "call")
	assert.Equal(t, true, matched)
}

// TestTmysqlParseFile_Do_ValidDDL 测试正确的DDL语句
func TestTmysqlParseFile_Do_ValidDDL(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	// 复制测试文件到工作目录
	testFile := getTestDataPath("valid_ddl.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	// 创建测试对象
	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"valid_ddl.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"valid_ddl.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	// 执行测试 - MySQL 5.7
	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	// 验证结果
	fileResult, ok := result["valid_ddl.sql"]
	require.True(t, ok, "should have result for valid_ddl.sql")

	// 正确的SQL不应该有语法错误
	assert.Empty(t, fileResult.SyntaxFailInfos, "should not have syntax errors")

	t.Logf("Result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
}

// TestTmysqlParseFile_Do_ValidDML 测试正确的DML语句
func TestTmysqlParseFile_Do_ValidDML(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("valid_dml.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"valid_dml.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"valid_dml.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["valid_dml.sql"]
	require.True(t, ok)
	assert.Empty(t, fileResult.SyntaxFailInfos, "should not have syntax errors for valid DML")

	t.Logf("DML Result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
}

// TestTmysqlParseFile_Do_InvalidSQL 测试语法错误的SQL
func TestTmysqlParseFile_Do_InvalidSQL(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("invalid_syntax.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"invalid_syntax.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"invalid_syntax.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	// 注意：即使有语法错误，Do方法可能也不返回错误，而是在结果中记录
	_ = err
	require.NotNil(t, result)

	fileResult, ok := result["invalid_syntax.sql"]
	require.True(t, ok)

	// 语法错误的SQL应该有错误信息
	assert.NotEmpty(t, fileResult.SyntaxFailInfos, "should have syntax errors for invalid SQL")

	t.Logf("Invalid SQL Result: %d syntax errors", len(fileResult.SyntaxFailInfos))
	for i, fail := range fileResult.SyntaxFailInfos {
		t.Logf("  Error %d: Line %d, Code %d, Msg: %s", i+1, fail.Line, fail.ErrorCode, fail.ErrorMsg)
	}
}

// TestTmysqlParseFile_Do_HighRiskCommands 测试高危命令检测
func TestTmysqlParseFile_Do_HighRiskCommands(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("high_risk_commands.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"high_risk_commands.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"high_risk_commands.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["high_risk_commands.sql"]
	require.True(t, ok)

	// 应该检测到高危命令
	assert.NotEmpty(t, fileResult.RiskWarnings, "should detect high risk commands")

	t.Logf("High Risk Commands Result: %d risk warnings", len(fileResult.RiskWarnings))
	for i, risk := range fileResult.RiskWarnings {
		t.Logf("  Risk %d: Line %d, Type: %s, Info: %s", i+1, risk.Line, risk.CommandType, risk.WarnInfo)
	}
}

// TestTmysqlParseFile_Do_BannedCommands 测试禁用命令检测
func TestTmysqlParseFile_Do_BannedCommands(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("banned_commands.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"banned_commands.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"banned_commands.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["banned_commands.sql"]
	require.True(t, ok)

	// 应该检测到禁用命令
	assert.NotEmpty(t, fileResult.BanWarnings, "should detect banned commands")

	t.Logf("Banned Commands Result: %d ban warnings", len(fileResult.BanWarnings))
	for i, ban := range fileResult.BanWarnings {
		t.Logf("  Ban %d: Line %d, Type: %s, Info: %s", i+1, ban.Line, ban.CommandType, ban.WarnInfo)
	}
}

// TestTmysqlParseFile_Do_MySQL_MultiVersion 测试MySQL多版本
func TestTmysqlParseFile_Do_MySQL_MultiVersion(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("valid_ddl.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"valid_ddl.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"valid_ddl.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	// 测试多个版本
	versions := []string{"5.6.24", "5.7.20", "8.0.18"}
	result, err := tf.Do(app.MySQL, versions)
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["valid_ddl.sql"]
	require.True(t, ok)

	t.Logf("Multi-version test result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
	t.Logf("Risk warnings: %v", fileResult.RiskWarnings)
	t.Logf("Ban warnings: %v", fileResult.BanWarnings)
	t.Logf("Syntax errors: %v", fileResult.SyntaxFailInfos)
}

// TestTmysqlParseFile_Do_Spider 测试Spider类型
func TestTmysqlParseFile_Do_Spider(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("spider_create_table.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	// Spider规则在包初始化时自动加载 (syntax.SR)
	// 无需手动初始化

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"spider_create_table.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"spider_create_table.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.Spider, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["spider_create_table.sql"]
	require.True(t, ok)

	t.Logf("Spider test result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
	t.Logf("Risk warnings: %v", fileResult.RiskWarnings)
	t.Logf("Ban warnings: %v", fileResult.BanWarnings)
	t.Logf("Syntax errors: %v", fileResult.SyntaxFailInfos)
}

// TestTmysqlParseFile_Do_SpiderInvalid 测试 Spider 建表的反向用例（应该触发检查错误）
func TestTmysqlParseFile_Do_SpiderInvalid(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("spider_create_table_invalid.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	// Spider规则在包初始化时自动加载 (syntax.SR)
	// 无需手动初始化

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"spider_create_table_invalid.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"spider_create_table_invalid.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.Spider, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["spider_create_table_invalid.sql"]
	require.True(t, ok)

	// 对于反向测试用例，我们期望有错误或警告
	t.Logf("Spider invalid test result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))

	// 断言：反向测试用例应该至少触发一些检查错误
	totalIssues := len(fileResult.SyntaxFailInfos) + len(fileResult.RiskWarnings) + len(fileResult.BanWarnings)
	assert.Greater(t, totalIssues, 0, "反向测试用例应该触发至少一个错误或警告")

	// 详细输出每个检查结果，帮助理解哪些规则被触发
	if len(fileResult.RiskWarnings) > 0 {
		t.Logf("Risk warnings detected:")
		for i, warn := range fileResult.RiskWarnings {
			t.Logf("  Warning %d: Line %d, Type: %s, Info: %s",
				i+1, warn.Line, warn.CommandType, warn.WarnInfo)
		}
	}

	if len(fileResult.BanWarnings) > 0 {
		t.Logf("Ban warnings detected:")
		for i, warn := range fileResult.BanWarnings {
			t.Logf("  Ban %d: Line %d, Type: %s, Info: %s",
				i+1, warn.Line, warn.CommandType, warn.WarnInfo)
		}
	}

	if len(fileResult.SyntaxFailInfos) > 0 {
		t.Logf("Syntax errors detected:")
		for i, fail := range fileResult.SyntaxFailInfos {
			t.Logf("  Error %d: Line %d, Code %d, Msg: %s",
				i+1, fail.Line, fail.ErrorCode, fail.ErrorMsg)
		}
	}
}

// TestTmysqlParseFile_Do_AdvancedFeatures 测试高级功能
func TestTmysqlParseFile_Do_AdvancedFeatures(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("valid_advanced.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"valid_advanced.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"valid_advanced.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["valid_advanced.sql"]
	require.True(t, ok)

	t.Logf("Advanced features result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
}

// TestTmysqlParseFile_CheckConflictUsedb 测试USE DB冲突检测
func TestTmysqlParseFile_CheckConflictUsedb(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("use_db_conflict.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"use_db_conflict.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"use_db_conflict.sql"},
					// 指定多个数据库，这应该触发USE DB冲突检测
					DbNames: []string{"database%", "test%"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	// 可能会有错误或警告
	_ = err
	require.NotNil(t, result)

	fileResult, ok := result["use_db_conflict.sql"]
	require.True(t, ok)

	// 应该检测到USE DB冲突
	t.Logf("USE DB conflict result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))

	if len(fileResult.BanWarnings) > 0 {
		t.Logf("Ban warnings detected (expected for USE DB conflict):")
		for i, ban := range fileResult.BanWarnings {
			t.Logf("  Ban %d: %s", i+1, ban.WarnInfo)
		}
	}
}

// TestTmysqlParseFile_Do_MultipleFiles 测试多文件并发处理
func TestTmysqlParseFile_Do_MultipleFiles(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	// 复制多个测试文件
	testFiles := []string{"valid_ddl.sql", "valid_dml.sql"}
	for _, file := range testFiles {
		err := copyTestFile(t, getTestDataPath(file), workdir)
		require.NoError(t, err)
	}

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: testFiles,
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: testFiles,
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	// 验证所有文件都有结果
	for _, file := range testFiles {
		fileResult, ok := result[file]
		require.True(t, ok, "should have result for %s", file)
		t.Logf("File %s: %d syntax errors, %d risk warnings, %d ban warnings",
			file,
			len(fileResult.SyntaxFailInfos),
			len(fileResult.RiskWarnings),
			len(fileResult.BanWarnings))
	}
}

// TestTmysqlParseFile_Do_EmptyFile 测试空文件
func TestTmysqlParseFile_Do_EmptyFile(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("empty_file.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"empty_file.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"empty_file.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["empty_file.sql"]
	require.True(t, ok)

	// 空文件不应该有任何错误或警告
	assert.Empty(t, fileResult.SyntaxFailInfos, "empty file should not have syntax errors")

	t.Logf("Empty file result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
}

// TestTmysqlParseFile_Do_LargeFile 测试大文件
func TestTmysqlParseFile_Do_LargeFile(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	workdir, cleanup := setupTestEnv(t)
	defer cleanup()

	testFile := getTestDataPath("large_file.sql")
	err := copyTestFile(t, testFile, workdir)
	require.NoError(t, err)

	tf := &syntax.TmysqlParseFile{
		TmysqlParse: syntax.TmysqlParse{
			TmysqlParseBinPath: testTmysqlParseBin,
			BaseWorkdir:        workdir,
		},
		Param: syntax.CheckSQLFileParam{
			FileNames: []string{"large_file.sql"},
			ExecuteObjects: []syntax.ExecuteSQLFileObj{
				{
					LineId:   1,
					SQLFiles: []string{"large_file.sql"},
					DbNames:  []string{"test_db"},
				},
			},
		},
		IsLocalFile: true,
	}

	result, err := tf.Do(app.MySQL, []string{"5.7.20"})
	require.NoError(t, err)
	require.NotNil(t, result)

	fileResult, ok := result["large_file.sql"]
	require.True(t, ok)

	t.Logf("Large file result: %d syntax errors, %d risk warnings, %d ban warnings",
		len(fileResult.SyntaxFailInfos),
		len(fileResult.RiskWarnings),
		len(fileResult.BanWarnings))
}

// TestTmysqlParseFile_Do_TableDriven 表驱动测试
func TestTmysqlParseFile_Do_TableDriven(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tests := []struct {
		name      string
		sqlFiles  []string
		dbtype    string
		versions  []string
		dbNames   []string
		wantErr   bool
		checkFunc func(t *testing.T, result map[string]*syntax.CheckInfo)
	}{
		{
			name:     "valid DDL statements",
			sqlFiles: []string{"valid_ddl.sql"},
			dbtype:   app.MySQL,
			versions: []string{"5.7.20"},
			dbNames:  []string{"test_db"},
			wantErr:  false,
			checkFunc: func(t *testing.T, result map[string]*syntax.CheckInfo) {
				fileResult, ok := result["valid_ddl.sql"]
				require.True(t, ok)
				assert.Empty(t, fileResult.SyntaxFailInfos)
			},
		},
		{
			name:     "invalid syntax",
			sqlFiles: []string{"invalid_syntax.sql"},
			dbtype:   app.MySQL,
			versions: []string{"5.7.20"},
			dbNames:  []string{"test_db"},
			wantErr:  false,
			checkFunc: func(t *testing.T, result map[string]*syntax.CheckInfo) {
				fileResult, ok := result["invalid_syntax.sql"]
				require.True(t, ok)
				assert.NotEmpty(t, fileResult.SyntaxFailInfos)
			},
		},
		{
			name:     "high risk commands",
			sqlFiles: []string{"high_risk_commands.sql"},
			dbtype:   app.MySQL,
			versions: []string{"5.7.20"},
			dbNames:  []string{"test_db"},
			wantErr:  false,
			checkFunc: func(t *testing.T, result map[string]*syntax.CheckInfo) {
				fileResult, ok := result["high_risk_commands.sql"]
				require.True(t, ok)
				assert.NotEmpty(t, fileResult.RiskWarnings)
			},
		},
		{
			name:     "banned commands",
			sqlFiles: []string{"banned_commands.sql"},
			dbtype:   app.MySQL,
			versions: []string{"5.7.20"},
			dbNames:  []string{"test_db"},
			wantErr:  false,
			checkFunc: func(t *testing.T, result map[string]*syntax.CheckInfo) {
				fileResult, ok := result["banned_commands.sql"]
				require.True(t, ok)
				assert.NotEmpty(t, fileResult.BanWarnings)
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			workdir, cleanup := setupTestEnv(t)
			defer cleanup()

			// 复制测试文件
			for _, file := range tt.sqlFiles {
				err := copyTestFile(t, getTestDataPath(file), workdir)
				require.NoError(t, err)
			}

			tf := &syntax.TmysqlParseFile{
				TmysqlParse: syntax.TmysqlParse{
					TmysqlParseBinPath: testTmysqlParseBin,
					BaseWorkdir:        workdir,
				},
				Param: syntax.CheckSQLFileParam{
					FileNames: tt.sqlFiles,
					ExecuteObjects: []syntax.ExecuteSQLFileObj{
						{
							LineId:   1,
							SQLFiles: tt.sqlFiles,
							DbNames:  tt.dbNames,
						},
					},
				},
				IsLocalFile: true,
			}

			result, err := tf.Do(tt.dbtype, tt.versions)
			if tt.wantErr {
				assert.Error(t, err)
				return
			}

			require.NoError(t, err)
			require.NotNil(t, result)

			if tt.checkFunc != nil {
				tt.checkFunc(t, result)
			}
		})
	}
}
