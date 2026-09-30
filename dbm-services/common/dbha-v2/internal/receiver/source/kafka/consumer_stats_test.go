/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package kafka

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/sink"

	"github.com/IBM/sarama"
)

type recordedStats struct {
	mu     sync.Mutex
	stats  map[string]sink.WriteStats
	errors map[string]int
	calls  int
}

func newRecordedStats() *recordedStats {
	return &recordedStats{
		stats:  map[string]sink.WriteStats{},
		errors: map[string]int{},
	}
}

func (r *recordedStats) bind(h *consumerHandler) {
	h.recordStats = func(topic string, stats sink.WriteStats) {
		r.mu.Lock()
		defer r.mu.Unlock()
		merged := r.stats[topic]
		merged.Merge(stats)
		r.stats[topic] = merged
		r.calls++
	}
	h.countWriteErrors = func(topic string, n int) {
		r.mu.Lock()
		defer r.mu.Unlock()
		r.errors[topic] += n
	}
}

func (r *recordedStats) get(topic string) (sink.WriteStats, int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.stats[topic], r.errors[topic]
}

func freshMessage(topic string, offset int64) *sarama.ConsumerMessage {
	return &sarama.ConsumerMessage{
		Topic: topic, Offset: offset, Value: []byte("x"), Timestamp: time.Now(),
	}
}

func testSession() *fakeSession {
	return &fakeSession{ctx: context.Background()}
}

type writtenSinker struct {
	mu    sync.Mutex
	calls int
}

func (w *writtenSinker) Save(msg *sink.Message) error { return nil }
func (w *writtenSinker) Close()                       {}
func (w *writtenSinker) SaveBatch(_ context.Context, msgs []*sink.Message) (sink.BatchResult, error) {
	w.mu.Lock()
	w.calls++
	w.mu.Unlock()
	return sink.BatchResult{Stats: sink.WriteStats{Written: len(msgs)}}, nil
}

type topicFailSinker struct {
	mu   sync.Mutex
	fail map[string]int
}

func (s *topicFailSinker) Save(msg *sink.Message) error { return nil }
func (s *topicFailSinker) Close()                       {}
func (s *topicFailSinker) SaveBatch(_ context.Context, msgs []*sink.Message) (sink.BatchResult, error) {
	topic := msgs[0].Topic
	s.mu.Lock()
	n := s.fail[topic]
	s.mu.Unlock()
	var stats sink.WriteStats
	stats.AddDrop("mysql", sink.ReasonFatal, n)
	return sink.BatchResult{Failed: n, Stats: stats}, nil
}

type gateSinker struct {
	blockTopic string
	started    chan struct{}
	release    <-chan struct{}
	once       sync.Once
}

func (g *gateSinker) Save(msg *sink.Message) error { return nil }
func (g *gateSinker) Close()                       {}
func (g *gateSinker) SaveBatch(ctx context.Context, msgs []*sink.Message) (sink.BatchResult, error) {
	if len(msgs) > 0 && msgs[0].Topic == g.blockTopic {
		g.once.Do(func() { close(g.started) })
		select {
		case <-g.release:
		case <-ctx.Done():
			return sink.BatchResult{}, ctx.Err()
		}
	}
	return sink.BatchResult{}, nil
}

