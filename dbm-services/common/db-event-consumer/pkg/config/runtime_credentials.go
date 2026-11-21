// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"fmt"
	"sync"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/common/go-pubpkg/kms"
)

var kmsOptions = kms.LoadOptions{
	CredentialDirEnv: "DB_EVENT_CONSUMER_KMS_CREDENTIAL_DIR",
}

// datasource 关联的 KMS mysql 凭证名称
const (
	KMSCredentialDbmReport = "dbmReport"
	KMSCredentialDbmStats  = "dbmStats"
)

// defaultDatasourceCredentials 是 ConfigMap 模板中固定 datasource 名称到 KMS mysql 凭证的映射。
// 自定义 datasource 可在 datasource.yaml 中通过 kms_credential 显式指定。
var defaultDatasourceCredentials = map[string]string{
	"prod_bk_dbm_report":      KMSCredentialDbmReport,
	"prod_bk_dbm_report_raw":  KMSCredentialDbmReport,
	"mysql_bk_dbm_stats":      KMSCredentialDbmStats,
	"doris_bk_dbm_stats":      KMSCredentialDbmStats,
	"doris_http_bk_dbm_stats": KMSCredentialDbmStats,
}

type userPassword struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// RuntimeCredentials 只声明本服务实际消费的信封字段；共享信封允许包含其他服务的未知字段。
// JSON tag 与共享信封结构保持一致。
type RuntimeCredentials struct {
	BkAppIdSecret struct {
		Default struct {
			AppCode   string `json:"app_code"`
			AppSecret string `json:"app_secret"`
		} `json:"default"`
	} `json:"bkapp_id_secret"`
	MySQL struct {
		DbmReport userPassword `json:"dbmReport"`
		DbmStats  userPassword `json:"dbmStats"`
	} `json:"mysql"`
	Kafka struct {
		Default userPassword `json:"default"`
	} `json:"kafka"`
	BkMonitor struct {
		Default struct {
			BkmDbmToken string `json:"bkm_dbm_token"`
		} `json:"default"`
	} `json:"bkmonitor"`
}

func (c *RuntimeCredentials) mysqlCredential(name string) (userPassword, bool) {
	switch name {
	case KMSCredentialDbmReport:
		return c.MySQL.DbmReport, true
	case KMSCredentialDbmStats:
		return c.MySQL.DbmStats, true
	default:
		return userPassword{}, false
	}
}

var runtimeCredentials struct {
	sync.Once
	value *RuntimeCredentials
	err   error
}

// LoadRuntimeCredentials 解密并校验一份启动凭证快照。KMS 关闭时返回 (nil, nil)，
// 调用方继续使用原配置中的凭证；开启后任何加载或校验失败都返回错误。
// sync.Once 保证整个进程只解密一次。
func LoadRuntimeCredentials() (*RuntimeCredentials, error) {
	enabled, err := kms.Enabled()
	if err != nil || !enabled {
		return nil, err
	}
	runtimeCredentials.Do(func() {
		runtimeCredentials.value, runtimeCredentials.err = loadRuntimeCredentials()
	})
	return runtimeCredentials.value, runtimeCredentials.err
}

func loadRuntimeCredentials() (*RuntimeCredentials, error) {
	plaintext, enabled, err := kms.LoadEnvelope(kmsOptions)
	if err != nil || !enabled {
		return nil, err
	}
	return parseRuntimeCredentials(plaintext)
}

func parseRuntimeCredentials(plaintext string) (*RuntimeCredentials, error) {
	var credentials RuntimeCredentials
	if err := kms.DecodeJSON(plaintext, &credentials); err != nil {
		return nil, err
	}
	for _, field := range []struct{ name, value string }{
		{"bkapp_id_secret.default.app_code", credentials.BkAppIdSecret.Default.AppCode},
		{"bkapp_id_secret.default.app_secret", credentials.BkAppIdSecret.Default.AppSecret},
		{"mysql.dbmReport.username", credentials.MySQL.DbmReport.Username},
		{"mysql.dbmReport.password", credentials.MySQL.DbmReport.Password},
		{"mysql.dbmStats.username", credentials.MySQL.DbmStats.Username},
		{"mysql.dbmStats.password", credentials.MySQL.DbmStats.Password},
		{"kafka.default.username", credentials.Kafka.Default.Username},
		{"kafka.default.password", credentials.Kafka.Default.Password},
		{"bkmonitor.default.bkm_dbm_token", credentials.BkMonitor.Default.BkmDbmToken},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}
	return &credentials, nil
}

// ApplyRuntimeCredentials 用校验通过的凭证无条件覆盖 config.yaml 中的账号密码与 token。
// broker 地址、端口、SASL 机制、上报地址、data_id、业务 ID、API 地址等非敏感配置保留原值。
func ApplyRuntimeCredentials(cfg *mainConfig, credentials *RuntimeCredentials) {
	if cfg.KafkaInfo == nil {
		cfg.KafkaInfo = &KafkaMeta{}
	}
	cfg.KafkaInfo.AuthInfo.Username = credentials.Kafka.Default.Username
	cfg.KafkaInfo.AuthInfo.Password = credentials.Kafka.Default.Password

	if cfg.BkmApiInfo == nil {
		cfg.BkmApiInfo = &BkmApiInfo{}
	}
	cfg.BkmApiInfo.BkAppCode = credentials.BkAppIdSecret.Default.AppCode
	cfg.BkmApiInfo.BkAppSecret = credentials.BkAppIdSecret.Default.AppSecret

	if cfg.BkmReport == nil {
		cfg.BkmReport = &base.BKReportConfig{}
	}
	cfg.BkmReport.Token = credentials.BkMonitor.Default.BkmDbmToken
}

// ApplyDatasourceCredentials 用 KMS mysql 凭证覆盖 datasource.yaml 中每个 datasource 的 user/password。
// 映射优先取 datasource 的 kms_credential，未指定时按模板内置的 datasource 名称映射。
// 开启 KMS 后存在无法映射的 datasource 时直接返回错误，避免继续使用 ConfigMap 中的占位符或旧凭证。
func ApplyDatasourceCredentials(datasources map[string]*sinker.Datasource, credentials *RuntimeCredentials) error {
	for name, ds := range datasources {
		if ds == nil {
			continue
		}
		credentialName := ds.KMSCredential
		if credentialName == "" {
			credentialName = defaultDatasourceCredentials[name]
		}
		if credentialName == "" {
			return fmt.Errorf("datasource %s has no KMS credential mapping, please set kms_credential", name)
		}
		cred, ok := credentials.mysqlCredential(credentialName)
		if !ok {
			return fmt.Errorf("datasource %s has unsupported kms_credential %s", name, credentialName)
		}
		if ds.Dsn == nil {
			ds.Dsn = make(map[string]interface{})
		}
		ds.Dsn["user"] = cred.Username
		ds.Dsn["password"] = cred.Password
	}
	return nil
}
