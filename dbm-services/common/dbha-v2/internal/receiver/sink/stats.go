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
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	// ReasonStale is a Kafka message skipped because it is older than the max age.
	ReasonStale = "stale"
	// ReasonNoSink means the message had no sinker to write to.
	ReasonNoSink = "no_sink"
	// ReasonEmpty is an empty probe payload.
	ReasonEmpty = "empty"
	// ReasonQueueFull means the probe ingest queue rejected the message.
	ReasonQueueFull = "queue_full"
	// ReasonSinkClosed means the sink was already closed.
	ReasonSinkClosed = "sink_closed"
	// ReasonInvalidJSON means the payload was not valid JSON.
	ReasonInvalidJSON = "invalid_json"
	// ReasonUnknownType means harvest_type is not a known value.
	ReasonUnknownType = "unknown_type"
	// ReasonDedup means a later message in the same batch replaced this one.
	ReasonDedup = "dedup"
	// ReasonDataError means every endpoint rejected the row as a data error.
	ReasonDataError = "data_error"
	// ReasonRetryTimeout means retries ended before the row was written.
	ReasonRetryTimeout = "retry_timeout"
	// ReasonFatal means an endpoint returned an error that stops the batch.
	ReasonFatal = "fatal"
	// ReasonWriteError means a non-batch Save failed, or Save failed for a non-data error.
	ReasonWriteError = "write_error"
	// ReasonDegradeTimeout means the per-message degrade write timed out.
	ReasonDegradeTimeout = "degrade_timeout"
	// ReasonPanic means a per-message write panicked before this sinker ran.
	ReasonPanic = "panic"
	// ReasonCtxDone is internal to SaveBatch. RecordWriteStats does not export it.
	ReasonCtxDone = "ctx_done"
)

// DelaySample is one successful write measured from report_timestamp.
type DelaySample struct {
	DbType string
	Ms     float64
}

type dropKey struct {
	dbType string
	reason string
}

type dropItem struct {
	dbType string
	reason string
	n      int
}

// WriteStats is the per-sinker outcome of one batch or one message.
// Written plus the drop total equals the input message count for SaveBatch.
type WriteStats struct {
	Written int
	Samples []DelaySample
	drops   map[dropKey]int
}

// AddDrop adds n messages dropped for dbType and reason.
func (st *WriteStats) AddDrop(dbType, reason string, n int) {
	if st == nil || n <= 0 {
		return
	}
	if st.drops == nil {
		st.drops = make(map[dropKey]int)
	}
	st.drops[dropKey{dbType: dbType, reason: reason}] += n
}

// DropCount returns how many messages were dropped for dbType and reason.
func (st WriteStats) DropCount(dbType, reason string) int {
	if st.drops == nil {
		return 0
	}
	return st.drops[dropKey{dbType: dbType, reason: reason}]
}

// DropTotal returns the number of dropped messages.
func (st WriteStats) DropTotal() int {
	total := 0
	for _, n := range st.drops {
		total += n
	}
	return total
}

// Merge adds other into st.
func (st *WriteStats) Merge(other WriteStats) {
	if st == nil {
		return
	}
	st.Written += other.Written
	if len(other.Samples) > 0 {
		st.Samples = append(st.Samples, other.Samples...)
	}
	for key, n := range other.drops {
		st.AddDrop(key.dbType, key.reason, n)
	}
}

// exportDrops lists drops that can be published. ctx_done is counted separately and not exported.
func (st WriteStats) exportDrops() (items []dropItem, ignoredCtx int) {
	for key, n := range st.drops {
		if key.reason == ReasonCtxDone {
			ignoredCtx += n
			continue
		}
		items = append(items, dropItem{dbType: key.dbType, reason: key.reason, n: n})
	}
	return items, ignoredCtx
}

// RewriteCtxDone copies st, replacing ctx_done with to.
func RewriteCtxDone(st WriteStats, to string) WriteStats {
	out := WriteStats{Written: st.Written}
	if len(st.Samples) > 0 {
		out.Samples = append([]DelaySample(nil), st.Samples...)
	}
	for key, n := range st.drops {
		reason := key.reason
		if reason == ReasonCtxDone {
			reason = to
		}
		out.AddDrop(key.dbType, reason, n)
	}
	return out
}

// RecordWriteStats publishes stats on the sink delay and drop metrics.
// reason ctx_done is ignored so it never becomes a label value.
func RecordWriteStats(topic string, stats WriteStats) {
	observeDelaySamples(topic, stats.Samples)
	items, ignored := stats.exportDrops()
	if ignored > 0 {
		logger.Warn("ignore unpublished sink drop, reason: %s, count: %d", ReasonCtxDone, ignored)
	}
	if apm.SinkDropMessagesTotal == nil {
		return
	}
	for _, item := range items {
		err := apm.SinkDropMessagesTotal.AddWithLabels(map[string]string{
			apm.MetricLabelSink:   topic,
			apm.MetricLabelDbType: item.dbType,
			apm.MetricLabelReason: item.reason,
		}, float64(item.n))
		if err != nil {
			logger.Warn("update sink drop messages metric failed, errmsg: %s", err)
		}
	}
}

func observeDelaySamples(topic string, samples []DelaySample) {
	if len(samples) == 0 || apm.SinkWriteDelayMs == nil {
		return
	}
	grouped := make(map[string][]float64)
	for _, sample := range samples {
		grouped[sample.DbType] = append(grouped[sample.DbType], sample.Ms)
	}
	for dbType, values := range grouped {
		bound := apm.SinkWriteDelayMs.WithLabels(map[string]string{
			apm.MetricLabelSink:   topic,
			apm.MetricLabelDbType: dbType,
		})
		for _, ms := range values {
			if err := bound.Observe(ms); err != nil {
				logger.Warn("observe sink write delay failed, errmsg: %s", err)
			}
		}
	}
}

// DelayMillis converts a success time and a unix-second report_timestamp into milliseconds.
// It returns false when the timestamp is missing, would overflow, or is in the future.
func DelayMillis(at time.Time, reportTs uint64) (float64, bool) {
	if at.IsZero() || reportTs == 0 || reportTs > math.MaxInt64/1000 {
		return 0, false
	}
	ms := at.UnixMilli() - int64(reportTs)*1000
	if ms < 0 {
		return 0, false
	}
	return float64(ms), true
}
