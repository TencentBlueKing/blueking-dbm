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
	"crypto/sha512"
	"dbm-services/common/dbha-v2/internal/receiver/output"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"strings"
	"sync"
	"time"

	"github.com/IBM/sarama"
	"github.com/xdg-go/scram"
)

var (
	SHA512 scram.HashGeneratorFcn = sha512.New
)

const (
	Name                 = "kafka"
	kafkaConsumerGroupID = "dbhav2-receiver-kafka-consumer-group-id"
)

type xdgSCRAMClient struct {
	*scram.Client
	*scram.ClientConversation
	scram.HashGeneratorFcn
}

func (x *xdgSCRAMClient) Begin(userName, password, authzID string) (err error) {
	x.Client, err = x.HashGeneratorFcn.NewClient(userName, password, authzID)
	if err != nil {
		return err
	}
	x.ClientConversation = x.Client.NewConversation()
	return nil
}

func (x *xdgSCRAMClient) Step(challenge string) (response string, err error) {
	response, err = x.ClientConversation.Step(challenge)
	return
}

func (x *xdgSCRAMClient) Done() bool {
	return x.ClientConversation.Done()
}

type consumer struct {
	endpoints []string
	topics    []string
	user      string
	password  string
	quit      chan struct{}
	group     sarama.ConsumerGroup
	wg        sync.WaitGroup
}

func New(endpoints []string, topics []string, user, password, mechanism string) (*consumer, error) {
	config := sarama.NewConfig()

	config.Version = sarama.V3_2_3_0
	config.Metadata.Full = true

	// Network configuration
	config.Net.MaxOpenRequests = 5
	config.Net.DialTimeout = 30 * time.Second
	config.Net.ReadTimeout = 30 * time.Second
	config.Net.WriteTimeout = 30 * time.Second

	// SASL Configuration
	config.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.NewBalanceStrategyRoundRobin()}
	config.Consumer.Offsets.Initial = sarama.OffsetOldest
	config.Version = sarama.V0_10_2_0
	config.Consumer.Return.Errors = true
	config.Consumer.MaxProcessingTime = 200 * time.Millisecond
	config.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{
		sarama.NewBalanceStrategyRoundRobin(),
		sarama.NewBalanceStrategyRange(),
	}
	config.Consumer.Offsets.AutoCommit = struct {
		Enable   bool
		Interval time.Duration
	}{
		Enable:   true,
		Interval: 1 * time.Second,
	}

	config.Metadata.Full = true
	config.Net.SASL.User = user
	config.Net.SASL.Password = password
	if strings.ToUpper(mechanism) == "SCRAM-SHA-512" {
		config.Version = sarama.V2_4_0_0
		config.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA512
		config.Net.SASL.Enable = true
		config.Net.SASL.Handshake = true
		config.Net.SASL.Version = sarama.SASLHandshakeV1
		config.Net.SASL.SCRAMClientGeneratorFunc = func() sarama.SCRAMClient {
			return &xdgSCRAMClient{HashGeneratorFcn: SHA512}
		}
	} else {
		config.Net.SASL.Mechanism = sarama.SASLTypePlaintext
	}

	group, err := sarama.NewConsumerGroup(endpoints, kafkaConsumerGroupID, config)
	if err != nil {
		return nil, gerrors.Newf(gerrors.ComponentFailure, "create kafka client failed, errmsg(%v)", err)
	}

	kInputer := &consumer{endpoints: endpoints, topics: topics, user: user, password: password, group: group}
	return kInputer, nil
}

func (k *consumer) Harvest(ctx context.Context, savers []output.Outputter) error {
	k.wg.Add(1)
	go func(ctx context.Context) {
		defer k.wg.Done()

		for {
			select {
			case <-k.quit:
				return

			case <-ctx.Done():
				return

			default:
				err := k.group.Consume(ctx, k.topics, &consumerHandler{savers: savers})
				if err != nil {
					logger.Warn("kafka consumer failed, errmsg(%v)", err)
					return
				}
			}
		}

	}(ctx)

	return nil
}

func (k *consumer) Close() {
	if k.quit != nil {
		close(k.quit)
	}

	if k.group != nil {
		k.group.Close()
	}

	k.wg.Wait()
}
