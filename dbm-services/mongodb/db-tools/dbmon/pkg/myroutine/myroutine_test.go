package myroutine

import (
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"go.uber.org/zap"
)

// blockingJob 在 Run 中阻塞，直到 Stop 关闭 release。
type blockingJob struct {
	started atomic.Int32
	release chan struct{}
	stop    sync.Once
}

func (j *blockingJob) Run() {
	j.started.Add(1)
	<-j.release
}

func (j *blockingJob) Stop() {
	j.stop.Do(func() { close(j.release) })
}

func TestStartAllDoesNotDoubleStart(t *testing.T) {
	p := NewPool(zap.NewNop())
	job := &blockingJob{release: make(chan struct{})}
	p.Add("a", job)

	for i := 0; i < 50; i++ {
		p.StartAll()
	}
	time.Sleep(50 * time.Millisecond)
	if got := job.started.Load(); got != 1 {
		t.Fatalf("started = %d, want 1", got)
	}

	p.Stop("a")
	waitStopped(t, p, "a")

	// release 已关闭，再次启动会马上退出，用来确认 stopped 被置回 true 后还能再跑。
	p.StartAll()
	deadline := time.Now().Add(2 * time.Second)
	for job.started.Load() < 2 && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	if got := job.started.Load(); got != 2 {
		t.Fatalf("restarted started = %d, want 2", got)
	}
	waitStopped(t, p, "a")
}

func TestRunStopRace(t *testing.T) {
	p := NewPool(zap.NewNop())
	job := &blockingJob{release: make(chan struct{})}
	p.Add("a", job)

	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for n := 0; n < 20; n++ {
				p.StartAll()
				_ = p.find("a").IsStopped()
			}
		}()
	}
	wg.Wait()
	if got := job.started.Load(); got != 1 {
		t.Fatalf("started = %d, want 1", got)
	}
	p.StopAll()
	waitStopped(t, p, "a")
}

func waitStopped(t *testing.T, p *Pool, name string) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		r := p.find(name)
		if r != nil && r.IsStopped() {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("routine %s did not stop", name)
}
