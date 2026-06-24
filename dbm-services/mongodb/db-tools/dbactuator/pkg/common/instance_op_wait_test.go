package common

import (
	"dbm-services/common/go-pubpkg/logger"
	"net"
	"os"
	"testing"
	"time"
)

func testLogger() *logger.Logger {
	return logger.New(os.Stdout, true, logger.InfoLevel)
}

func TestWaitPortReleaseWithDeadlineTimesOut(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port

	op := NewInstanceOp("127.0.0.1", port, "admin", "pass", testLogger())
	deadline := time.Now().Add(150 * time.Millisecond)
	start := time.Now()
	err = op.waitPortReleaseWithDeadline(10, 50*time.Millisecond, deadline, true)
	if err == nil {
		t.Fatal("expected timeout error")
	}
	if time.Since(start) > 2*time.Second {
		t.Fatalf("waitPortReleaseWithDeadline took too long: %v", time.Since(start))
	}
}

func TestDoStopWithOptionsNoListenerReturnsNil(t *testing.T) {
	op := NewInstanceOp("127.0.0.1", 65530, "admin", "pass", testLogger())
	err := op.DoStopWithOptions(StopOptions{Graceful: false, Timeout: time.Second})
	if err != nil {
		t.Fatalf("unexpected error when port has no listener: %v", err)
	}
}
