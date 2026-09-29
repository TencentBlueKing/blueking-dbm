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
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"

	"github.com/IBM/sarama"
)

const (
	defaultBatchSize         = 500
	defaultBatchMaxBytes     = 4 << 20 // 4MB
	defaultDegradeTimeout    = 30 * time.Second
	defaultChannelBufferSize = 256
	defaultMaxProcessingTime = time.Second
)

var flushBatchLabel = safe.WithLabel("kafka-flush-batch")

// staleSkipTracker accumulates skipped stale messages and logs them at most once per interval.
type staleSkipTracker struct {
	count     int
	lastOff   int64
	lastAge   time.Duration
	lastLogAt time.Time
}

func (t *staleSkipTracker) add(claim sarama.ConsumerGroupClaim, skipped int, off int64, age time.Duration) {
	if skipped <= 0 {
		return
	}
	t.count += skipped
	t.lastOff = off
	t.lastAge = age
	if !t.lastLogAt.IsZero() && time.Since(t.lastLogAt) < staleSkipLogInterval {
		return
	}
	if flushStaleSkipLog(claim, t.count, t.lastOff, t.lastAge) {
		t.count = 0
		t.lastLogAt = time.Now()
	}
}

func (t *staleSkipTracker) flush(claim sarama.ConsumerGroupClaim) {
	flushStaleSkipLog(claim, t.count, t.lastOff, t.lastAge)
}

func (h *consumerHandler) consumeClaimBatched(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
) error {
	var stale staleSkipTracker
	messages := claim.Messages()
	for {
		select {
		case <-session.Context().Done():
			stale.flush(claim)
			return nil
		case first, ok := <-messages:
			if !ok {
				stale.flush(claim)
				return nil
			}
			batch := h.drainBatch(session.Context(), messages, first)
			if len(batch) == 0 {
				continue
			}
			skipped, lastOff, lastAge := h.flushBatch(session, claim, batch)
			stale.add(claim, skipped, lastOff, lastAge)
			if session.Context().Err() != nil {
				stale.flush(claim)
				return nil
			}
		}
	}
}

func (h *consumerHandler) drainBatch(
	sessionCtx context.Context,
	messages <-chan *sarama.ConsumerMessage,
	first *sarama.ConsumerMessage,
) []*sarama.ConsumerMessage {
	batchSize := h.batchSize
	if batchSize <= 0 {
		batchSize = defaultBatchSize
	}
	batchMaxBytes := h.batchMaxBytes
	if batchMaxBytes <= 0 {
		batchMaxBytes = defaultBatchMaxBytes
	}

	batch := []*sarama.ConsumerMessage{first}
	totalBytes := len(first.Value)

	for len(batch) < batchSize && totalBytes < batchMaxBytes {
		select {
		case <-sessionCtx.Done():
			return nil
		case msg, ok := <-messages:
			if !ok {
				return batch
			}
			batch = append(batch, msg)
			totalBytes += len(msg.Value)
		default:
			if h.batchLinger <= 0 {
				return batch
			}
			return h.drainWithLinger(sessionCtx, messages, batch, batchSize, batchMaxBytes, totalBytes)
		}
	}
	return batch
}

func (h *consumerHandler) drainWithLinger(
	sessionCtx context.Context,
	messages <-chan *sarama.ConsumerMessage,
	batch []*sarama.ConsumerMessage,
	batchSize, batchMaxBytes, totalBytes int,
) []*sarama.ConsumerMessage {
	timer := time.NewTimer(h.batchLinger)
	defer timer.Stop()
	for len(batch) < batchSize && totalBytes < batchMaxBytes {
		select {
		case <-sessionCtx.Done():
			return nil
		case <-timer.C:
			return batch
		case msg, ok := <-messages:
			if !ok {
				return batch
			}
			batch = append(batch, msg)
			totalBytes += len(msg.Value)
		}
	}
	return batch
}

