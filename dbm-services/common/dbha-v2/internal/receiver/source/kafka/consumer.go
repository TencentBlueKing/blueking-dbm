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

// Package kafka implements the receiver Kafka source that harvests probe reports from a consumer group.
package kafka

import (
	"context"
	"crypto/sha512"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"

	"github.com/IBM/sarama"
	"github.com/xdg-go/scram"
)

type newConsumerGroupFunc func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error)

var (
	// SHA512 is the SCRAM-SHA-512 hash generator used for SASL authentication.
	SHA512 scram.HashGeneratorFcn = sha512.New

	errConsumerStopping = errors.New("kafka consumer is stopping")
)

const (
	// Name is the receiver source identifier for Kafka.
	Name                 = "kafka"
	kafkaConsumerGroupID = "dbhav2-receiver-kafka-consumer-group-id"

	consumeRetryMinBackoff  = 1 * time.Second
	consumeRetryMaxBackoff  = 30 * time.Second
	consumeRebuildThreshold = 5
	timeoutMargin           = 5 * time.Second
	defaultMaxMessageAge    = 5 * time.Minute
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
	endpoints     []string
	topics        []string
	cliCfg        *sarama.Config
	maxMessageAge time.Duration
	quit          chan struct{}
	closeOnce     sync.Once
	mu            sync.Mutex
	group         sarama.ConsumerGroup
	newGroup      newConsumerGroupFunc
	minBackoff    time.Duration
	maxBackoff    time.Duration
	wg            sync.WaitGroup
}

// New creates a Kafka consumer inputter from source configuration.
// It validates config and endpoints but does not connect to Kafka; the consumer
// group is created lazily in Harvest so a temporary broker outage at startup
// can be retried.
func New(cfg config.SourceConfig) (*consumer, error) {
	if len(cfg.Topics) == 0 {
		return nil, gerrors.New(gerrors.InvalidConfiguration, "kafka topics is empty")
	}

	cliCfg := newSaramaConfig(cfg)
	adjustGroupTimeouts(cliCfg)
	if err := cliCfg.Validate(); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid kafka config, errmsg: %s", err)
	}

	parsed, err := hanet.ParseList(cfg.Endpoints, "tcp")
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid kafka endpoints, errmsg: %s", err)
	}

	return &consumer{
		endpoints:     hanet.ToHostPorts(parsed),
		topics:        cfg.Topics,
		cliCfg:        cliCfg,
		maxMessageAge: resolveMaxMessageAge(cfg.MaxMessageAge),
		quit:          make(chan struct{}),
		newGroup:      sarama.NewConsumerGroup,
		minBackoff:    consumeRetryMinBackoff,
		maxBackoff:    consumeRetryMaxBackoff,
	}, nil
}

// Harvest starts consuming Kafka topics in the background and writes messages to savers.
// ctx cancellation or Close stops the loop. It always returns nil after the goroutine is started.
func (k *consumer) Harvest(ctx context.Context, savers []sink.Sinker) error {
	k.wg.Add(1)
	go func(ctx context.Context) {
		defer k.wg.Done()
		k.runHarvestLoop(ctx, &consumerHandler{
			savers:        savers,
			maxMessageAge: k.maxMessageAge,
		})
	}(ctx)

	return nil
}

// Close stops the harvest loop, closes the consumer group if it exists, and waits for exit.
func (k *consumer) Close() {
	k.closeOnce.Do(func() {
		close(k.quit)
	})

	k.mu.Lock()
	group := k.group
	k.group = nil
	k.mu.Unlock()

	if group != nil {
		_ = group.Close()
	}

	k.wg.Wait()
}

func (k *consumer) runHarvestLoop(ctx context.Context, handler *consumerHandler) {
	backoff := k.minBackoff
	failures := 0

	for {
		group, lived, panicked, err := k.runOnce(ctx, handler)
		if k.shouldStop(ctx) {
			return
		}

		if lived >= k.minBackoff {
			backoff = k.minBackoff
			failures = 0
		}

		if err == nil {
			if lived >= k.minBackoff {
				continue
			}
			if !k.waitRetry(ctx, backoff) {
				return
			}
			backoff = min(backoff*2, k.maxBackoff)
			continue
		}

		if errors.Is(err, errConsumerStopping) {
			return
		}

		failures++
		failures = k.handleConsumeFailure(group, panicked, err, failures, backoff)
		if !k.waitRetry(ctx, backoff) {
			return
		}
		backoff = min(backoff*2, k.maxBackoff)
	}
}

func (k *consumer) handleConsumeFailure(
	group sarama.ConsumerGroup,
	panicked bool,
	err error,
	failures int,
	backoff time.Duration,
) int {
	immediateRebuild := panicked || errors.Is(err, sarama.ErrClosedConsumerGroup)
	if !immediateRebuild {
		logger.Warn("kafka consumer failed, retry after: %s, errmsg: %s", backoff, err)
	}
	if immediateRebuild || failures >= consumeRebuildThreshold {
		k.rebuildGroup(group, failures)
		return 0
	}
	return failures
}

