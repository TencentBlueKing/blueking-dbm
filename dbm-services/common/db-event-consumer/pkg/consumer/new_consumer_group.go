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
	"strings"
	"time"

	"github.com/Shopify/sarama"
	"github.com/samber/lo"
	"golang.org/x/exp/slog"

	"dbm-services/common/db-event-consumer/pkg/config"
	"dbm-services/common/db-event-consumer/pkg/model"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

type Sinker struct {
	RuntimeConfig   *config.SinkerConfig
	MetaInfo        *config.KafkaMeta
	consumerHandler sarama.ConsumerGroupHandler
	DSWriter        sinker.DSWriter
}

func (s *Sinker) NewSinkHandler() (sarama.ConsumerGroupHandler, error) {
	var handler *AnySinker
	modelTable, ok := sinker.ModelSinkerRegistered[s.RuntimeConfig.ModelTable]
	if ok {
		if !*s.RuntimeConfig.StrictSchema {
			return nil, fmt.Errorf("registerd table[%s] need strict_schema=true", s.RuntimeConfig.ModelTable)
		}
		modelType := reflect.TypeOf(modelTable).Elem()
		if modelType.Kind() == reflect.Ptr {
			modelType = modelType.Elem()
		}
		modelValue := reflect.New(modelType)
		handler = &AnySinker{
			modelType:   modelType,
			modelValue:  reflect.New(modelType),
			modelObject: modelValue.Interface(),
			dsWriter:    s.DSWriter,
			Ready:       make(chan bool),
			Sinker:      s,
			// 如果找到了 model 定义，则一定是按照定义的 StrictSchema 来决定是使用 struct 还是 map 来反序列化
			strictSchema: modelTable.StrictSchema(),
		}
	} else {
		// 如果没有找到 model 定义，且 strict_schema=false, 则使用 map 来反序列化，自动根据字段名来写 db（没有 schema migrate）
		if !*s.RuntimeConfig.StrictSchema {
			fakeModel := &model.FakeModelForNoStrictSchema{}
			fakeModel.SetTableName(s.RuntimeConfig.ModelTable)
			fakeModel.SetOmitFields(s.RuntimeConfig.OmitFields)
			modelType := reflect.TypeOf(fakeModel).Elem()
			modelValue := reflect.New(modelType)
			handler = &AnySinker{
				dsWriter:     s.DSWriter,
				Ready:        make(chan bool),
				Sinker:       s,
				modelObject:  fakeModel,  // use to get table name
				modelType:    modelType,  //for not panic
				modelValue:   modelValue, // for not panic
				strictSchema: false,      // true
			}
		} else {
			return nil, fmt.Errorf("table [%s] is not registered to struct", s.RuntimeConfig.ModelTable)
		}
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
	brokerIps := strings.Split(s.MetaInfo.ClusterConfig.Brokers, ",")
	brokerAddrs := lo.Map(brokerIps, func(item string, index int) string {
		if strings.Contains(item, ":") {
			return item
		}
		return fmt.Sprintf("%s:%d", item, s.MetaInfo.ClusterConfig.Port)
	})
	group, err := sarama.NewConsumerGroup(brokerAddrs,
		groupId,
		consumerConfig,
	)
	if err != nil {
		slog.Error("create consumer", err)
		return nil, err
	}

	return group, nil
}
