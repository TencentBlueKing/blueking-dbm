package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeFile(t *testing.T, dir, name, content string) string {
	t.Helper()
	p := filepath.Join(dir, name)
	if err := os.WriteFile(p, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return p
}

// 13 个内置默认入库项应能生成 defaults 文件并被子集配置整项覆盖
func TestGenerateAndOverride(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	writeFile(t, dir, "datasource.yaml", "[]\n")

	if err := InitConfig(mainConf, true); err != nil {
		t.Fatal(err)
	}
	defaultsFile := filepath.Join(dir, DefaultsSinkerFile)
	content, err := os.ReadFile(defaultsFile)
	if err != nil {
		t.Fatalf("defaults file not generated: %v", err)
	}
	if !strings.Contains(string(content), "DO NOT EDIT") {
		t.Fatal("missing generated header")
	}
	if !strings.Contains(string(content), "mysql_proxy_connlog_v2") {
		t.Fatal("defaults missing builtin entry")
	}

	// 用户配置整项覆盖 mysql_proxy_connlog，并新增一个 group_id_suffix 变体 + 关掉一项
	userConf := `
- bk_collector_name: mysql_proxy_connlog_v2_new
  model_table: mysql_proxy_connlog
  datasource: dbmReport
  strict_schema: true
  ingest_threads: 8
  sink_batch_size: 20000
- bk_collector_name: mysql_proxy_connlog_v2
  model_table: mysql_proxy_connlog
  group_id_suffix: _v2
  datasource: dbmStats
  strict_schema: true
- topic: redis_backup_progress
  model_table: tb_redis_backup_progress
  datasource: dbmReport
  enable: false
`
	writeFile(t, dir, "data.user.yaml", userConf)

	// 再次 InitConfig 会覆盖重写 defaults，用户配置仍然生效
	if err = InitConfig(mainConf, true); err != nil {
		t.Fatal(err)
	}
	byKey := map[string]*SinkerConfig{}
	for _, s := range SinkerConfigs {
		byKey[s.Key()] = s
	}
	// 被覆盖：bk_collector_name 和 datasource 都换了
	got := byKey["mysql_proxy_connlog|"]
	if got == nil || got.BkCollectorName != "mysql_proxy_connlog_v2_new" ||
		got.Datasource != DsDbmReport || got.IngestThreads != 8 || got.SinkBatchSize != 20000 {
		t.Fatalf("override failed: %+v", got)
	}
	// 新增：同 model_table 不同 group_id_suffix 是独立项，不受覆盖影响
	if v, ok := byKey["mysql_proxy_connlog|_v2"]; !ok || v.Datasource != DsDbmStats {
		t.Fatalf("new sinker failed: %+v", v)
	}
	// 关闭
	if s := byKey["tb_redis_backup_progress|"]; s == nil || s.IsEnabled() {
		t.Fatalf("disable failed: %+v", s)
	}
	// 未被用户改动的默认项保留
	if s := byKey["tb_mysql_slow_log|"]; s == nil || s.BkCollectorName != "mysql_slowlog" ||
		s.FetchMinBytes != 1048576 || s.Datasource != DsDbmStats {
		t.Fatalf("default lost: %+v", s)
	}
	if len(SinkerConfigs) != 14 {
		t.Fatalf("expect 14 sinkers, got %d", len(SinkerConfigs))
	}
}

// 只在 data.defaults.yaml 里手改也能生效(此时 --enable-defaults 关闭)
func TestDefaultsFileWithoutGenerate(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	writeFile(t, dir, "data.defaults.yaml", `
- topic: mysql_binlog_result
  model_table: tb_mysql_binlog_result
  datasource: dbmReport
  strict_schema: true
`)
	if err := InitConfig(mainConf, false); err != nil {
		t.Fatal(err)
	}
	if len(SinkerConfigs) != 1 || SinkerConfigs[0].ModelTable != "tb_mysql_binlog_result" {
		t.Fatalf("expect single sinker, got %d", len(SinkerConfigs))
	}
}

// 多个用户文件里的重复 key 必须报错，避免生效结果取决于文件名
func TestDuplicateAcrossUserFiles(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	item := `
- topic: mysql_binlog_result
  model_table: tb_mysql_binlog_result
  datasource: dbmReport
`
	writeFile(t, dir, "data.a.yaml", item)
	writeFile(t, dir, "data.b.yaml", item)
	err := InitConfig(mainConf, false)
	if err == nil || !strings.Contains(err.Error(), "duplicate sinker") {
		t.Fatalf("expect duplicate error, got %v", err)
	}
}

// 文件内重复 key
func TestDuplicateInSameFile(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	item := `
- topic: mysql_binlog_result
  model_table: tb_mysql_binlog_result
  datasource: dbmReport
- topic: mysql_binlog_result2
  model_table: tb_mysql_binlog_result
  datasource: dbmReport
`
	writeFile(t, dir, "data.user.yaml", item)
	err := InitConfig(mainConf, false)
	if err == nil || !strings.Contains(err.Error(), "duplicate sinker") {
		t.Fatalf("expect duplicate error, got %v", err)
	}
}

// 没有任何配置时报错，提示用 --enable-defaults
func TestNoSinker(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	err := InitConfig(mainConf, false)
	if err == nil || !strings.Contains(err.Error(), "--enable-defaults") {
		t.Fatalf("expect no sinker error, got %v", err)
	}
}

// 非法字段值
func TestInvalidWriteMode(t *testing.T) {
	dir := t.TempDir()
	mainConf := writeFile(t, dir, "config.yaml", "otel_port: 0\n")
	writeFile(t, dir, "data.user.yaml", `
- topic: mysql_binlog_result
  model_table: tb_mysql_binlog_result
  datasource: dbmReport
  write_mode: not_exist
`)
	err := InitConfig(mainConf, false)
	if err == nil || !strings.Contains(err.Error(), "invalid write_mode") {
		t.Fatalf("expect write_mode error, got %v", err)
	}
}
