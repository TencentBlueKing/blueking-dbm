package atomredis

import (
	"net"
	"path/filepath"
	"regexp"
	"strconv"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

func unusedLocalPort(t *testing.T) int {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen on random local port failed: %v", err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	if err := listener.Close(); err != nil {
		t.Fatalf("close random local listener failed: %v", err)
	}
	return port
}

func TestDtsOnlineSwitchBackupNamesIncludeTimestamp(t *testing.T) {
	timestamp := "20260528111617.123456789"
	job := &RedisDtsOnlineSwitch{
		params: RedisDtsOnlineSwitchParams{
			DtsBillID:      123,
			SrcProxyIP:     "1.1.1.1",
			SrcProxyPort:   50048,
			SrcClusterType: consts.TendisTypeTwemproxyRedisInstance,
		},
	}

	backupFile := filepath.Base(job.buildSrcProxyConfBackupFile(timestamp))
	wantFile := "dts_bak_config.billid_123.1.1.1.1_50048.20260528111617.123456789.yml"
	if backupFile != wantFile {
		t.Fatalf("unexpected backup file name, got:%s want:%s", backupFile, wantFile)
	}

	backupDir := job.buildGeneratedProxyConfDirBackup("/data/predixy/50048/", timestamp)
	wantDir := "/data/predixy/50048.dts_online_switch_bak.billid_123.20260528111617.123456789"
	if backupDir != wantDir {
		t.Fatalf("unexpected backup dir name, got:%s want:%s", backupDir, wantDir)
	}
}

func TestDtsOnlineSwitchBackupTimestampFormat(t *testing.T) {
	timestamp := newDtsOnlineSwitchBackupTimestamp()
	matched := regexp.MustCompile(`^\d{14}\.\d{9}$`).MatchString(timestamp)
	if !matched {
		t.Fatalf("unexpected backup timestamp format:%s", timestamp)
	}
}

func TestIsProxyAliveReturnsQuicklyForClosedPort(t *testing.T) {
	port := unusedLocalPort(t)
	job := &RedisDtsOnlineSwitch{}
	start := time.Now()

	alive := job.IsProxyAlive("127.0.0.1", port, "")
	if alive {
		t.Fatalf("expected proxy on closed port %s to be dead", strconv.Itoa(port))
	}
	if elapsed := time.Since(start); elapsed > time.Second {
		t.Fatalf("closed-port proxy check took too long:%s", elapsed)
	}
}
