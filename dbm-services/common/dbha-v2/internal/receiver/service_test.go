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

package receiver

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/internal/receiver/source"
)

type fakeInputter struct {
	closeStarted chan struct{}
	releaseClose chan struct{}
	closed       atomic.Bool
}

func (f *fakeInputter) Harvest(context.Context, []sink.Sinker) error { return nil }

func (f *fakeInputter) Close() {
	if f.closeStarted != nil {
		select {
		case <-f.closeStarted:
		default:
			close(f.closeStarted)
		}
	}
	if f.releaseClose != nil {
		<-f.releaseClose
	}
	f.closed.Store(true)
}

var _ source.Inputter = (*fakeInputter)(nil)

type orderSinker struct {
	sourceClosed *atomic.Bool
	sawSourceOk  atomic.Bool
	closed       atomic.Bool
}

func (o *orderSinker) Save(*sink.Message) error { return nil }

func (o *orderSinker) Close() {
	if o.sourceClosed.Load() {
		o.sawSourceOk.Store(true)
	}
	o.closed.Store(true)
}

func TestCloseSourcesBeforeSinks(t *testing.T) {
	t.Parallel()
	src := &fakeInputter{
		closeStarted: make(chan struct{}),
		releaseClose: make(chan struct{}),
	}
	sk := &orderSinker{sourceClosed: &src.closed}

	svc := &Service{
		quit:    make(chan struct{}),
		sources: []source.Inputter{src},
		sinkers: []sink.Sinker{sk},
	}

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		svc.Close()
	}()

	select {
	case <-src.closeStarted:
	case <-time.After(time.Second):
		t.Fatal("source Close not started")
	}

	time.Sleep(50 * time.Millisecond)
	if sk.closed.Load() {
		t.Fatal("sink closed before source finished")
	}

	close(src.releaseClose)
	wg.Wait()

	if !sk.closed.Load() {
		t.Fatal("sink was not closed")
	}
	if !sk.sawSourceOk.Load() {
		t.Fatal("sink closed before source reported closed")
	}
}
