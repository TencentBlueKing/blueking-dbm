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

package sink

import (
	"math"
	"testing"
	"time"
)

func TestDelayMillisSkipsUnusableTimestamps(t *testing.T) {
	t.Parallel()
	at := time.Unix(1000, 0)
	if _, ok := DelayMillis(at, 0); ok {
		t.Fatal("expected zero timestamp to be skipped")
	}
	if _, ok := DelayMillis(at, uint64(math.MaxInt64/1000)+1); ok {
		t.Fatal("expected overflowing timestamp to be skipped")
	}
	if _, ok := DelayMillis(at, 1001); ok {
		t.Fatal("expected future timestamp to be skipped")
	}
	ms, ok := DelayMillis(at, 990)
	if !ok || ms != 10000 {
		t.Fatalf("expected 10000ms, ok=%v ms=%v", ok, ms)
	}
}

func TestExportDropsSkipsCtxDone(t *testing.T) {
	t.Parallel()
	var stats WriteStats
	stats.AddDrop("mysql", ReasonCtxDone, 2)
	stats.AddDrop("mysql", ReasonFatal, 1)
	items, ignored := stats.exportDrops()
	if ignored != 2 {
		t.Fatalf("expected ignored ctx_done=2, got %d", ignored)
	}
	if len(items) != 1 || items[0].reason != ReasonFatal || items[0].n != 1 {
		t.Fatalf("unexpected exported drops: %+v", items)
	}
}

func TestRewriteCtxDone(t *testing.T) {
	t.Parallel()
	var stats WriteStats
	stats.AddDrop("redis", ReasonCtxDone, 3)
	stats.Written = 1
	out := RewriteCtxDone(stats, ReasonDegradeTimeout)
	if out.DropCount("redis", ReasonCtxDone) != 0 {
		t.Fatal("ctx_done should be rewritten")
	}
	if out.DropCount("redis", ReasonDegradeTimeout) != 3 || out.Written != 1 {
		t.Fatalf("unexpected rewrite: written=%d drops=%d", out.Written, out.DropTotal())
	}
}

func TestEarliestEndpointSample(t *testing.T) {
	t.Parallel()
	t0 := time.Unix(1000, 0)
	results := [][]endpointChunkResult{{
		{rowOK: []bool{true}, rowOKAt: []time.Time{t0}},
	}, {
		{rowOK: []bool{true}, rowOKAt: []time.Time{t0.Add(200 * time.Millisecond)}},
	}}
	ms, ok := sampleMillis(results, 0, 0, 990)
	if !ok || ms != 10000 {
		t.Fatalf("expected earliest sample 10000ms, ok=%v ms=%v", ok, ms)
	}
}
