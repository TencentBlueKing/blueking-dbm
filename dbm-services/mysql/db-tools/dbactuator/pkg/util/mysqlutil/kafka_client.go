/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil

import (
	"crypto/sha512"
	"fmt"

	"github.com/IBM/sarama"
	"github.com/xdg-go/scram"

	"dbm-services/common/go-pubpkg/logger"
)

var (
	SHA512 scram.HashGeneratorFcn = sha512.New
)

// XDGSCRAMClient todo
type XDGSCRAMClient struct {
	*scram.Client
	*scram.ClientConversation
	scram.HashGeneratorFcn
}

// Begin todo
func (x *XDGSCRAMClient) Begin(userName, password, authzID string) (err error) {
	x.Client, err = x.HashGeneratorFcn.NewClient(userName, password, authzID)
	if err != nil {
		return err
	}
	x.ClientConversation = x.Client.NewConversation()
	return nil
}

// Step todo
func (x *XDGSCRAMClient) Step(challenge string) (response string, err error) {
	response, err = x.ClientConversation.Step(challenge)
	return
}

// Done todo
func (x *XDGSCRAMClient) Done() bool {
	return x.ClientConversation.Done()
}

// KafkaCheck kakfa联通性校验
func KafkaCheck(targetHost string, targetPort int, user string, pwd string) (err error) {
	// 拼装连接参数
	broker := fmt.Sprintf("%s:%d", targetHost, targetPort)
	config := sarama.NewConfig()
	config.Net.SASL.Enable = true
	config.Net.SASL.User = user
	config.Net.SASL.Password = pwd
	config.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA512
	config.Net.SASL.Handshake = true
	config.Net.SASL.SCRAMClientGeneratorFunc =
		func() sarama.SCRAMClient { return &XDGSCRAMClient{HashGeneratorFcn: SHA512} }

	// 创建 Kafka 连接
	client, err := sarama.NewClient([]string{broker}, config)
	if err != nil {
		return fmt.Errorf("failed to connect to Kafka broker: %s", err.Error())
	}
	defer client.Close()
	logger.Info("Kafka [%s] connectivity test successful", broker)
	return nil

}
