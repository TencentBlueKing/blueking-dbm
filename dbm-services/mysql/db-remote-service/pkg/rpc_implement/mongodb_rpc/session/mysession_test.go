package session

import (
	"io"
	"log/slog"
	"testing"
	"time"
)

func testLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func TestIsTimeoutZeroLastRunTime(t *testing.T) {
	s := &MySession{}
	if s.IsTimeout(1) {
		t.Fatal("zero LastRunTime must not be treated as idle timeout")
	}
}

func TestStopNilJob(t *testing.T) {
	s := &MySession{logger: testLogger()}
	s.Stop()
}

func TestSweepTimeoutNilJob(t *testing.T) {
	p := NewPool(testLogger())
	s := p.Add("idle")
	s.LastRunTime = time.Now().Add(-2 * time.Hour)
	stopped, running := p.sweepTimeout(3600)
	if running != 0 {
		t.Fatalf("running=%d", running)
	}
	if len(stopped) != 1 || stopped[0] != "idle" {
		t.Fatalf("stopped=%v", stopped)
	}
	if p.find("idle") != nil {
		t.Fatal("idle session should be removed")
	}
}

func TestSweepTimeoutSkipsFreshSession(t *testing.T) {
	p := NewPool(testLogger())
	s := p.Add("fresh")
	if s.LastRunTime.IsZero() {
		t.Fatal("Add should set LastRunTime")
	}
	stopped, running := p.sweepTimeout(3600)
	if len(stopped) != 0 {
		t.Fatalf("fresh session reaped: %v", stopped)
	}
	if running != 1 {
		t.Fatalf("running=%d", running)
	}
}
