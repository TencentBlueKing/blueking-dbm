package common

import (
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

func TestCheckMongoServiceNoProcess(t *testing.T) {
	ok, name, err := CheckMongoService(65528)
	if err != nil {
		t.Fatalf("CheckMongoService: %v", err)
	}
	if ok || name != "" {
		t.Fatalf("expected no service, got ok=%v name=%q", ok, name)
	}
}

func TestGetMongoPidAndNameByPortNoProcess(t *testing.T) {
	pid, name, err := GetMongoPidAndNameByPort(65527)
	if err != nil {
		t.Fatalf("GetMongoPidAndNameByPort: %v", err)
	}
	if pid != 0 || name != "" {
		t.Fatalf("expected pid=0, got pid=%d name=%q", pid, name)
	}
}

func TestGetMongoPidAndNameByPortNonMongo(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port

	_, _, err = GetMongoPidAndNameByPort(port)
	if err == nil {
		t.Fatal("expected error when non-mongo process occupies port")
	}
}

func TestCheckMongoServiceNonMongo(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port

	_, _, err = CheckMongoService(port)
	if err == nil {
		t.Fatal("expected error when non-mongo process occupies port")
	}
}

func TestWaitPortReleaseNoPid(t *testing.T) {
	if err := waitPortRelease(65526, 200*time.Millisecond); err != nil {
		t.Fatalf("waitPortRelease on free port: %v", err)
	}
}

func TestWaitPortReleaseTimeoutWhilePidPresent(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port

	start := time.Now()
	err = waitPortRelease(port, 300*time.Millisecond)
	if err == nil {
		t.Fatal("expected timeout while listener pid still present")
	}
	if time.Since(start) > 2*time.Second {
		t.Fatalf("waitPortRelease took too long: %v", time.Since(start))
	}
}

func TestIsRunningPidPortStandard(t *testing.T) {
	op := NewInstanceOp("127.0.0.1", 65525, "admin", "pass", testLogger())
	pid, using, err := op.IsRunning()
	if err != nil {
		t.Fatalf("IsRunning: %v", err)
	}
	if pid != 0 || using {
		t.Fatalf("expected not running, got pid=%d using=%v", pid, using)
	}

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port
	op = NewInstanceOp("127.0.0.1", port, "admin", "pass", testLogger())
	pid, using, err = op.IsRunning()
	if err != nil {
		t.Fatalf("IsRunning with listener: %v", err)
	}
	if pid <= 0 || !using {
		t.Fatalf("expected running with pid, got pid=%d using=%v", pid, using)
	}
}

func TestIsMongodLockCleanMissing(t *testing.T) {
	dir := t.TempDir()
	clean, size, err := IsMongodLockClean(dir)
	if err != nil {
		t.Fatalf("IsMongodLockClean: %v", err)
	}
	if !clean || size != 0 {
		t.Fatalf("expected clean missing lock, got clean=%v size=%d", clean, size)
	}
}

func TestIsMongodLockCleanEmptyFile(t *testing.T) {
	dir := t.TempDir()
	lockPath := filepath.Join(dir, "mongod.lock")
	if err := os.WriteFile(lockPath, nil, 0644); err != nil {
		t.Fatal(err)
	}
	clean, size, err := IsMongodLockClean(dir)
	if err != nil {
		t.Fatalf("IsMongodLockClean: %v", err)
	}
	if !clean || size != 0 {
		t.Fatalf("expected clean empty lock, got clean=%v size=%d", clean, size)
	}
}

func TestIsMongodLockCleanNonEmpty(t *testing.T) {
	dir := t.TempDir()
	lockPath := filepath.Join(dir, "mongod.lock")
	if err := os.WriteFile(lockPath, []byte("12345\n"), 0644); err != nil {
		t.Fatal(err)
	}
	clean, size, err := IsMongodLockClean(dir)
	if err != nil {
		t.Fatalf("IsMongodLockClean: %v", err)
	}
	if clean || size == 0 {
		t.Fatalf("expected dirty lock, got clean=%v size=%d", clean, size)
	}
}

func TestWaitMongodLockCleanAlreadyClean(t *testing.T) {
	dir := t.TempDir()
	if err := WaitMongodLockClean(dir, 200*time.Millisecond); err != nil {
		t.Fatalf("WaitMongodLockClean on missing lock: %v", err)
	}
	lockPath := filepath.Join(dir, "mongod.lock")
	if err := os.WriteFile(lockPath, nil, 0644); err != nil {
		t.Fatal(err)
	}
	if err := WaitMongodLockClean(dir, 200*time.Millisecond); err != nil {
		t.Fatalf("WaitMongodLockClean on empty lock: %v", err)
	}
}

func TestWaitMongodLockCleanTimeoutDirty(t *testing.T) {
	dir := t.TempDir()
	lockPath := filepath.Join(dir, "mongod.lock")
	if err := os.WriteFile(lockPath, []byte("999\n"), 0644); err != nil {
		t.Fatal(err)
	}
	start := time.Now()
	err := WaitMongodLockClean(dir, 300*time.Millisecond)
	if err == nil {
		t.Fatal("expected timeout while mongod.lock is dirty")
	}
	if time.Since(start) > 2*time.Second {
		t.Fatalf("WaitMongodLockClean took too long: %v", time.Since(start))
	}
}

func TestLockCleanWaitBudgetFloorsShortRemaining(t *testing.T) {
	cases := []struct {
		name      string
		remaining time.Duration
		want      time.Duration
	}{
		{name: "zero", remaining: 0, want: mongodLockCleanMinWait},
		{name: "negative", remaining: -time.Second, want: mongodLockCleanMinWait},
		{name: "below floor", remaining: time.Second, want: mongodLockCleanMinWait},
		{name: "at floor", remaining: mongodLockCleanMinWait, want: mongodLockCleanMinWait},
		{name: "above floor", remaining: 30 * time.Second, want: 30 * time.Second},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := lockCleanWaitBudget(tc.remaining); got != tc.want {
				t.Fatalf("lockCleanWaitBudget(%s)=%s, want %s", tc.remaining, got, tc.want)
			}
		})
	}
}