func (h *consumerHandler) flushBatch(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
	batch []*sarama.ConsumerMessage,
) (skipped int, lastSkipOff int64, lastSkipAge time.Duration) {
	kept, toWrite, skipped, lastSkipOff, lastSkipAge, stats := h.partitionBatch(batch, claim.HighWaterMarkOffset())
	h.recordReadMetrics(kept)

	if h.hasBatchSinker() {
		h.flushViaBatchSinker(session, claim, batch, kept, toWrite, &stats)
	} else {
		h.flushViaOneByOne(session, kept, &stats)
	}

	if session.Context().Err() != nil {
		return skipped, lastSkipOff, lastSkipAge
	}
	h.observeConsumeDelay(kept)
	h.emitWriteStats(batch[len(batch)-1].Topic, stats)
	session.MarkMessage(batch[len(batch)-1], "")
	return skipped, lastSkipOff, lastSkipAge
}

func (h *consumerHandler) partitionBatch(
	batch []*sarama.ConsumerMessage,
	hwm int64,
) (
	kept []*sarama.ConsumerMessage,
	toWrite []*sink.Message,
	skipped int,
	lastSkipOff int64,
	lastSkipAge time.Duration,
	stats sink.WriteStats,
) {
	for _, msg := range batch {
		if h.shouldSkipStale(msg, hwm) {
			skipped++
			lastSkipOff = msg.Offset
			lastSkipAge = time.Since(msg.Timestamp)
			stats.AddDrop("", sink.ReasonStale, 1)
			continue
		}
		kept = append(kept, msg)
		toWrite = append(toWrite, copySinkMessage(msg))
	}
	return kept, toWrite, skipped, lastSkipOff, lastSkipAge, stats
}

func copySinkMessage(msg *sarama.ConsumerMessage) *sink.Message {
	data := &sink.Message{Topic: msg.Topic, Data: make([]byte, len(msg.Value))}
	if len(msg.Value) > 0 {
		copy(data.Data, msg.Value)
	}
	return data
}

func (h *consumerHandler) hasBatchSinker() bool {
	for _, saver := range h.savers {
		if _, ok := saver.(sink.BatchSinker); ok {
			return true
		}
	}
	return false
}

func (h *consumerHandler) flushViaBatchSinker(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
	batch []*sarama.ConsumerMessage,
	keptMsgs []*sarama.ConsumerMessage,
	toWrite []*sink.Message,
	stats *sink.WriteStats,
) {
	var (
		batchPanicked bool
		errCount      int
		batchStats    sink.WriteStats
	)
	safe.Run(func() {
		errCount, batchStats = h.writeBatchSinkers(session, toWrite)
	}, flushBatchLabel, safe.WithOnPanic(func(pi safe.PanicInfo) {
		batchPanicked = true
		h.logBatchPanic(claim, batch, pi)
	}))
	if batchPanicked {
		h.degradeWriteOneByOne(session, keptMsgs, stats)
		return
	}
	if session.Context().Err() != nil {
		return
	}
	stats.Merge(batchStats)
	if len(toWrite) > 0 {
		h.addWriteErrors(toWrite[0].Topic, errCount)
	}
}

func (h *consumerHandler) logBatchPanic(
	claim sarama.ConsumerGroupClaim,
	batch []*sarama.ConsumerMessage,
	pi safe.PanicInfo,
) {
	firstOff, lastOff := int64(0), int64(0)
	if len(batch) > 0 {
		firstOff = batch[0].Offset
		lastOff = batch[len(batch)-1].Offset
	}
	logger.Error(
		"handle kafka batch panic, topic: %s, partition: %d, offset_from: %d, offset_to: %d, errmsg: %s",
		claim.Topic(), claim.Partition(), firstOff, lastOff, panicReasonError(pi.Reason),
	)
}

func (h *consumerHandler) flushViaOneByOne(
	session sarama.ConsumerGroupSession,
	keptMsgs []*sarama.ConsumerMessage,
	stats *sink.WriteStats,
) {
	if len(h.savers) == 0 {
		stats.AddDrop("", sink.ReasonNoSink, len(keptMsgs))
		return
	}
	for _, msg := range keptMsgs {
		if session.Context().Err() != nil {
			return
		}
		stats.Merge(h.handleOneMessage(session, session.Context(), msg))
	}
}

