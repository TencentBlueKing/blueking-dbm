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
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"

	"github.com/IBM/sarama"
)

const (
	staleBacklogThreshold = int64(1000)
	staleSkipLogInterval  = time.Minute
)

var handleMessageLabel = safe.WithLabel("kafka-handle-message")

type consumerHandler struct {
	savers         []sink.Sinker
	maxMessageAge  time.Duration
	batchSize      int
	batchMaxBytes  int
	batchLinger    time.Duration
	degradeTimeout time.Duration

	// recordStats replaces sink.RecordWriteStats in tests.
	recordStats func(topic string, stats sink.WriteStats)
	// countWriteErrors replaces kafka write-error counting in tests.
	countWriteErrors func(topic string, n int)
}

var _ sarama.ConsumerGroupHandler = (*consumerHandler)(nil)

func (h *consumerHandler) Setup(_ sarama.ConsumerGroupSession) error {
	logger.Info("begin to consume")
	return nil
}

func (h *consumerHandler) Cleanup(_ sarama.ConsumerGroupSession) error {
	logger.Info("end to consume")
	return nil
}

func (h *consumerHandler) ConsumeClaim(
	session sarama.ConsumerGroupSession,
	claim sarama.ConsumerGroupClaim,
) error {
	return h.consumeClaimBatched(session, claim)
}

func (h *consumerHandler) shouldSkipStale(msg *sarama.ConsumerMessage, hwm int64) bool {
	if msg.Timestamp.IsZero() {
		return false
	}
	if h.maxMessageAge <= 0 {
		return false
	}
	if time.Since(msg.Timestamp) <= h.maxMessageAge {
		return false
	}
	return hwm-msg.Offset > staleBacklogThreshold
}

func flushStaleSkipLog(claim sarama.ConsumerGroupClaim, count int, lastOff int64, age time.Duration) bool {
	if count <= 0 {
		return false
	}
	logger.Warn(
		"skip stale kafka messages, topic: %s, partition: %d, skipped: %d, last offset: %d, age: %s",
		claim.Topic(), claim.Partition(), count, lastOff, age,
	)
	return true
}
