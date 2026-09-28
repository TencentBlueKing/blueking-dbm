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

func (h *consumerHandler) consumeClaimBatched(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
) error {
	var (
		skippedCount  int
		lastSkipAge   time.Duration
		lastSkipOff   int64
		lastSkipLogAt time.Time
	)

	messages := claim.Messages()
	for {
		select {
		case <-session.Context().Done():
			flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge)
			return nil
		case first, ok := <-messages:
			if !ok {
				flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge)
				return nil
			}
			batch := h.drainBatch(session.Context(), messages, first)
			if len(batch) == 0 {
				continue
			}
			skipped, lastOff, lastAge := h.flushBatch(session, claim, batch)
			if skipped > 0 {
				skippedCount += skipped
				lastSkipOff = lastOff
				lastSkipAge = lastAge
				if lastSkipLogAt.IsZero() || time.Since(lastSkipLogAt) >= staleSkipLogInterval {
					if flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge) {
						skippedCount = 0
						lastSkipLogAt = time.Now()
					}
				}
			}
			if session.Context().Err() != nil {
				flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge)
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
	hwm := claim.HighWaterMarkOffset()
	var (
		toWrite  []*sink.Message
		keptMsgs []*sarama.ConsumerMessage
		lastMsg  = batch[len(batch)-1]
	)

	for _, msg := range batch {
		if h.shouldSkipStale(msg, hwm) {
			skipped++
			lastSkipOff = msg.Offset
			lastSkipAge = time.Since(msg.Timestamp)
			continue
		}
		keptMsgs = append(keptMsgs, msg)
		dataLength := len(msg.Value)
		data := &sink.Message{
			Topic: msg.Topic,
			Data:  make([]byte, dataLength),
		}
		if dataLength > 0 {
			copy(data.Data, msg.Value)
		}
		toWrite = append(toWrite, data)
	}
	h.recordReadMetrics(keptMsgs)

	if h.hasBatchSinker() {
		h.flushViaBatchSinker(session, claim, batch, keptMsgs, toWrite)
	} else {
		h.flushViaOneByOne(session, keptMsgs)
	}

	if session.Context().Err() != nil {
		return skipped, lastSkipOff, lastSkipAge
	}
	h.observeConsumeDelay(keptMsgs)
	session.MarkMessage(lastMsg, "")
	return skipped, lastSkipOff, lastSkipAge
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
) {
	batchPanicked := false
	safe.Run(func() {
		h.writeBatchSinkers(session, toWrite)
	}, flushBatchLabel, safe.WithOnPanic(func(pi safe.PanicInfo) {
		batchPanicked = true
		firstOff, lastOff := int64(0), int64(0)
		if len(batch) > 0 {
			firstOff = batch[0].Offset
			lastOff = batch[len(batch)-1].Offset
		}
		logger.Error(
			"handle kafka batch panic, topic: %s, partition: %d, offset_from: %d, offset_to: %d, errmsg: %s",
			claim.Topic(), claim.Partition(), firstOff, lastOff, panicReasonError(pi.Reason),
		)
	}))
	if batchPanicked {
		h.degradeWriteOneByOne(session, keptMsgs)
		return
	}
	if session.Context().Err() == nil {
		h.recordBatchWriteErrors(toWrite)
	}
}

func (h *consumerHandler) flushViaOneByOne(
	session sarama.ConsumerGroupSession,
	keptMsgs []*sarama.ConsumerMessage,
) {
	for _, msg := range keptMsgs {
		if session.Context().Err() != nil {
			return
		}
		h.handleOneMessage(session, session.Context(), msg)
	}
}

func (h *consumerHandler) writeBatchSinkers(session sarama.ConsumerGroupSession, msgs []*sink.Message) {
	h.lastBatchErrorCount = 0
	if len(msgs) == 0 {
		return
	}
	for _, saver := range h.savers {
		bs, ok := saver.(sink.BatchSinker)
		if !ok {
			for _, msg := range msgs {
				if session.Context().Err() != nil {
					return
				}
				if err := saver.Save(msg); err != nil {
					logger.Warn("save the data failed, topic: %s, errmsg: %s", msg.Topic, err)
					incKafkaWriteErrors(msg.Topic, 1)
				}
			}
			continue
		}
		result, err := bs.SaveBatch(session.Context(), msgs)
		if err != nil {
			logger.Warn("save batch failed, topic: %s, errmsg: %s", msgs[0].Topic, err)
		}
		h.lastBatchErrorCount += result.Invalid + result.Failed
	}
}

func (h *consumerHandler) degradeWriteOneByOne(
	session sarama.ConsumerGroupSession,
	msgs []*sarama.ConsumerMessage,
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
			// degrade timeout while session still valid: count remaining and mark later
			incKafkaWriteErrors(msg.Topic, len(msgs)-i)
			return
		}
		h.handleOneMessage(session, degradeCtx, msg)
	}
}

func (h *consumerHandler) handleOneMessage(
	session sarama.ConsumerGroupSession,
	writeCtx context.Context,
	msg *sarama.ConsumerMessage,
) {
	safe.Run(func() {
		dataLength := len(msg.Value)
		data := &sink.Message{
			Topic: msg.Topic,
			Data:  make([]byte, dataLength),
		}
		if dataLength > 0 {
			copy(data.Data, msg.Value)
		}
		for _, saver := range h.savers {
			if session.Context().Err() != nil {
				return
			}
			if writeCtx.Err() != nil {
				incKafkaWriteErrors(msg.Topic, 1)
				return
			}
			if bs, ok := saver.(sink.BatchSinker); ok {
				result, err := bs.SaveBatch(writeCtx, []*sink.Message{data})
				if err != nil {
					logger.Warn("save batch one failed, topic: %s, errmsg: %s", msg.Topic, err)
				}
				if n := result.Invalid + result.Failed; n > 0 {
					incKafkaWriteErrors(msg.Topic, n)
				}
				continue
			}
			if err := saver.Save(data); err != nil {
				logger.Warn("save the data failed, topic: %s, errmsg: %s", msg.Topic, err)
				incKafkaWriteErrors(msg.Topic, 1)
			}
		}
	}, handleMessageLabel, safe.WithOnPanic(func(pi safe.PanicInfo) {
		logger.Error(
			"handle kafka message panic, topic: %s, partition: %d, offset: %d, errmsg: %s",
			msg.Topic, msg.Partition, msg.Offset, panicReasonError(pi.Reason),
		)
		incKafkaWriteErrors(msg.Topic, 1)
	}))
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

func (h *consumerHandler) recordBatchWriteErrors(msgs []*sink.Message) {
	if len(msgs) == 0 || h.lastBatchErrorCount <= 0 {
		return
	}
	incKafkaWriteErrors(msgs[0].Topic, h.lastBatchErrorCount)
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
