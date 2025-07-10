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
	"reflect"
	"time"

	"github.com/Shopify/sarama"
	"golang.org/x/exp/slog"

	"dbm-services/common/db-event-consumer/pkg/config"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

type Sinker struct {
	RuntimeConfig   *config.SinkerConfig
	MetaInfo        *config.KafkaMeta
	consumerHandler sarama.ConsumerGroupHandler
	DSWriter        sinker.DSWriter
}

func (s *Sinker) NewSinkHandler() (sarama.ConsumerGroupHandler, error) {
	modelTable, ok := sinker.ModelSinkerRegistered[s.RuntimeConfig.ModelTable]
	if !ok {
		return nil, fmt.Errorf("table not config")
	}
	modelType := reflect.TypeOf(modelTable).Elem()
	if modelType.Kind() == reflect.Ptr {
		modelType = modelType.Elem()
	}
	modelValue := reflect.New(modelType)
	handler := &AnySinker{
		modelType:      modelType,
		modelValue:     reflect.New(modelType),
		modelObject:    modelValue.Interface(),
		dsWriter:       s.DSWriter,
		Ready:          make(chan bool),
		Sinker:         s,
		NoManageSchema: modelTable.NoManageSchema(),
	}
	handler.Sinker = s
	s.consumerHandler = handler
	return handler, nil
}

func (s *Sinker) NewConsumerGroup() (sarama.ConsumerGroup, error) {
	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.BalanceStrategyRoundRobin}
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetOldest
	consumerConfig.Version = sarama.V0_10_2_0
	consumerConfig.Consumer.Return.Errors = true
	consumerConfig.Consumer.MaxProcessingTime = 200 * time.Millisecond
	if s.RuntimeConfig.FetchMinBytes > 0 {
		consumerConfig.Consumer.Fetch.Min = s.RuntimeConfig.FetchMinBytes
	} else {
		consumerConfig.Consumer.Fetch.Min = 1024
	}
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

	consumerConfig.ClientID = fmt.Sprintf("%s%s", s.RuntimeConfig.Topic, s.RuntimeConfig.ClientIdSuffix)

	slog.Debug("build consumer config", slog.Any("config", consumerConfig))

	groupId := fmt.Sprintf("%s_%s", s.RuntimeConfig.Topic, s.RuntimeConfig.GroupIdSuffix)
	group, err := sarama.NewConsumerGroup(
		[]string{
			fmt.Sprintf(
				`%s:%d`,
				s.MetaInfo.ClusterConfig.DomainName,
				s.MetaInfo.ClusterConfig.Port),
		},
		groupId,
		consumerConfig,
	)
	if err != nil {
		slog.Error("create consumer", err)
		return nil, err
	}

	return group, nil
}