func (h *consumerHandler) writeBatchSinkers(
	session sarama.ConsumerGroupSession,
	msgs []*sink.Message,
) (int, sink.WriteStats) {
	var stats sink.WriteStats
	if len(msgs) == 0 {
		return 0, stats
	}
	if len(h.savers) == 0 {
		stats.AddDrop("", sink.ReasonNoSink, len(msgs))
		return 0, stats
	}
	errCount := 0
	for _, saver := range h.savers {
		if session.Context().Err() != nil {
			return errCount, stats
		}
		n, one := h.writeOneBatchSaver(session, saver, msgs)
		errCount += n
		stats.Merge(one)
	}
	return errCount, stats
}

func (h *consumerHandler) writeOneBatchSaver(
	session sarama.ConsumerGroupSession,
	saver sink.Sinker,
	msgs []*sink.Message,
) (int, sink.WriteStats) {
	bs, ok := saver.(sink.BatchSinker)
	if !ok {
		return 0, h.saveBatchOneByOne(session, saver, msgs)
	}
	result, err := bs.SaveBatch(session.Context(), msgs)
	if err != nil && len(msgs) > 0 {
		logger.Warn("save batch failed, topic: %s, errmsg: %s", msgs[0].Topic, err)
	}
	return result.Invalid + result.Failed, result.Stats
}

func (h *consumerHandler) saveBatchOneByOne(
	session sarama.ConsumerGroupSession,
	saver sink.Sinker,
	msgs []*sink.Message,
) sink.WriteStats {
	var stats sink.WriteStats
	for _, msg := range msgs {
		if session.Context().Err() != nil {
			return stats
		}
		if err := saver.Save(msg); err != nil {
			logger.Warn("save the data failed, topic: %s, errmsg: %s", msg.Topic, err)
			h.addWriteErrors(msg.Topic, 1)
			stats.AddDrop("", sink.ReasonWriteError, 1)
			continue
		}
		stats.Written++
	}
	return stats
}

func (h *consumerHandler) degradeWriteOneByOne(
	session sarama.ConsumerGroupSession,
	msgs []*sarama.ConsumerMessage,
	stats *sink.WriteStats,
) {
	timeout := h.degradeTimeout
	if timeout <= 0 {
		timeout = defaultDegradeTimeout
	}
	degradeCtx, cancel := context.WithTimeout(session.Context(), timeout)
	defer cancel()

	for i, msg := range msgs {
		if session.Context().Err() != nil {
			return
		}
		if degradeCtx.Err() != nil {
			h.addWriteErrors(msg.Topic, len(msgs)-i)
			h.addUntouchedDegrade(stats, msgs[i:])
			return
		}
		stats.Merge(h.handleOneMessage(session, degradeCtx, msg))
	}
}

func (h *consumerHandler) addUntouchedDegrade(stats *sink.WriteStats, msgs []*sarama.ConsumerMessage) {
	for range msgs {
		if len(h.savers) == 0 {
			stats.AddDrop("", sink.ReasonNoSink, 1)
			continue
		}
		for range h.savers {
			stats.AddDrop("", sink.ReasonDegradeTimeout, 1)
		}
	}
}

func (h *consumerHandler) handleOneMessage(
	session sarama.ConsumerGroupSession,
	writeCtx context.Context,
	msg *sarama.ConsumerMessage,
) sink.WriteStats {
	var stats sink.WriteStats
	done := 0
	panicked := false
	safe.Run(func() {
		h.writeMessageSavers(session, writeCtx, msg, &stats, &done)
	}, handleMessageLabel, safe.WithOnPanic(func(pi safe.PanicInfo) {
		panicked = true
		logger.Error(
			"handle kafka message panic, topic: %s, partition: %d, offset: %d, errmsg: %s",
			msg.Topic, msg.Partition, msg.Offset, panicReasonError(pi.Reason),
		)
		h.addWriteErrors(msg.Topic, 1)
	}))
	if panicked {
		h.addPanicDrops(&stats, done)
	}
	return stats
}

func (h *consumerHandler) writeMessageSavers(
	session sarama.ConsumerGroupSession,
	writeCtx context.Context,
	msg *sarama.ConsumerMessage,
	stats *sink.WriteStats,
	done *int,
) {
	if len(h.savers) == 0 {
		stats.AddDrop("", sink.ReasonNoSink, 1)
		return
	}
	data := copySinkMessage(msg)
	for i, saver := range h.savers {
		*done = i
		if session.Context().Err() != nil {
			return
		}
		if writeCtx.Err() != nil {
			h.addWriteErrors(msg.Topic, 1)
			h.addDegradeFrom(stats, i)
			*done = len(h.savers)
			return
		}
		h.writeOneSaver(writeCtx, msg.Topic, data, saver, stats)
		*done = i + 1
	}
}

