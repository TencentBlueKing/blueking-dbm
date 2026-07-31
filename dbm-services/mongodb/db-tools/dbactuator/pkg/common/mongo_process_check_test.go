package common

import (
	"net"
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