func TestFlushBatchPartitionsDoNotShareErrorCount(t *testing.T) {
	release := make(chan struct{})
	counter := &topicFailSinker{fail: map[string]int{"topic-a": 1, "topic-b": 2}}
	gate := &gateSinker{blockTopic: "topic-a", started: make(chan struct{}), release: release}
	h := &consumerHandler{savers: []sink.Sinker{counter, gate}}
	rec := newRecordedStats()
	rec.bind(h)
	claimA := &fakeClaim{topic: "topic-a", hwm: 10}
	claimB := &fakeClaim{topic: "topic-b", hwm: 10}

	done := make(chan struct{})
	go func() {
		h.flushBatch(testSession(), claimA, []*sarama.ConsumerMessage{freshMessage("topic-a", 1)})
		close(done)
	}()
	select {
	case <-gate.started:
	case <-time.After(2 * time.Second):
		t.Fatal("partition A did not reach the second sinker")
	}
	h.flushBatch(testSession(), claimB, []*sarama.ConsumerMessage{
		freshMessage("topic-b", 1), freshMessage("topic-b", 2),
	})
	close(release)
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("partition A did not finish")
	}

	statsA, errA := rec.get("topic-a")
	statsB, errB := rec.get("topic-b")
	if errA != 1 || errB != 2 {
		t.Fatalf("error counts topic-a=%d topic-b=%d", errA, errB)
	}
	if statsA.DropCount("mysql", sink.ReasonFatal) != 1 || statsB.DropCount("mysql", sink.ReasonFatal) != 2 {
		t.Fatalf("stats A=%+v B=%+v", statsA, statsB)
	}
}

func TestFlushBatchStaleRecordedOnlyWhenMarking(t *testing.T) {
	h := &consumerHandler{
		savers:        []sink.Sinker{&writtenSinker{}},
		maxMessageAge: time.Minute,
	}
	rec := newRecordedStats()
	rec.bind(h)
	stale := &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("old"), Timestamp: time.Now().Add(-time.Hour),
	}
	batch := []*sarama.ConsumerMessage{stale, freshMessage("t", 2)}
	claim := &fakeClaim{topic: "t", hwm: 5000}
	h.flushBatch(testSession(), claim, batch)
	stats, _ := rec.get("t")
	if stats.DropCount("", sink.ReasonStale) != 1 || stats.Written != 1 {
		t.Fatalf("expected stale and one write, got %+v", stats)
	}

	canceled, cancel := context.WithCancel(context.Background())
	cancel()
	skipped := newRecordedStats()
	h.recordStats = func(topic string, stats sink.WriteStats) {
		skipped.mu.Lock()
		skipped.calls++
		skipped.mu.Unlock()
	}
	h.flushBatch(&fakeSession{ctx: canceled}, claim, batch)
	if skipped.calls != 0 {
		t.Fatalf("expected no stats when the session is already done, calls=%d", skipped.calls)
	}
}

func TestFlushBatchPanicKeepsStaleAndDropsBatchStats(t *testing.T) {
	h := &consumerHandler{
		savers:         []sink.Sinker{&writtenSinker{}, &fakeBatchSinker{panicOn: 1}},
		maxMessageAge:  time.Minute,
		degradeTimeout: time.Second,
	}
	rec := newRecordedStats()
	rec.bind(h)
	stale := &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("old"), Timestamp: time.Now().Add(-time.Hour),
	}
	h.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 5000}, []*sarama.ConsumerMessage{
		stale, freshMessage("t", 2),
	})
	stats, _ := rec.get("t")
	if stats.DropCount("", sink.ReasonStale) != 1 {
		t.Fatalf("stale was lost, stats=%+v", stats)
	}
	if stats.Written != 1 {
		t.Fatalf("expected only the degrade write, written=%d stats=%+v", stats.Written, stats)
	}
	if stats.DropCount("", sink.ReasonCtxDone) != 0 {
		t.Fatalf("ctx_done must not be exported, stats=%+v", stats)
	}
}

type panicThenBlockSinker struct {
	mu    sync.Mutex
	calls int
}

func (p *panicThenBlockSinker) Save(msg *sink.Message) error { return nil }
func (p *panicThenBlockSinker) Close()                       {}
func (p *panicThenBlockSinker) SaveBatch(
	ctx context.Context, msgs []*sink.Message,
) (sink.BatchResult, error) {
	p.mu.Lock()
	p.calls++
	call := p.calls
	p.mu.Unlock()
	if call == 1 {
		panic("batch panic")
	}
	<-ctx.Done()
	var stats sink.WriteStats
	stats.AddDrop("", sink.ReasonCtxDone, len(msgs))
	return sink.BatchResult{Failed: len(msgs), Stats: stats}, ctx.Err()
}

