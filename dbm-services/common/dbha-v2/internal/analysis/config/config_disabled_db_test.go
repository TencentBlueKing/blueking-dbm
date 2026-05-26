package config

import (
	"os"
	"path/filepath"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestLoadNormalizeDisabledDB(t *testing.T) {
	oldCfg := Cfg
	t.Cleanup(func() {
		Cfg = oldCfg
	})

	tmpDir := t.TempDir()
	cfgFile := filepath.Join(tmpDir, "analysis.yaml")
	content := []byte("workflow:\n  disabledDB: [MySQL, redis, REDIS]\n")
	if err := os.WriteFile(cfgFile, content, 0o600); err != nil {
		t.Fatalf("failed to write config file: %s", err)
	}

	if err := Load(cfgFile); err != nil {
		t.Fatalf("load config failed: %s", err)
	}

	expected := []haprobe.DbType{haprobe.DbTypeMySql, haprobe.DbTypeRedis}
	if len(Cfg.Workflow.DisabledDB) != len(expected) {
		t.Fatalf("unexpected disabledDB size, got: %d", len(Cfg.Workflow.DisabledDB))
	}
	for idx, dbType := range expected {
		if Cfg.Workflow.DisabledDB[idx] != dbType {
			t.Fatalf("unexpected disabledDB value at %d, got: %s", idx, Cfg.Workflow.DisabledDB[idx])
		}
	}
}

func TestLoadValidDisabledDBWithNonMysqlRedisTypes(t *testing.T) {
	oldCfg := Cfg
	t.Cleanup(func() {
		Cfg = oldCfg
	})

	tmpDir := t.TempDir()
	cfgFile := filepath.Join(tmpDir, "analysis.yaml")
	content := []byte("workflow:\n  disabledDB: [kafka, SQLServer, doris]\n")
	if err := os.WriteFile(cfgFile, content, 0o600); err != nil {
		t.Fatalf("failed to write config file: %s", err)
	}

	if err := Load(cfgFile); err != nil {
		t.Fatalf("load config failed: %s", err)
	}

	expected := []haprobe.DbType{
		haprobe.DbTypeKafka,
		haprobe.DbTypeSqlServer,
		haprobe.DbTypeDoris,
	}
	if len(Cfg.Workflow.DisabledDB) != len(expected) {
		t.Fatalf("unexpected disabledDB size, got: %d", len(Cfg.Workflow.DisabledDB))
	}
	for idx, dbType := range expected {
		if Cfg.Workflow.DisabledDB[idx] != dbType {
			t.Fatalf("unexpected disabledDB value at %d, got: %s", idx, Cfg.Workflow.DisabledDB[idx])
		}
	}
}

func TestLoadInvalidDisabledDB(t *testing.T) {
	oldCfg := Cfg
	t.Cleanup(func() {
		Cfg = oldCfg
	})

	tmpDir := t.TempDir()
	cfgFile := filepath.Join(tmpDir, "analysis.yaml")
	content := []byte("workflow:\n  disabledDB: [postgres]\n")
	if err := os.WriteFile(cfgFile, content, 0o600); err != nil {
		t.Fatalf("failed to write config file: %s", err)
	}

	if err := Load(cfgFile); err == nil {
		t.Fatal("expected load failure for invalid disabledDB value")
	}
}
