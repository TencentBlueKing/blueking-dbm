package atommongodb

import (
	"encoding/json"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
)

// pickFreeTCPPort returns a free local TCP port (IPv4). The listener is closed before return.
func pickFreeTCPPort(t *testing.T) int {
	t.Helper()
	ln, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	port := ln.Addr().(*net.TCPAddr).Port
	if err := ln.Close(); err != nil {
		t.Fatalf("close listener: %v", err)
	}
	return port
}

func marshalDeInstallParams(t *testing.T, p DeInstallConfParams) []byte {
	t.Helper()
	b, err := json.Marshal(p)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	return b
}

func runMongoDeinstall(t *testing.T, payload []byte, baseDir string) error {
	t.Helper()
	if baseDir == "" {
		baseDir = t.TempDir()
	}
	rt, err := jobruntime.NewJobGenericRuntime(
		"ut-deinstall-uid", "ut-root", "ut-node", "ut-v1",
		string(payload), consts.PayloadFormatRaw, "mongo_deinstall", baseDir,
	)
	if err != nil {
		t.Fatalf("NewJobGenericRuntime: %v", err)
	}
	j := NewDeInstall()
	if err := j.Init(rt); err != nil {
		return err
	}
	return j.Run()
}

// TestMongoDeinstall_Run_IdlePort exercises Init+Run when nothing is listening on the target port:
// CheckMongoService reports no mongo, shutdown is skipped, DirRename skipped when RenameDir=false.
func TestMongoDeinstall_Run_IdlePort(t *testing.T) {
	port := pickFreeTCPPort(t)
	p := DeInstallConfParams{
		IP:           "127.0.0.1",
		Port:         port,
		NodeInfo:     []string{"127.0.0.1"},
		InstanceType: "mongod",
		Force:        true,
		RenameDir:    false,
	}
	if err := runMongoDeinstall(t, marshalDeInstallParams(t, p), ""); err != nil {
		t.Fatalf("Run: %v", err)
	}
}

// TestMongoDeinstall_Run_DirRenameMovesDataAndLogTrees uses MONGO_DATA_DIR / MONGO_BACKUP_DIR under a
// temp root so DirRename runs real mv without touching host /data paths.
func TestMongoDeinstall_Run_DirRenameMovesDataAndLogTrees(t *testing.T) {
	root := t.TempDir()
	t.Setenv("MONGO_DATA_DIR", root)
	t.Setenv("MONGO_BACKUP_DIR", root)

	port := pickFreeTCPPort(t)
	portStr := strconv.Itoa(port)
	portDir := filepath.Join(root, "mongodata", portStr)
	logPortDir := filepath.Join(root, "mongolog", portStr)
	if err := os.MkdirAll(filepath.Join(portDir, "db"), 0o755); err != nil {
		t.Fatalf("mkdir data: %v", err)
	}
	if err := os.MkdirAll(logPortDir, 0o755); err != nil {
		t.Fatalf("mkdir log: %v", err)
	}
	if err := os.WriteFile(filepath.Join(portDir, "marker.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("write marker data: %v", err)
	}
	if err := os.WriteFile(filepath.Join(logPortDir, "marker.log"), []byte("log"), 0o644); err != nil {
		t.Fatalf("write marker log: %v", err)
	}

	p := DeInstallConfParams{
		IP:           "127.0.0.1",
		Port:         port,
		NodeInfo:     []string{"127.0.0.1"},
		InstanceType: "mongod",
		Force:        true,
		RenameDir:    true,
	}
	if err := runMongoDeinstall(t, marshalDeInstallParams(t, p), ""); err != nil {
		t.Fatalf("Run: %v", err)
	}

	if util.FileExists(portDir) {
		t.Fatalf("expected original data port dir removed, still exists: %s", portDir)
	}
	if util.FileExists(logPortDir) {
		t.Fatalf("expected original log port dir removed, still exists: %s", logPortDir)
	}

	dataRemoved, err := filepath.Glob(filepath.Join(root, "mongodata", "removed_"+portStr+"_*"))
	if err != nil {
		t.Fatalf("glob data removed: %v", err)
	}
	if len(dataRemoved) != 1 {
		t.Fatalf("want exactly one renamed data dir, got %v", dataRemoved)
	}
	if !util.FileExists(filepath.Join(dataRemoved[0], "marker.txt")) {
		t.Fatalf("marker.txt missing under %s", dataRemoved[0])
	}

	logRemoved, err := filepath.Glob(filepath.Join(root, "mongolog", "removed_"+portStr+"_*"))
	if err != nil {
		t.Fatalf("glob log removed: %v", err)
	}
	if len(logRemoved) != 1 {
		t.Fatalf("want exactly one renamed log dir, got %v", logRemoved)
	}
	if !util.FileExists(filepath.Join(logRemoved[0], "marker.log")) {
		t.Fatalf("marker.log missing under %s", logRemoved[0])
	}
}

func TestMongoDeinstall_Init_InvalidJSON(t *testing.T) {
	rt, err := jobruntime.NewJobGenericRuntime(
		"ut-deinstall-uid", "ut-root", "ut-node", "ut-v1",
		"{not-json", consts.PayloadFormatRaw, "mongo_deinstall", t.TempDir(),
	)
	if err != nil {
		t.Fatalf("NewJobGenericRuntime: %v", err)
	}
	j := NewDeInstall()
	if err := j.Init(rt); err == nil {
		t.Fatal("expected Init error for invalid JSON")
	}
}

func TestMongoDeinstall_Init_ValidateMissingRequiredFields(t *testing.T) {
	// Port=0 fails validate:"required" semantics for Port in some setups; omit InstanceType instead.
	p := DeInstallConfParams{
		IP:       "127.0.0.1",
		Port:     pickFreeTCPPort(t),
		NodeInfo: []string{"127.0.0.1"},
		// InstanceType intentionally empty
	}
	rt, err := jobruntime.NewJobGenericRuntime(
		"ut-deinstall-uid", "ut-root", "ut-node", "ut-v1",
		string(marshalDeInstallParams(t, p)), consts.PayloadFormatRaw, "mongo_deinstall", t.TempDir(),
	)
	if err != nil {
		t.Fatalf("NewJobGenericRuntime: %v", err)
	}
	j := NewDeInstall()
	if err := j.Init(rt); err == nil {
		t.Fatal("expected Init validation error")
	}
}