func TestFlushBatchDegradeTimeoutAssignsRemaining(t *testing.T) {
	h := &consumerHandler{
		savers:         []sink.Sinker{&panicThenBlockSinker{}, &writtenSinker{}},
		degradeTimeout: 30 * time.Millisecond,
	}
	rec := newRecordedStats()
	rec.bind(h)
	h.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 10}, []*sarama.ConsumerMessage{
		freshMessage("t", 1), freshMessage("t", 2),
	})
	stats, _ := rec.get("t")
	if stats.DropCount("", sink.ReasonDegradeTimeout) != 4 {
		t.Fatalf("expected 4 degrade_timeout, got %+v", stats)
	}
	if stats.DropCount("", sink.ReasonCtxDone) != 0 {
		t.Fatalf("ctx_done must be rewritten, stats=%+v", stats)
	}
}

func TestFlushBatchPanicOnSaveAssignsRemainingSinkers(t *testing.T) {
	h := &consumerHandler{savers: []sink.Sinker{&fakeSinker{panicOn: 1}, &fakeSinker{}}}
	rec := newRecordedStats()
	rec.bind(h)
	h.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 10}, []*sarama.ConsumerMessage{
		freshMessage("t", 1),
	})
	stats, _ := rec.get("t")
	if stats.DropCount("", sink.ReasonPanic) != 2 {
		t.Fatalf("expected panic on both sinkers, got %+v", stats)
	}
}

func TestFlushBatchNoSinkAndPlainSave(t *testing.T) {
	rec := newRecordedStats()
	empty := &consumerHandler{}
	rec.bind(empty)
	empty.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 10}, []*sarama.ConsumerMessage{
		freshMessage("t", 1),
	})
	stats, _ := rec.get("t")
	if stats.DropCount("", sink.ReasonNoSink) != 1 {
		t.Fatalf("expected no_sink, got %+v", stats)
	}

	plain := newRecordedStats()
	failed := &consumerHandler{savers: []sink.Sinker{&fakeSinker{err: errors.New("boom")}}}
	plain.bind(failed)
	failed.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 10}, []*sarama.ConsumerMessage{
		freshMessage("t", 1),
	})
	stats, _ = plain.get("t")
	if stats.DropCount("", sink.ReasonWriteError) != 1 || stats.Written != 0 {
		t.Fatalf("expected write_error, got %+v", stats)
	}

	okRec := newRecordedStats()
	okHandler := &consumerHandler{savers: []sink.Sinker{&fakeSinker{}}}
	okRec.bind(okHandler)
	okHandler.flushBatch(testSession(), &fakeClaim{topic: "t", hwm: 10}, []*sarama.ConsumerMessage{
		freshMessage("t", 1),
	})
	stats, _ = okRec.get("t")
	if stats.Written != 1 || len(stats.Samples) != 0 || stats.DropTotal() != 0 {
		t.Fatalf("expected written without a sample, got %+v", stats)
	}
}

func TestStaleSkipTrackerRateLimit(t *testing.T) {
	claim := &fakeClaim{topic: "t", partition: 1}
	var tracker staleSkipTracker

	tracker.add(claim, 2, 10, time.Minute)
	if tracker.count != 0 || tracker.lastLogAt.IsZero() {
		t.Fatalf("first skip should log and reset, count=%d", tracker.count)
	}
	loggedAt := tracker.lastLogAt

	tracker.add(claim, 0, 11, time.Second)
	if tracker.count != 0 || !tracker.lastLogAt.Equal(loggedAt) {
		t.Fatal("zero skipped should leave the tracker unchanged")
	}

	tracker.add(claim, 3, 12, 2*time.Minute)
	if tracker.count != 3 || tracker.lastOff != 12 || !tracker.lastLogAt.Equal(loggedAt) {
		t.Fatalf("skip inside the interval should only accumulate, tracker=%+v", tracker)
	}

	tracker.lastLogAt = time.Now().Add(-staleSkipLogInterval)
	tracker.add(claim, 1, 13, 3*time.Minute)
	if tracker.count != 0 || tracker.lastOff != 13 {
		t.Fatalf("skip after the interval should log and reset, tracker=%+v", tracker)
	}
}
