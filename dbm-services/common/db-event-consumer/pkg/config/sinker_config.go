// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

type SinkerConfig struct {
	Topic      string `yaml:"topic" validate:"required"`
	ModelTable string `yaml:"model_table" validate:"required"`
	// StrictSchema default strict_schema=true, use defined model struct to unmarshal kafka msg
	// strict_schema=false: use map[string]interface{} to unmarshal kafka msg, and save to db.
	//    model_table is used as table_name, and need to be created manually
	StrictSchema *bool `yaml:"strict_schema"`
	// SkipMigrateSchema do not run model_table migration change, only works when strict_schema=true
	SkipMigrateSchema bool `yaml:"skip_migrate_schema"`
	// OmitFields is used to omit fields when save to db
	//  only works when StrictSchema=false
	OmitFields *[]string `yaml:"omit_fields"`
	// ClientIdSuffix is used to generate client_id: topic + client_id_suffix
	ClientIdSuffix string `yaml:"client_id_suffix"`
	// GroupIdSuffix is used to generate group_id: topic + group_id_suffix
	GroupIdSuffix string `yaml:"group_id_suffix"`
	// FromBeginning consumer starts reading from the beginning of the topic.
	// default is the last committed offset, not from beginning
	FromBeginning bool `yaml:"from_beginning"`
	// FetchMinBytes consumer fetch messages at least this size, default 1024 bytes
	FetchMinBytes int32 `yaml:"fetch_min_bytes"`
	// SinkBatchSize 一次 fetch 可能有多条记录，sink_batch_size 控制多少次 fetch 合并成一次 sink. default 1
	SinkBatchSize int    `yaml:"sink_batch_size"`
	Datasource    string `yaml:"datasource"`

	KafkaMeta *KafkaMeta `yaml:"-"`
}

type KafkaMeta struct {
	ClusterConfig struct {
		// Brokers ip1:port,ip2:port,ip3:port
		Brokers string `json:"brokers" yaml:"brokers"`
		Port    int    `json:"port" yaml:"port"`
	} `json:"cluster_config" yaml:"cluster_config"`
	AuthInfo struct {
		Username string `json:"username" yaml:"username"`
		Password string `json:"password" yaml:"password"`
		// SaslMechanisms like SCRAM-SHA-512
		SaslMechanisms string `json:"sasl_mechanisms" yaml:"sasl_mechanisms"`
		// SecurityProtocol like SASL_PLAINTEXT
		SecurityProtocol string `json:"security_protocol" yaml:"security_protocol"`
	} `json:"auth_info" yaml:"auth_info"`
}
