package consumer

import (
	"fmt"
	"time"

	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"

	"github.com/Shopify/sarama"
	"golang.org/x/exp/slog"
)

func newConsumerGroup() (sarama.ConsumerGroup, error) {
	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.BalanceStrategyRoundRobin}
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetOldest
	consumerConfig.Version = sarama.V0_10_2_0
	consumerConfig.Consumer.Return.Errors = true
	consumerConfig.Consumer.Offsets.AutoCommit = struct {
		Enable   bool
		Interval time.Duration
	}{
		Enable:   true,
		Interval: 1 * time.Second,
	}

	consumerConfig.Metadata.Full = true
	consumerConfig.Net.SASL.User = config.MetaInfo.AuthInfo.Username
	consumerConfig.Net.SASL.Password = config.MetaInfo.AuthInfo.Password
	if config.MetaInfo.AuthInfo.SaslMechanisms == "SCRAM-SHA-512" {
		consumerConfig.Version = sarama.V2_4_0_0
		consumerConfig.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA512
		consumerConfig.Net.SASL.Enable = true
		consumerConfig.Net.SASL.Handshake = true
		consumerConfig.Net.SASL.Version = sarama.SASLHandshakeV1
		consumerConfig.Net.SASL.SCRAMClientGeneratorFunc = func() sarama.SCRAMClient {
			return &XDGSCRAMClient{HashGeneratorFcn: SHA512}
		}
	} else {
		consumerConfig.Net.SASL.Mechanism = sarama.SASLTypePlaintext
	}

	consumerConfig.ClientID = config.RuntimeConfig.ClientId

	slog.Debug("build consumer config", slog.Any("config", consumerConfig))

	group, err := sarama.NewConsumerGroup(
		[]string{
			fmt.Sprintf(
				`%s:%d`,
				config.MetaInfo.ClusterConfig.DomainName,
				config.MetaInfo.ClusterConfig.Port),
		},
		config.RuntimeConfig.GroupId,
		consumerConfig,
	)
	if err != nil {
		slog.Error("create consumer", err)
		return nil, err
	}

	return group, nil
}
