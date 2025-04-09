// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

type KafkaMeta struct {
	ClusterConfig struct {
		DomainName string `json:"domain_name"`
		Port       int    `json:"port"`
	} `json:"cluster_config"`
	StorageConfig struct {
		Topic     string `json:"topic"`
		Partition int    `json:"partition"`
	} `json:"storage_config"`
	AuthInfo struct {
		Username string `json:"username"`
		Password string `json:"password"`
		// SaslMechanisms like SCRAM-SHA-512
		SaslMechanisms string `json:"sasl_mechanisms"`
		// SecurityProtocol like SASL_PLAINTEXT
		SecurityProtocol string `json:"security_protocol"`
	} `json:"auth_info"`
}
