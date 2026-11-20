package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"encoding/json"
	"os"
	"strconv"
	"strings"
	"testing"
)

func TestIsTlinux12(t *testing.T) {
	t.Logf("is tlinux1.2: %v", isTlinux12())
}

func TestValidateArchiveBaseName(t *testing.T) {
	cases := []struct {
		name    string
		wantErr bool
	}{
		{"migrate-root-1-seta", false},
		{"", true},
		{".", true},
		{"..", true},
		{"a/b", true},
		{`a\b`, true},
	}
	for _, tc := range cases {
		err := validateArchiveBaseName(tc.name)
		if tc.wantErr && err == nil {
			t.Fatalf("validateArchiveBaseName(%q) want error", tc.name)
		}
		if !tc.wantErr && err != nil {
			t.Fatalf("validateArchiveBaseName(%q) unexpected err: %v", tc.name, err)
		}
	}
}

func TestUnderBackupDir(t *testing.T) {
	backupDir := "/data/dbbak/billdump"
	if err := underBackupDir(backupDir, "/data/dbbak/billdump/ok"); err != nil {
		t.Fatalf("ok child: %v", err)
	}
	if err := underBackupDir(backupDir, "/data/dbbak/billdump"); err == nil {
		t.Fatal("equal backup dir should fail")
	}
	if err := underBackupDir(backupDir, "/data/dbbak"); err == nil {
		t.Fatal("parent dir should fail")
	}
	if err := underBackupDir(backupDir, "/tmp/other"); err == nil {
		t.Fatal("outside dir should fail")
	}
}

func TestBackupJob(t *testing.T) {
	if os.Getenv("TestDump_PORT") == "" {
		t.Skip("integration test; set TestDump_PORT, TestDump_HOST, TestDump_USER, TestDump_PASS, TestDump_FILE_TAG")
	}
	// list all envs in Testdump_*
	outs := []string{}
	for _, env := range os.Environ() {
		if len(env) < 100 {
			outs = append(outs, env)
		}
	}
	t.Logf("envs:\n%s", strings.Join(outs, "\n"))
	port, err := strconv.ParseInt(os.Getenv("TestDump_PORT"), 10, 64)
	if err != nil {
		t.Errorf("strconv.ParseInt failed, err:%v", err)
		return
	}
	param := backupParams{
		BkDbmInstance: config.BkDbmLabel{
			BkBizID:   111,
			BkCloudID: 1,
			App:       "test",
			AppName:   "test",
		},

		IP:                    os.Getenv("TestDump_HOST"),
		Port:                  int(port),
		AdminUsername:         os.Getenv("TestDump_USER"),
		AdminPassword:         os.Getenv("TestDump_PASS"),
		SkipBackupSystemDb:    false,
		WaitBackupSysTaskDone: false,
		FileTag:               os.Getenv("TestDump_FILE_TAG"),
		BackupType:            "logical",
		MaxConcurrency:        4,
	}
	payload, err := json.Marshal(param)
	if err != nil {
		t.Errorf("json.Marshal failed, err:%v", err)
		return
	}
	runtime, err := jobruntime.NewJobGenericRuntime(
		"111", "333000333", "3333", "4444",
		string(payload), consts.PayloadFormatRaw, "mongodb_backup", "test")
	if err != nil {
		t.Errorf("NewJobGenericRuntime failed, err:%v", err)
		return
	}
	BackupJob := NewBackupJob()
	err = BackupJob.Init(runtime)
	if err != nil {
		t.Errorf("BackupJob.Init failed, err:%v", err)
		return
	}
	err = BackupJob.Run()
	if err != nil {
		t.Errorf("BackupJob.Run failed, err:%v", err)
		return
	}
}
