// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

type SinkerConfig struct {
	BkDataId      int     `yaml:"bk_data_id"`
	AltBroker     *string `yaml:"alt_broker"`
	ClientId      string  `yaml:"client_id"`
	GroupId       string  `yaml:"group_id"`
	FromBeginning bool    `yaml:"from_beginning"`
	Dsn           struct {
		User                   string  `yaml:"user"`
		Password               string  `yaml:"password"`
		Address                string  `yaml:"address"`
		Database               string  `yaml:"database"`
		Charset                string  `yaml:"charset"`
		Table                  *string `yaml:"table"`
		ConnectionPerPartition int     `yaml:"connection_per_partition"`
		BatchInserts           int     `yaml:"batch_inserts"`
	} `yaml:"dsn"`
	KafkaMeta *KafkaMeta `yaml:"-"`
}