func TestResolveMongodDbPathRequiresConf(t *testing.T) {
	// Without a real mongo.conf for this port, resolve must fail (no default fallback).
	_, err := ResolveMongodDbPath(65521)
	if err == nil {
		t.Fatal("expected error when mongo.conf is missing, got nil")
	}
}

func TestResolveMongodDbPathFromConf(t *testing.T) {
	dataDir := t.TempDir()
	t.Setenv("MONGO_DATA_DIR", dataDir)
	port := 27099
	wantDbPath := filepath.Join(dataDir, "custom", "db")
	confDir := filepath.Join(dataDir, "mongodata", strconv.Itoa(port))
	if err := os.MkdirAll(confDir, 0755); err != nil {
		t.Fatal(err)
	}
	confContent := fmt.Sprintf("storage:\n  dbPath: %s\n", wantDbPath)
	if err := os.WriteFile(filepath.Join(confDir, "mongo.conf"), []byte(confContent), 0644); err != nil {
		t.Fatal(err)
	}
	got, err := ResolveMongodDbPath(port)
	if err != nil {
		t.Fatalf("ResolveMongodDbPath: %v", err)
	}
	if got != wantDbPath {
		t.Fatalf("dbPath=%q, want %q", got, wantDbPath)
	}
}

func TestResolveMongodDbPathRejectsRelative(t *testing.T) {
	dataDir := t.TempDir()
	t.Setenv("MONGO_DATA_DIR", dataDir)
	port := 27098
	confDir := filepath.Join(dataDir, "mongodata", strconv.Itoa(port))
	if err := os.MkdirAll(confDir, 0755); err != nil {
		t.Fatal(err)
	}
	confContent := "storage:\n  dbPath: relative/db\n"
	if err := os.WriteFile(filepath.Join(confDir, "mongo.conf"), []byte(confContent), 0644); err != nil {
		t.Fatal(err)
	}
	_, err := ResolveMongodDbPath(port)
	if err == nil {
		t.Fatal("expected error when dbPath is relative")
	}
}