func (h *consumerHandler) writeOneSaver(
	writeCtx context.Context,
	topic string,
	data *sink.Message,
	saver sink.Sinker,
	stats *sink.WriteStats,
) {
	if bs, ok := saver.(sink.BatchSinker); ok {
		result, err := bs.SaveBatch(writeCtx, []*sink.Message{data})
		if err != nil {
			logger.Warn("save batch one failed, topic: %s, errmsg: %s", topic, err)
		}
		if n := result.Invalid + result.Failed; n > 0 {
			h.addWriteErrors(topic, n)
		}
		stats.Merge(sink.RewriteCtxDone(result.Stats, sink.ReasonDegradeTimeout))
		return
	}
	if err := saver.Save(data); err != nil {
		logger.Warn("save the data failed, topic: %s, errmsg: %s", topic, err)
		h.addWriteErrors(topic, 1)
		stats.AddDrop("", sink.ReasonWriteError, 1)
		return
	}
	stats.Written++
}

func (h *consumerHandler) addDegradeFrom(stats *sink.WriteStats, from int) {
	for i := from; i < len(h.savers); i++ {
		stats.AddDrop("", sink.ReasonDegradeTimeout, 1)
	}
}

func (h *consumerHandler) addPanicDrops(stats *sink.WriteStats, done int) {
	if len(h.savers) == 0 {
		stats.AddDrop("", sink.ReasonPanic, 1)
		return
	}
	for i := done; i < len(h.savers); i++ {
		stats.AddDrop("", sink.ReasonPanic, 1)
	}
}

func (h *consumerHandler) emitWriteStats(topic string, stats sink.WriteStats) {
	if stats.Written == 0 && len(stats.Samples) == 0 && stats.DropTotal() == 0 {
		return
	}
	if h.recordStats != nil {
		h.recordStats(topic, stats)
		return
	}
	sink.RecordWriteStats(topic, stats)
}

func (h *consumerHandler) addWriteErrors(topic string, n int) {
	if h.countWriteErrors != nil {
		h.countWriteErrors(topic, n)
		return
	}
	incKafkaWriteErrors(topic, n)
}

func (h *consumerHandler) recordReadMetrics(msgs []*sarama.ConsumerMessage) {
	for _, msg := range msgs {
		if err := apm.KafkaReadBytesTotal.AddWithLabels(map[string]string{
			apm.MetricLabelKafka: msg.Topic,
		}, float64(len(msg.Value))); err != nil {
			logger.Warn("update kafka read bytes metric failed, errmsg: %s", err)
		}
		if err := apm.KafkaReadMessagesTotal.IncWithLabels(map[string]string{
			apm.MetricLabelKafka: msg.Topic,
		}); err != nil {
			logger.Warn("update kafka read messages metric failed, errmsg: %s", err)
		}
	}
}

func (h *consumerHandler) observeConsumeDelay(msgs []*sarama.ConsumerMessage) {
	if len(msgs) == 0 || apm.KafkaConsumeDelayMs == nil {
		return
	}
	bound := apm.KafkaConsumeDelayMs.WithLabels(map[string]string{
		apm.MetricLabelKafka: msgs[0].Topic,
	})
	now := time.Now()
	for _, msg := range msgs {
		if msg.Timestamp.IsZero() {
			continue
		}
		if obsErr := bound.Observe(float64(now.Sub(msg.Timestamp).Milliseconds())); obsErr != nil {
			logger.Warn("observe kafka consume delay failed, errmsg: %s", obsErr)
		}
	}
}

func incKafkaWriteErrors(topic string, n int) {
	if n <= 0 {
		return
	}
	if err := apm.KafkaWriteErrorsTotal.AddWithLabels(map[string]string{
		apm.MetricLabelKafka: topic,
	}, float64(n)); err != nil {
		logger.Warn("update kafka write errors metric failed, errmsg: %s", err)
	}
}
