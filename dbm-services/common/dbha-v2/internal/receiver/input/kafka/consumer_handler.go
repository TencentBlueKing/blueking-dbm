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
	"dbm-services/common/dbha-v2/internal/receiver/output"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/IBM/sarama"
)

var _ sarama.ConsumerGroupHandler = (*consumerHandler)(nil)

type consumerHandler struct {
	savers []output.Outputter
}

func (h *consumerHandler) Setup(session sarama.ConsumerGroupSession) error {
	logger.Info("begin to consume")
	return nil
}

func (h *consumerHandler) Cleanup(session sarama.ConsumerGroupSession) error {
	logger.Info("end to consume")
	return nil
}

func (h *consumerHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		dataLength := len(msg.Value)
		data := &output.Message{
			Topic: msg.Topic,
			Data:  make([]byte, dataLength),
		}

		if dataLength > 0 {
			copy(data.Data, msg.Value)
		}

		for _, saver := range h.savers {
			if err := saver.Save(data); err != nil {
				logger.Warn("save the data failed, topic(%s), %v", msg.Topic, err)
			}
		}
	}

	return nil
}
