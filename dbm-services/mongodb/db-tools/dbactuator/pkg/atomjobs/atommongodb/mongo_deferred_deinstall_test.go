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
)

func marshalDeferredDeInstallParams(t *testing.T, p DeferredDeInstallConfParams) []byte {
	t.Helper()
	b, err := json.Marshal(p)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	return b
}

func runMongoDeferredDeinstall(t *testing.T, payload []byte, baseDir string) error {
	t.Helper()
	if baseDir == "" {
		baseDir = t.TempDir()
	}
	rt, err := jobruntime.NewJobGenericRuntime(
		"ut-deferred-uid", "ut-root", "ut-node", "ut-v1",
		string(payload), consts.PayloadFormatRaw, "mongo_deferred_deinstall", baseDir,
	)
	if err != nil {
		t.Fatalf("NewJobGenericRuntime: %v", err)
	}
	j := NewDeferredDeInstall()
	if err := j.Init(rt); err != nil {
		return err
	}
	return j.Run()
}

func pickFreeTCPPortDeferred(t *testing.T) int {
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

// TestMongoDeferredDeinstall_ProcessStopped skips REMOVED/conn checks and renames dirs.
func TestMongoDeferredDeinstall_ProcessStopped(t *testing.T) {
	root := t.TempDir()
	t.Setenv("MONGO_DATA_DIR", root)
	t.Setenv("MONGO_BACKUP_DIR", root)

	port := pickFreeTCPPortDeferred(t)
	portStr := strconv.Itoa(port)
	portDir := filepath.Join(root, "mongodata", portStr)
	logPortDir := filepath.Join(root, "mongolog", portStr)
	if err := os.MkdirAll(filepath.Join(portDir, "db"), 0o755); err != nil {
		t.Fatalf("mkdir data: %v", err)
	}
	if err := os.MkdirAll(logPortDir, 0o755); err != nil {
		t.Fatalf("mkdir log: %v", err)
	}

	p := DeferredDeInstallConfParams{
		IP:           "127.0.0.1",
		Port:         port,
		NodeInfo:     []string{"127.0.0.1"},
		InstanceType: "mongod",
		RenameDir:    true,
	}
	if err := runMongoDeferredDeinstall(t, marshalDeferredDeInstallParams(t, p), ""); err != nil {
		t.Fatalf("Run: %v", err)
	}
	if _, err := os.Stat(portDir); !os.IsNotExist(err) {
		t.Fatalf("expected data port dir renamed away, still exists: %s", portDir)
	}
	matches, err := filepath.Glob(filepath.Join(root, "mongodata", "removed_"+portStr+"_*"))
	if err != nil || len(matches) != 1 {
		t.Fatalf("expected one renamed data dir, matches=%v err=%v", matches, err)
	}
}

func TestMongoDeferredDeinstall_InitRejectsBadInstanceType(t *testing.T) {
	p := DeferredDeInstallConfParams{
		IP:           "127.0.0.1",
		Port:         27017,
		NodeInfo:     []string{"127.0.0.1"},
		InstanceType: "invalid",
		RenameDir:    false,
	}
	err := runMongoDeferredDeinstall(t, marshalDeferredDeInstallParams(t, p), "")
	if err == nil {
		t.Fatal("expected init/run error for bad instanceType")
	}
}

func TestMongoDeferredDeinstall_Name(t *testing.T) {
	if NewDeferredDeInstall().Name() != "mongo_deferred_deinstall" {
		t.Fatalf("unexpected name %s", NewDeferredDeInstall().Name())
	}
}

func boolPtr(v bool) *bool { return &v }

func TestIsMongodRemovedAccepted(t *testing.T) {
	cases := []struct {
		name string
		in   mongodRemovedCheckResult
		want bool
	}{
		{
			name: "myState REMOVED",
			in:   mongodRemovedCheckResult{State: rsStateRemoved, StateStr: rsStateStrRemoved},
			want: true,
		},
		{
			name: "hello msg contains removed",
			in:   mongodRemovedCheckResult{Msg: "Removed from replica set"},
			want: true,
		},
		{
			name: "old isMaster invalid replica set config",
			in: mongodRemovedCheckResult{
				Msg:          "Does not have a valid replica set config",
				IsMaster:     boolPtr(false),
				Secondary:    boolPtr(false),
				IsReplicaSet: boolPtr(true),
			},
			want: true,
		},
		{
			name: "invalid config but still secondary true — reject",
			in: mongodRemovedCheckResult{
				Msg:       "Does not have a valid replica set config",
				IsMaster:  boolPtr(false),
				Secondary: boolPtr(true),
			},
			want: false,
		},
		{
			name: "state 0 empty msg — reject (ticket 493 pattern before fix)",
			in:   mongodRemovedCheckResult{State: 0, Msg: ""},
			want: false,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := isMongodRemovedAccepted(tc.in)
			if got != tc.want {
				t.Fatalf("got %v want %v for %+v", got, tc.want, tc.in)
			}
		})
	}
}
