// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package consumer

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/bkdata-kafka-consumer/pkg/config"

	"github.com/Shopify/sarama"
	"golang.org/x/exp/slog"
)

type Sinker struct {
	RuntimeConfig   *config.SinkerConfig
	MetaInfo        *config.KafkaMeta
	consumerHandler sarama.ConsumerGroupHandler
}

func (s *Sinker) NewSinkHandler() (sarama.ConsumerGroupHandler, error) {
	db, err := getDb(s)
	if err != nil {
		return nil, err
	}
	if strings.HasPrefix(s.RuntimeConfig.GroupId, "mysql-backup-result") {
		handler := &MysqlBackupResult{Db: db, Ready: make(chan bool)}
		handler.Sinker = s
		s.consumerHandler = handler
		return handler, nil
	} else if strings.HasPrefix(s.RuntimeConfig.GroupId, "mysql-binlog-result") {
		handler := &MysqlBinlogResult{Db: db, Ready: make(chan bool)}
		handler.Sinker = s
		s.consumerHandler = handler
		return handler, nil
	} else if strings.HasPrefix(s.RuntimeConfig.GroupId, "mysql_db_table_size_to_mysql") {
		handler := &MysqlTableSize{Db: db, Ready: make(chan bool)}
		handler.Sinker = s
		s.consumerHandler = handler
		return handler, nil
	} else if strings.HasPrefix(s.RuntimeConfig.GroupId, "mysql_db_table_size_to_doris") {
		handler := &MysqlTableSizeDoris{Db: db, Ready: make(chan bool)}
		handler.Sinker = s
		s.consumerHandler = handler
		return handler, nil
	}
	return nil, fmt.Errorf("table not config")
}

func (s *Sinker) newConsumerGroup() (sarama.ConsumerGroup, error) {
	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.BalanceStrategyRoundRobin}
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetOldest
	consumerConfig.Version = sarama.V0_10_2_0
	consumerConfig.Consumer.Return.Errors = true
	consumerConfig.Consumer.MaxProcessingTime = 200 * time.Millisecond
	consumerConfig.Consumer.Fetch.Min = 1024
	consumerConfig.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{
		sarama.BalanceStrategyRoundRobin,
		sarama.BalanceStrategyRange,
	}
	consumerConfig.Consumer.Offsets.AutoCommit = struct {
		Enable   bool
		Interval time.Duration
	}{
		Enable:   true,
		Interval: 1 * time.Second,
	}

	consumerConfig.Metadata.Full = true
	consumerConfig.Net.SASL.User = s.MetaInfo.AuthInfo.Username
	consumerConfig.Net.SASL.Password = s.MetaInfo.AuthInfo.Password
	if s.MetaInfo.AuthInfo.SaslMechanisms == "SCRAM-SHA-512" {
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

	consumerConfig.ClientID = s.RuntimeConfig.ClientId

	slog.Debug("build consumer config", slog.Any("config", consumerConfig))

	group, err := sarama.NewConsumerGroup(
		[]string{
			fmt.Sprintf(
				`%s:%d`,
				s.MetaInfo.ClusterConfig.DomainName,
				s.MetaInfo.ClusterConfig.Port),
		},
		s.RuntimeConfig.GroupId,
		consumerConfig,
	)
	if err != nil {
		slog.Error("create consumer", err)
		return nil, err
	}

	return group, nil
}
