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
	"context"
	"testing"

	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/proto"
)

func captureProbeStats(ch *connectionHandler) *[]sink.WriteStats {
	got := &[]sink.WriteStats{}
	ch.recordStats = func(topic string, stats sink.WriteStats) {
		if topic != SinkMessageTopic {
			panic("unexpected topic " + topic)
		}
		*got = append(*got, stats)
	}
	return got
}

func TestReadEventNoSinkBeforeEmpty(t *testing.T) {
	ch := &connectionHandler{eventC: make(chan *proto.ReceiverRequest, 1)}
	got := captureProbeStats(ch)
	ch.eventC <- &proto.ReceiverRequest{Payload: []byte{}}
	close(ch.eventC)
	ch.readEvent()
	if len(*got) != 1 || (*got)[0].DropCount("", sink.ReasonNoSink) != 1 {
		t.Fatalf("expected no_sink ahead of empty, got %+v", *got)
	}
}

func TestReadEventEmptyPayload(t *testing.T) {
	ch := &connectionHandler{
		savers: []sink.Sinker{&fakeSinker{}},
		eventC: make(chan *proto.ReceiverRequest, 1),
	}
	got := captureProbeStats(ch)
	ch.eventC <- &proto.ReceiverRequest{Payload: []byte{}}
	close(ch.eventC)
	ch.readEvent()
	if len(*got) != 1 || (*got)[0].DropCount("", sink.ReasonEmpty) != 1 {
		t.Fatalf("expected empty, got %+v", *got)
	}
}

func TestPushDataUnaryQueueFull(t *testing.T) {
	ch := &connectionHandler{eventC: make(chan *proto.ReceiverRequest, 1)}
	got := captureProbeStats(ch)
	ch.eventC <- &proto.ReceiverRequest{Payload: []byte("1")}
	p := &Probe{connHandler: ch}
	if _, err := p.PushDataUnary(context.Background(), &proto.ReceiverRequest{Payload: []byte("2")}); err != nil {
		t.Fatalf("PushDataUnary failed, errmsg: %s", err)
	}
	if len(*got) != 1 || (*got)[0].DropCount("", sink.ReasonQueueFull) != 1 {
		t.Fatalf("expected queue_full, got %+v", *got)
	}
}