func (k *consumer) runOnce(
	ctx context.Context,
	handler *consumerHandler,
) (group sarama.ConsumerGroup, lived time.Duration, panicked bool, err error) {
	safe.Run(func() {
		var innerErr error
		group, innerErr = k.ensureGroup()
		if innerErr != nil {
			err = innerErr
			return
		}
		start := time.Now()
		err = group.Consume(ctx, k.topics, handler)
		lived = time.Since(start)
	}, safe.WithLabel("kafka-consumer"), safe.WithOnPanic(func(pi safe.PanicInfo) {
		panicked = true
		err = panicReasonError(pi.Reason)
	}))

	return
}

func panicReasonError(reason any) error {
	if err, ok := reason.(error); ok {
		return err
	}
	return fmt.Errorf("%v", reason)
}

func (k *consumer) ensureGroup() (sarama.ConsumerGroup, error) {
	k.mu.Lock()
	if k.group != nil {
		group := k.group
		k.mu.Unlock()
		return group, nil
	}
	if k.isQuitClosed() {
		k.mu.Unlock()
		return nil, errConsumerStopping
	}
	k.mu.Unlock()

	created, err := k.newGroup(k.endpoints, kafkaConsumerGroupID, k.cliCfg)
	if err != nil {
		return nil, err
	}

	k.mu.Lock()
	if k.isQuitClosed() {
		k.mu.Unlock()
		_ = created.Close()
		return nil, errConsumerStopping
	}
	if k.group != nil {
		existing := k.group
		k.mu.Unlock()
		_ = created.Close()
		return existing, nil
	}
	k.group = created
	k.mu.Unlock()
	return created, nil
}

func (k *consumer) rebuildGroup(old sarama.ConsumerGroup, failures int) {
	if old == nil {
		return
	}

	logger.Warn("rebuild kafka consumer group, consecutive failures: %d", failures)

	k.mu.Lock()
	if k.group == old {
		k.group = nil
	}
	k.mu.Unlock()

	_ = old.Close()
}

func (k *consumer) shouldStop(ctx context.Context) bool {
	if ctx.Err() != nil {
		return true
	}
	return k.isQuitClosed()
}

func (k *consumer) isQuitClosed() bool {
	select {
	case <-k.quit:
		return true
	default:
		return false
	}
}

func (k *consumer) waitRetry(ctx context.Context, d time.Duration) bool {
	timer := time.NewTimer(d)
	defer timer.Stop()

	select {
	case <-k.quit:
		return false
	case <-ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

func newSaramaConfig(cfg config.SourceConfig) *sarama.Config {
	cliCfg := sarama.NewConfig()
	cliCfg.Net.DialTimeout = cfg.NetDialTimeout
	cliCfg.Net.ReadTimeout = cfg.NetReadTimeout
	cliCfg.Net.WriteTimeout = cfg.NetWriteTimeout

	cliCfg.Version = sarama.V0_10_2_0
	cliCfg.Consumer.Offsets.Initial = sarama.OffsetNewest
	cliCfg.Consumer.Return.Errors = true
	cliCfg.Consumer.MaxProcessingTime = 200 * time.Millisecond
	cliCfg.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{
		sarama.NewBalanceStrategyRoundRobin(),
		sarama.NewBalanceStrategyRange(),
	}
	cliCfg.Consumer.Offsets.AutoCommit = struct {
		Enable   bool
		Interval time.Duration
	}{
		Enable:   true,
		Interval: 1 * time.Second,
	}
	cliCfg.Metadata.Full = true
	cliCfg.Net.SASL.User = cfg.User
	cliCfg.Net.SASL.Password = cfg.Password

	if strings.ToUpper(cfg.Mechanism) == "SCRAM-SHA-512" {
		cliCfg.Version = sarama.V2_4_0_0
		cliCfg.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA512
		cliCfg.Net.SASL.Enable = true
		cliCfg.Net.SASL.Handshake = true
		cliCfg.Net.SASL.Version = sarama.SASLHandshakeV1
		cliCfg.Net.SASL.SCRAMClientGeneratorFunc = func() sarama.SCRAMClient {
			return &xdgSCRAMClient{HashGeneratorFcn: SHA512}
		}
	} else {
		cliCfg.Net.SASL.Mechanism = sarama.SASLTypePlaintext
	}

	return cliCfg
}

func resolveMaxMessageAge(d time.Duration) time.Duration {
	if d == 0 {
		return defaultMaxMessageAge
	}
	return d
}

func adjustGroupTimeouts(cfg *sarama.Config) {
	readTimeout := cfg.Net.ReadTimeout
	rebalanceTimeout := cfg.Consumer.Group.Rebalance.Timeout
	sessionTimeout := cfg.Consumer.Group.Session.Timeout

	if readTimeout > rebalanceTimeout+timeoutMargin {
		return
	}

	adjusted := max(time.Duration(float64(readTimeout)*0.8), sessionTimeout)
	cfg.Consumer.Group.Rebalance.Timeout = adjusted
	logger.Info(
		"adjust kafka rebalance timeout, read_timeout: %s, rebalance_timeout: %s",
		readTimeout, adjusted,
	)

	if cfg.Net.ReadTimeout < cfg.Consumer.Group.Rebalance.Timeout+timeoutMargin {
		cfg.Net.ReadTimeout = cfg.Consumer.Group.Rebalance.Timeout + timeoutMargin
		logger.Warn(
			"kafka read timeout too small, adjusted read_timeout: %s, rebalance_timeout: %s",
			cfg.Net.ReadTimeout, cfg.Consumer.Group.Rebalance.Timeout,
		)
	}
}
