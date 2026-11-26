// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

// SinkerConfig 一个入库项的配置。
// 默认值全部内置在代码里(builtin_sinkers.go)，启动时用 --enable-defaults 生成 data.defaults.yaml。
// yaml tag 上的 omitempty 只影响生成 data.defaults.yaml 时的输出(零值字段不输出，便于人工复制修改)，
// 不影响解析。
type SinkerConfig struct {
	Topic    string `yaml:"topic,omitempty"`
	BkDataId int    `yaml:"bk_data_id,omitempty"`
	// BkCollectorName collector_config_name_en
	BkCollectorName string `yaml:"bk_collector_name,omitempty"`

	ModelTable string `yaml:"model_table" validate:"required"`
	// StrictSchema default strict_schema=true, use defined model struct to unmarshal kafka msg
	// strict_schema=false: use map[string]interface{} to unmarshal kafka msg, and save to db.
	//    model_table is used as table_name, and need to be created manually
	StrictSchema *bool `yaml:"strict_schema,omitempty"`
	// SkipMigrateSchema do not run model_table migration change, only works when strict_schema=true
	SkipMigrateSchema bool `yaml:"skip_migrate_schema"`
	// OmitFields is used to omit fields when save to db
	//  only works when StrictSchema=false
	OmitFields *[]string `yaml:"omit_fields,omitempty"`
	// ClientIdSuffix is used to generate client_id: topic + client_id_suffix
	ClientIdSuffix string `yaml:"client_id_suffix,omitempty"`
	// GroupIdSuffix is used to generate group_id: topic + group_id_suffix
	GroupIdSuffix string `yaml:"group_id_suffix"`
	// FromBeginning consumer starts reading from the beginning of the topic.
	// default is the last committed offset, not from beginning
	FromBeginning bool `yaml:"from_beginning,omitempty"`
	// FetchMinBytes consumer fetch messages at least this size, default 1024 bytes
	FetchMinBytes int32 `yaml:"fetch_min_bytes,omitempty"`
	// SinkBatchSize 一次 fetch 可能有多条记录，sink_batch_size 控制多少次 fetch 合并成一次 sink. default 10
	SinkBatchSize int `yaml:"sink_batch_size,omitempty"`
	// WriteMode default is upsert, allowed: insert_ignore, insert, upsert
	WriteMode  string `yaml:"write_mode"`
	Datasource string `yaml:"datasource"`
	// IngestThreads 每个 partition 启动的并发写入 goroutine 数量。
	// 当为 0 或 1 时保持同步处理逻辑；当 > 1 时启用固定数量的 goroutine 并发处理消息
	IngestThreads int `yaml:"ingest_threads,omitempty"`
	// Enable 是否启用。默认是启用 true
	Enable *bool `yaml:"enable"`
}

// Key 入库项的唯一标识，用于 data.xxx.yaml 覆盖 data.defaults.yaml 里的同名项。
// 不用 topic/bk_collector_name 是因为它们在不同环境可能不一样(比如采集项改名)，
// 而 model_table 由代码定义，是稳定的。
func (s *SinkerConfig) Key() string {
	return s.ModelTable + "|" + s.GroupIdSuffix
}

// IsEnabled 是否启用，默认启用
func (s *SinkerConfig) IsEnabled() bool {
	return s.Enable == nil || *s.Enable
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

type BkmApiInfo struct {
	BkAppCode   string `yaml:"bk_app_code" json:"bk_app_code"`
	BkAppSecret string `yaml:"bk_app_secret" json:"bk_app_secret"`
	BkBizId     int    `yaml:"bk_biz_id" json:"bk_biz_id"`
	BkUsername  string `yaml:"bk_username" json:"bk_username"`
	// BkTicket    string `yaml:"bk_ticket" json:"bk_ticket"`
	// BkToken     string `yaml:"bk_token" json:"bk_token"`
	// BkmonitorApiUrl https://bk-monitor.xxx.com/prod/
	BkmonitorApiUrl string `yaml:"bkmonitor_api_url" json:"bkmonitor_api_url"`
	BklogApiUrl     string `yaml:"bklog_api_url" json:"bklog_api_url"`
}

type BkDataKafkaMeta struct {
	ClusterConfig struct {
		DomainName string `json:"domain_name" yaml:"domain_name"`
		Port       int    `json:"port" yaml:"port"`
	} `json:"cluster_config" yaml:"cluster_config"`
	StorageConfig struct {
		Topic     string `json:"topic" yaml:"topic"`
		Partition int    `json:"partition" yaml:"partition"`
	} `json:"storage_config" yaml:"storage_config"`
	AuthInfo struct {
		Username string `json:"username" yaml:"username"`
		Password string `json:"password" yaml:"password"`
		// SaslMechanisms like SCRAM-SHA-512
		SaslMechanisms string `json:"sasl_mechanisms" yaml:"sasl_mechanisms"`
		// SecurityProtocol like SASL_PLAINTEXT
		SecurityProtocol string `json:"security_protocol" yaml:"security_protocol"`
	} `json:"auth_info" yaml:"auth_info"`
}
