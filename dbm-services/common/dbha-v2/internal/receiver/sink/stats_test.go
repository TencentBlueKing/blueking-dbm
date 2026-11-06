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

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/testutil"
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

func TestFirstSuccessUsesEarliestEndpoint(t *testing.T) {
	t.Parallel()
	t0 := time.Unix(1000, 0)
	results := [][]endpointChunkResult{{
		{rowOK: []bool{true}, rowOKAt: []time.Time{t0.Add(200 * time.Millisecond)}},
	}, {
		{rowOK: []bool{true}, rowOKAt: []time.Time{t0}},
	}}
	ok, at := firstSuccess(results, 0, 0)
	if !ok || !at.Equal(t0) {
		t.Fatalf("expected earliest success at %s, ok: %v, at: %s", t0, ok, at)
	}
}

func TestRecordWriteStatsNormalizesDbType(t *testing.T) {
	const (
		testTopic      = "topic"
		unknownDbType  = "not-a-db-type"
		mysqlDbType    = "mysql"
		dropCountWant  = 3
		delayCountWant = 1
	)

	drops := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "test_sink_drop_messages_total", Help: "test",
	}, []string{apm.MetricLabelSink, apm.MetricLabelDbType, apm.MetricLabelReason})
	delays := prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Name: "test_sink_write_delay_ms", Help: "test", Buckets: []float64{1000},
	}, []string{apm.MetricLabelSink, apm.MetricLabelDbType})

	prevDrops := apm.SinkDropMessagesTotal.ToMetric().Collector
	prevDelays := apm.SinkWriteDelayMs.ToMetric().Collector
	apm.SinkDropMessagesTotal.ToMetric().Collector = drops
	apm.SinkWriteDelayMs.ToMetric().Collector = delays
	t.Cleanup(func() {
		apm.SinkDropMessagesTotal.ToMetric().Collector = prevDrops
		apm.SinkWriteDelayMs.ToMetric().Collector = prevDelays
	})

	var stats WriteStats
	stats.AddDrop("", ReasonInvalidJSON, 1)
	stats.AddDrop(unknownDbType, ReasonFatal, 2)
	stats.AddDrop(mysqlDbType, ReasonDedup, 1)
	stats.Samples = append(stats.Samples,
		DelaySample{DbType: "", Ms: 10},
		DelaySample{DbType: unknownDbType, Ms: 20},
	)
	RecordWriteStats(testTopic, stats)

	if got := testutil.CollectAndCount(drops); got != dropCountWant {
		t.Fatalf("sink_drop_messages_total has %d series, want %d", got, dropCountWant)
	}
	unknown := haprobe.DbType("").Normalize().String()
	if got := testutil.ToFloat64(drops.WithLabelValues(testTopic, unknown, ReasonInvalidJSON)); got != 1 {
		t.Fatalf("empty db_type drop = %v, want 1", got)
	}
	if got := testutil.ToFloat64(drops.WithLabelValues(testTopic, unknown, ReasonFatal)); got != 2 {
		t.Fatalf("unknown db_type drop = %v, want 2", got)
	}
	if got := testutil.ToFloat64(drops.WithLabelValues(testTopic, mysqlDbType, ReasonDedup)); got != 1 {
		t.Fatalf("known db_type drop = %v, want 1", got)
	}
	if got := testutil.CollectAndCount(delays); got != delayCountWant {
		t.Fatalf("sink_write_delay_ms has %d series, want %d", got, delayCountWant)
	}
}
