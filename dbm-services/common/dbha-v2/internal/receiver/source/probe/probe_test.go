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

package probe

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/proto"
)

// fakeSinker records all messages it receives.
type fakeSinker struct {
	mu       sync.Mutex
	messages []*sink.Message
}

// errorSinker simulates save errors.
type errorSinker struct{}

type sleepSinker struct{}

func (f *fakeSinker) Save(ctx context.Context, msg *sink.Message) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.messages = append(f.messages, msg)
	return nil
}

func (f *fakeSinker) Close() {}

func (f *fakeSinker) count() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.messages)
}

func (f *fakeSinker) getData(index int) []byte {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.messages[index].Data
}

func (e *errorSinker) Save(ctx context.Context, msg *sink.Message) error {
	return fmt.Errorf("injected failure")
}
func (e *errorSinker) Close() {}

func (s *sleepSinker) Save(ctx context.Context, msg *sink.Message) error {
	select {
	case <-time.After(12 * time.Second):
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

func (s *sleepSinker) Close() {}

func prepareServerAndClient(t *testing.T) (*Probe, *client.ReceiverClient) {
	t.Helper()

	ctx := context.Background()

	listen, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed: %v", err)
	}
	endpoint := listen.Addr().String()
	listen.Close()

	cfg := config.SourceConfig{
		Name:      "probe",
		Enable:    true,
		Endpoints: endpoint,
	}

	probe, err := NewProbeServer(cfg)
	if err != nil {
		t.Fatalf("NewProbeServer failed: %v", err)
	}

	cli, err := client.NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("NewReceiverClient failed: %v", err)
	}

	return probe, cli
}

func prepareConnectionHandler(bufferSize int) (*connectionHandler, *fakeSinker) {
	fs := &fakeSinker{}
	ch := &connectionHandler{
		savers:     []sink.Sinker{fs},
		bufferSize: bufferSize,
		eventC:     make(requestEventC, bufferSize),
	}
	return ch, fs
}

func TestHarvestWithProbe(t *testing.T) {
	probe, cli := prepareServerAndClient(t)
	defer func() {
		probe.Close()
		cli.Close()
	}()

	fs := &fakeSinker{}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	err := probe.Harvest(ctx, []sink.Sinker{fs})
	if err != nil {
		t.Fatalf("Harvest failed: %v", err)
	}

	payload := []byte(`{"hello":"world"}`)
	if err := cli.Post(ctx, payload); err != nil {
		t.Fatalf("Post failed: %v", err)
	}

	ticker1 := time.NewTicker(500 * time.Millisecond)
	ticker2 := time.NewTicker(3 * time.Second)

	for {
		select {
		case <-ticker1.C:
			if fs.count() > 0 {
				msg := fs.getData(0)
				if !bytes.Equal(msg, payload) {
					t.Fatalf("sinker data = %s, want %s", msg, payload)
				}
				return
			}
		case <-ticker2.C:
			t.Fatal("failed to save data, time exceeded")
			return
		}
	}
}

func TestConnHandlerSuccess(t *testing.T) {
	ch, fs := prepareConnectionHandler(3)
	defer ch.close()

	req := &proto.ReceiverRequest{
		Payload: []byte(`{"hello":"world"}`),
	}

	err := ch.postEvent(req)
	if err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	go ch.readEvent()

	time.Sleep(3 * time.Second)

	msg := fs.getData(0)
	if !bytes.Equal(msg, req.Payload) {
		t.Fatalf("sinker data = %s, want %s", msg, req.Payload)
	}
}

func TestQueueFull(t *testing.T) {
	ch, _ := prepareConnectionHandler(1)
	defer ch.close()

	err := ch.postEvent(&proto.ReceiverRequest{Payload: []byte("1")})
	if err != nil {
		t.Fatalf("first post should succeed: %v", err)
	}

	err = ch.postEvent(&proto.ReceiverRequest{Payload: []byte("2")})
	if err == nil {
		t.Fatal("second post should fail with queue full")
	}
}

func TestSinkerBroadCast(t *testing.T) {
	probe, cli := prepareServerAndClient(t)
	defer func() {
		probe.Close()
		cli.Close()
	}()

	sinkers := make([]sink.Sinker, 3)
	fakes := make([]*fakeSinker, 3)

	for i := 0; i < 3; i++ {
		fakes[i] = &fakeSinker{}
		sinkers[i] = fakes[i]
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := probe.Harvest(ctx, sinkers); err != nil {
		t.Fatalf("Harvest failed: %v", err)
	}

	if err := cli.Post(ctx, []byte(`{"hello":"world"}`)); err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	time.Sleep(3 * time.Second)

	count := 0
	for _, fs := range fakes {
		count += fs.count()
	}
	if count != 3 {
		t.Fatalf("failed to send messages to all sinkers: expect 3, got %d", count)
	}
}

func TestSinkerIndependency(t *testing.T) {
	probe, cli := prepareServerAndClient(t)
	defer func() {
		probe.Close()
		cli.Close()
	}()

	sinkers := make([]sink.Sinker, 3)
	var targetFs *fakeSinker
	for i := 0; i < 3; i++ {
		if i == 1 {
			targetFs = &fakeSinker{}
			sinkers[i] = targetFs
			continue
		}
		sinkers[i] = &errorSinker{}
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := probe.Harvest(ctx, sinkers); err != nil {
		t.Fatalf("Harvest failed: %v", err)
	}

	if err := cli.Post(ctx, []byte(`{"hello":"world"}`)); err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	time.Sleep(3 * time.Second)

	if targetFs.count() != 1 {
		t.Fatal("failed to save message, affected by error sinkers")
	}
}

func TestSpecialPayload(t *testing.T) {
	probe, cli := prepareServerAndClient(t)
	defer func() {
		probe.Close()
		cli.Close()
	}()

	fs := &fakeSinker{}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := probe.Harvest(ctx, []sink.Sinker{fs}); err != nil {
		t.Fatalf("Harvest failed: %v", err)
	}

	// test empty payload
	if err := cli.Post(ctx, []byte{}); err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	time.Sleep(3 * time.Second)

	if fs.count() != 0 {
		t.Fatal("failed to drop empty messgae")
	}

	// test large payload
	bigPayload := make([]byte, 3*1024*1024)
	if err := cli.Post(ctx, bigPayload); err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	time.Sleep(3 * time.Second)

	if fs.count() != 1 {
		t.Fatal("big payload not received")
	}

	data := fs.getData(0)
	length := len(data)
	if length != 3*1024*1024 {
		t.Fatalf("error in big payload, expect 3MB, got %.2f MB", float64(length)/float64(1024*1024))
	}
}

func TestSinkerSaveTimeout(t *testing.T) {
	ss := &sleepSinker{}
	fs := &fakeSinker{}
	ch := &connectionHandler{
		savers: []sink.Sinker{ss, fs},
		eventC: make(requestEventC, 3),
	}
	defer ch.close()

	req := &proto.ReceiverRequest{
		Payload: []byte(`{"hello":"world"}`),
	}

	err := ch.postEvent(req)
	if err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}

	go ch.readEvent()

	time.Sleep(12 * time.Second)

	if fs.count() != 1 {
		t.Fatalf("fakeSinker should still receive msg after sleepSinker timeout, got %d", fs.count())
	}
}
