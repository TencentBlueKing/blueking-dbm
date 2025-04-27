/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package entity

// Dependencies 定义集群运行时依赖的外部服务配置
type Dependencies struct {
	ExternalS3    *ExternalS3    `json:"externalS3,omitempty"`
	ExternalEtcd  *ExternalEtcd  `json:"externalEtcd,omitempty"`
	ExternalKafka *ExternalKafka `json:"externalKafka,omitempty"`
}

// ExternalS3 定义外部 S3 存储服务的连接配置
type ExternalS3 struct {
	Enabled        bool   `json:"enabled,omitempty"`
	Host           string `json:"host,omitempty"`
	Port           string `json:"port,omitempty"`
	AccessKey      string `json:"accessKey,omitempty"`
	SecretKey      string `json:"secretKey,omitempty"`
	UseSSL         bool   `json:"useSSL,omitempty"`
	BucketName     string `json:"bucketName,omitempty"`
	RootPath       string `json:"rootPath,omitempty"`
	UseIAM         bool   `json:"useIAM,omitempty"`
	CloudProvider  string `json:"cloudProvider,omitempty"`
	IamEndpoint    string `json:"iamEndpoint,omitempty"`
	Region         string `json:"region,omitempty"`
	UseVirtualHost bool   `json:"useVirtualHost,omitempty"`
}

// ExternalEtcd 定义外部 Etcd 服务的连接配置
type ExternalEtcd struct {
	Enabled   bool     `json:"enabled,omitempty"`
	Endpoints []string `json:"endpoints,omitempty"`
}

// ExternalKafka 定义外部 Kafka 消息队列的连接配置
type ExternalKafka struct {
	Enabled          bool   `json:"enabled,omitempty"`
	BrokerList       string `json:"brokerList,omitempty"`
	SecurityProtocol string `json:"securityProtocol,omitempty"`
	Sasl             Sasl   `json:"sasl,omitempty"`
}

// Sasl 定义Kafka SASL 认证的详细参数
type Sasl struct {
	Mechanisms string `json:"mechanisms,omitempty"`
	Username   string `json:"username,omitempty"`
	Password   string `json:"password,omitempty"`
}
