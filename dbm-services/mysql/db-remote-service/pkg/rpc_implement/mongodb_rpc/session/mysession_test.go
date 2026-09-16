package session

import (
	"io"
	"log/slog"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type blockingStartJob struct {
	entered   chan struct{}
	release   chan struct{}
	runUntil  chan struct{}
	stopCount atomic.Int32
	stopOnce  sync.Once
	started   atomic.Bool
}

func (j *blockingStartJob) Run(startWg *sync.WaitGroup, _ *slog.Logger) error {
	close(j.entered)
	<-j.release
	j.started.Store(true)
	startWg.Done()
	<-j.runUntil
	return nil
}

func (j *blockingStartJob) Stop() {
	j.stopCount.Add(1)
	j.stopOnce.Do(func() { close(j.runUntil) })
}

func (j *blockingStartJob) SendMsg([]byte) (int, error)      { return 0, nil }
func (j *blockingStartJob) ReceiveMsg(int64) ([]byte, error) { return nil, nil }

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

func TestStopWaitsUntilJobStarted(t *testing.T) {
	p := NewPool(testLogger())
	s := p.Add("starting")
	j := &blockingStartJob{
		entered:  make(chan struct{}),
		release:  make(chan struct{}),
		runUntil: make(chan struct{}),
	}

	runErr := make(chan error, 1)
	go func() { runErr <- s.Run(j) }()
	<-j.entered

	stopDone := make(chan struct{})
	go func() {
		s.Stop()
		close(stopDone)
	}()

	select {
	case <-stopDone:
		t.Fatal("Stop returned before start finished")
	case <-time.After(50 * time.Millisecond):
	}
	if j.started.Load() {
		t.Fatal("job should not have started while Stop is waiting")
	}
	if j.stopCount.Load() != 0 {
		t.Fatal("Stop must not kill the job before start completes")
	}

	close(j.release)
	if err := <-runErr; err != nil {
		t.Fatalf("Run: %v", err)
	}
	select {
	case <-stopDone:
	case <-time.After(2 * time.Second):
		t.Fatal("Stop did not return after start")
	}
	if !j.started.Load() {
		t.Fatal("job should have started before Stop")
	}
	if j.stopCount.Load() < 1 {
		t.Fatal("Stop should run after start")
	}
}
