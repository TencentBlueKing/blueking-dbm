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

type fakeSinker struct {
	mu       sync.Mutex
	calls    int
	err      error
	panicOn  int
	messages []*sink.Message
}

func (f *fakeSinker) Save(msg *sink.Message) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.calls++
	if f.panicOn > 0 && f.calls == f.panicOn {
		panic("save panic")
	}
	cp := &sink.Message{Topic: msg.Topic, Data: append([]byte(nil), msg.Data...)}
	f.messages = append(f.messages, cp)
	return f.err
}

func (f *fakeSinker) Close() {}

func (f *fakeSinker) callCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.calls
}

type fakeSession struct {
	ctx        context.Context
	marked     []*sarama.ConsumerMessage
	markMu     sync.Mutex
	generation int32
	memberID   string
	claims     map[string][]int32
}

func (s *fakeSession) Claims() map[string][]int32 { return s.claims }
func (s *fakeSession) MemberID() string           { return s.memberID }
func (s *fakeSession) GenerationID() int32        { return s.generation }
func (s *fakeSession) MarkOffset(string, int32, int64, string) {
}
func (s *fakeSession) Commit()                                  {}
func (s *fakeSession) ResetOffset(string, int32, int64, string) {}
func (s *fakeSession) MarkMessage(msg *sarama.ConsumerMessage, _ string) {
	s.markMu.Lock()
	defer s.markMu.Unlock()
	s.marked = append(s.marked, msg)
}
func (s *fakeSession) Context() context.Context { return s.ctx }

func (s *fakeSession) markedCount() int {
	s.markMu.Lock()
	defer s.markMu.Unlock()
	return len(s.marked)
}

type fakeClaim struct {
	topic     string
	partition int32
	hwm       int64
	messages  chan *sarama.ConsumerMessage
}

func (c *fakeClaim) Topic() string                            { return c.topic }
func (c *fakeClaim) Partition() int32                         { return c.partition }
func (c *fakeClaim) InitialOffset() int64                     { return 0 }
func (c *fakeClaim) HighWaterMarkOffset() int64               { return c.hwm }
func (c *fakeClaim) Messages() <-chan *sarama.ConsumerMessage { return c.messages }

func TestConsumeClaimMarksMessages(t *testing.T) {
	saver := &fakeSinker{}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{
		topic:     "t",
		partition: 0,
		hwm:       10,
		messages:  make(chan *sarama.ConsumerMessage, 3),
	}

	for i := int64(0); i < 3; i++ {
		claim.messages <- &sarama.ConsumerMessage{
			Topic:     "t",
			Partition: 0,
			Offset:    i,
			Value:     []byte("x"),
			Timestamp: time.Now(),
		}
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	if session.markedCount() != 3 {
		t.Fatalf("expected 3 marks, got: %d", session.markedCount())
	}
	if saver.callCount() != 3 {
		t.Fatalf("expected 3 saves, got: %d", saver.callCount())
	}
}

func TestConsumeClaimMarksOnSaveError(t *testing.T) {
	saver := &fakeSinker{err: errors.New("save failed")}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{topic: "t", hwm: 10, messages: make(chan *sarama.ConsumerMessage, 1)}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("x"), Timestamp: time.Now(),
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	if session.markedCount() != 1 {
		t.Fatalf("expected mark on save error, got: %d", session.markedCount())
	}
}

func TestConsumeClaimMarksOnPanic(t *testing.T) {
	saver := &fakeSinker{panicOn: 1}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
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
	if session.markedCount() != 2 {
		t.Fatalf("expected both messages marked after panic, got: %d", session.markedCount())
	}
	if saver.callCount() != 2 {
		t.Fatalf("expected second message still processed, saves: %d", saver.callCount())
	}
}

func TestConsumeClaimReturnsOnSessionCancel(t *testing.T) {
	saver := &fakeSinker{}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{topic: "t", hwm: 10, messages: make(chan *sarama.ConsumerMessage, 2)}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("a"), Timestamp: time.Now(),
	}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 2, Value: []byte("b"), Timestamp: time.Now(),
	}

	done := make(chan error, 1)
	go func() {
		done <- h.ConsumeClaim(session, claim)
	}()

	deadline := time.Now().Add(time.Second)
	for saver.callCount() < 1 && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	cancel()

	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
		}
	case <-time.After(time.Second):
		t.Fatal("ConsumeClaim did not return after session cancel")
	}
}

func TestConsumeClaimSkipsStaleWithBacklog(t *testing.T) {
	saver := &fakeSinker{}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{
		topic: "t", partition: 1, hwm: 2000,
		messages: make(chan *sarama.ConsumerMessage, 1),
	}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Partition: 1, Offset: 1, Value: []byte("old"),
		Timestamp: time.Now().Add(-10 * time.Minute),
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	if saver.callCount() != 0 {
		t.Fatalf("expected stale message skipped, saves: %d", saver.callCount())
	}
	if session.markedCount() != 1 {
		t.Fatalf("expected stale message marked, marks: %d", session.markedCount())
	}
}

func TestConsumeClaimKeepsStaleWithoutBacklog(t *testing.T) {
	saver := &fakeSinker{}
	h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: 5 * time.Minute}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	session := &fakeSession{ctx: ctx}
	claim := &fakeClaim{
		topic: "t", hwm: 10,
		messages: make(chan *sarama.ConsumerMessage, 1),
	}
	claim.messages <- &sarama.ConsumerMessage{
		Topic: "t", Offset: 1, Value: []byte("skew"),
		Timestamp: time.Now().Add(-10 * time.Minute),
	}
	close(claim.messages)

	if err := h.ConsumeClaim(session, claim); err != nil {
		t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
	}
	if saver.callCount() != 1 {
		t.Fatalf("expected write when backlog is small, saves: %d", saver.callCount())
	}
}

func TestConsumeClaimKeepsZeroTimestampAndDisabledFilter(t *testing.T) {
	cases := []struct {
		name          string
		maxMessageAge time.Duration
		timestamp     time.Time
	}{
		{name: "zero timestamp", maxMessageAge: 5 * time.Minute},
		{name: "filter disabled", maxMessageAge: -1, timestamp: time.Now().Add(-10 * time.Minute)},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			saver := &fakeSinker{}
			h := &consumerHandler{savers: []sink.Sinker{saver}, maxMessageAge: tc.maxMessageAge}
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			session := &fakeSession{ctx: ctx}
			claim := &fakeClaim{
				topic: "t", hwm: 2000,
				messages: make(chan *sarama.ConsumerMessage, 1),
			}
			claim.messages <- &sarama.ConsumerMessage{
				Topic: "t", Offset: 1, Value: []byte("x"), Timestamp: tc.timestamp,
			}
			close(claim.messages)

			if err := h.ConsumeClaim(session, claim); err != nil {
				t.Fatalf("ConsumeClaim failed, errmsg: %s", err)
			}
			if saver.callCount() != 1 {
				t.Fatalf("expected message saved, saves: %d", saver.callCount())
			}
		})
	}
}

func TestShouldSkipStale(t *testing.T) {
	h := &consumerHandler{maxMessageAge: 5 * time.Minute}
	msg := &sarama.ConsumerMessage{
		Offset:    1,
		Timestamp: time.Now().Add(-10 * time.Minute),
	}
	if !h.shouldSkipStale(msg, 2000) {
		t.Fatal("expected skip with backlog")
	}
	if h.shouldSkipStale(msg, 10) {
		t.Fatal("expected no skip without backlog")
	}
}
