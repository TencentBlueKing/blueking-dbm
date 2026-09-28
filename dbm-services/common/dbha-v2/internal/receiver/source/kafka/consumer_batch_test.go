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
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/sink"

	"github.com/IBM/sarama"
)

type fakeBatchSinker struct {
	mu         sync.Mutex
	calls      int
	panicOn    int
	result     sink.BatchResult
	err        error
	blockUntil <-chan struct{}
}

func (f *fakeBatchSinker) Save(msg *sink.Message) error {
	_, err := f.SaveBatch(context.Background(), []*sink.Message{msg})
	return err
}

func (f *fakeBatchSinker) SaveBatch(ctx context.Context, msgs []*sink.Message) (sink.BatchResult, error) {
	f.mu.Lock()
	f.calls++
	call := f.calls
	f.mu.Unlock()
	if f.panicOn > 0 && call == f.panicOn {
		panic("batch panic")
	}
	if f.blockUntil != nil {
		select {
		case <-f.blockUntil:
		case <-ctx.Done():
			return sink.BatchResult{Failed: len(msgs)}, ctx.Err()
		}
	}
	return f.result, f.err
}

func (f *fakeBatchSinker) Close() {}

func (f *fakeBatchSinker) callCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.calls
}

func TestFlushBatchMarksLastOffset(t *testing.T) {
	t.Parallel()
	saver := &fakeBatchSinker{}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{topic: "t", hwm: 10, messages: make(chan *sarama.ConsumerMessage, 3)}
	for i := int64(0); i < 3; i++ {
		claim.messages <- &sarama.ConsumerMessage{
			Topic: "t", Offset: i, Value: []byte("x"), Timestamp: time.Now(),
		}
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	if session.markedCount() != 1 || session.marked[0].Offset != 2 {
		t.Fatalf("expected mark offset 2, got %+v", session.marked)
	}
	if saver.callCount() != 1 {
		t.Fatalf("expected 1 SaveBatch, got %d", saver.callCount())
	}
}

func TestFlushBatchSessionEndedNoMark(t *testing.T) {
	t.Parallel()
	started := make(chan struct{})
	block := make(chan struct{})
	saver := &fakeBatchSinker{
		result:     sink.BatchResult{Invalid: 1, Failed: 1},
		blockUntil: block,
	}
	// wrap to signal start
	orig := saver
	h := &consumerHandler{savers: []sink.Sinker{orig}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{topic: "t", hwm: 10, messages: make(chan *sarama.ConsumerMessage, 1)}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("x"), Timestamp: time.Now(),
	}
	close(claim.messages)

	done := make(chan error, 1)
	go func() { done <- h.ConsumeClaim(session, claim) }()

	// wait until SaveBatch is in progress
	deadline := time.Now().Add(time.Second)
	for orig.callCount() < 1 && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	if orig.callCount() < 1 {
		close(block)
		t.Fatal("SaveBatch was not called")
	}
	_ = started
	cancel()
	close(block)

	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("ConsumeClaim did not return")
	}
	if session.markedCount() != 0 {
		t.Fatalf("expected no mark when session ended, got %d", session.markedCount())
	}
}

func TestFlushBatchPanicDegrade(t *testing.T) {
	t.Parallel()
	saver := &fakeBatchSinker{panicOn: 1}
	h := &consumerHandler{
		savers:         []sink.Sinker{saver},
		maxMessageAge:  5 * time.Minute,
		degradeTimeout: time.Second,
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{topic: "t", hwm: 10, messages: make(chan *sarama.ConsumerMessage, 2)}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("a"), Timestamp: time.Now(),
	}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 2, Value: []byte("b"), Timestamp: time.Now(),
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	// 1 batch panic + 2 single SaveBatch in degrade
	if saver.callCount() != 3 {
		t.Fatalf("expected 3 SaveBatch calls (1 panic + 2 degrade), got %d", saver.callCount())
	}
	if session.markedCount() != 1 || session.marked[0].Offset != 2 {
		t.Fatalf("expected mark offset 2, got %+v", session.marked)
	}
}
