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

	"dbm-services/common/dbha-v2/internal/receiver/apm"
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
	savers        []sink.Sinker
	maxMessageAge time.Duration
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
	var (
		skippedCount  int
		lastSkipAge   time.Duration
		lastSkipOff   int64
		lastSkipLogAt time.Time
	)

	for {
		select {
		case <-session.Context().Done():
			flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge)
			return nil

		case msg, ok := <-claim.Messages():
			if !ok {
				flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge)
				return nil
			}

			skipped := h.handleMessage(msg, claim.HighWaterMarkOffset())
			if skipped {
				skippedCount++
				lastSkipAge = time.Since(msg.Timestamp)
				lastSkipOff = msg.Offset
				if lastSkipLogAt.IsZero() || time.Since(lastSkipLogAt) >= staleSkipLogInterval {
					if flushStaleSkipLog(claim, skippedCount, lastSkipOff, lastSkipAge) {
						skippedCount = 0
						lastSkipLogAt = time.Now()
					}
				}
			}

			session.MarkMessage(msg, "")
		}
	}
}

func (h *consumerHandler) handleMessage(msg *sarama.ConsumerMessage, hwm int64) (skipped bool) {
	safe.Run(func() {
		if h.shouldSkipStale(msg, hwm) {
			skipped = true
			return
		}

		dataLength := len(msg.Value)
		data := &sink.Message{
			Topic: msg.Topic,
			Data:  make([]byte, dataLength),
		}
		if dataLength > 0 {
			copy(data.Data, msg.Value)
		}

		if err := apm.KafkaReadBytesTotal.AddWithLabels(map[string]string{
			apm.MetricLabelKafka: msg.Topic,
		}, float64(dataLength)); err != nil {
			logger.Warn("update kafka read bytes metric failed, errmsg: %s", err)
		}

		if err := apm.KafkaReadMessagesTotal.IncWithLabels(map[string]string{
			apm.MetricLabelKafka: msg.Topic,
		}); err != nil {
			logger.Warn("update kafka read messages metric failed, errmsg: %s", err)
		}

		for _, saver := range h.savers {
			if err := saver.Save(data); err != nil {
				logger.Warn("save the data failed, topic: %s, errmsg: %s", msg.Topic, err)

				if metricErr := apm.KafkaWriteErrorsTotal.IncWithLabels(map[string]string{
					apm.MetricLabelKafka: msg.Topic,
				}); metricErr != nil {
					logger.Warn("update kafka write errors metric failed, errmsg: %s", metricErr)
				}
			}
		}
	}, handleMessageLabel, safe.WithOnPanic(func(pi safe.PanicInfo) {
		logger.Error(
			"handle kafka message panic, topic: %s, partition: %d, offset: %d, errmsg: %s",
			msg.Topic, msg.Partition, msg.Offset, panicReasonError(pi.Reason),
		)
		if metricErr := apm.KafkaWriteErrorsTotal.IncWithLabels(map[string]string{
			apm.MetricLabelKafka: msg.Topic,
		}); metricErr != nil {
			logger.Warn("update kafka write errors metric failed, errmsg: %s", metricErr)
		}
	}))

	return
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
