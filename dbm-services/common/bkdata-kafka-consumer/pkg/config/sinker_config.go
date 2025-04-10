// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

type SinkerConfig struct {
	BkDataId int `yaml:"bk_data_id"`
	// AltBroker can be nil
	AltBroker *string `yaml:"alt_broker"`
	ClientId  string  `yaml:"client_id"`
	// GroupId is the name of the consumer group, also used as config table mapping
	GroupId string `yaml:"group_id"`
	// FromBeginning consumer starts reading from the beginning of the topic.
	// default is the last committed offset, not from beginning
	FromBeginning bool `yaml:"from_beginning"`
	// FetchMinBytes consumer fetch messages at least this size, default 1024 bytes
	FetchMinBytes int32 `yaml:"fetch_min_bytes"`
	// SinkBatchSize 一次 fetch 可能有多条记录，sink_batch_size 控制多少次 fetch 合并成一次 sink. default 1
	SinkBatchSize int `yaml:"sink_batch_size"`
	Dsn           struct {
		User                   string                 `yaml:"user"`
		Password               string                 `yaml:"password"`
		Address                string                 `yaml:"address"`
		Database               string                 `yaml:"database"`
		Charset                string                 `yaml:"charset"`
		Table                  *string                `yaml:"table"`
		ConnectionPerPartition int                    `yaml:"connection_per_partition"`
		SessionVariables       map[string]interface{} `yaml:"session_variables"`
	} `yaml:"dsn"`
	KafkaMeta *KafkaMeta `yaml:"-"`
}
