// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"sync"

	"dbm-services/common/go-pubpkg/kms"
)

var kmsOptions = kms.LoadOptions{
	CredentialDirEnv: "BACKUP_CONSUMER_KMS_CREDENTIAL_DIR",
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
		BackupServer struct {
			Username string `json:"username"`
			Password string `json:"password"`
		} `json:"backupServer"`
	} `json:"mysql"`
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
		{"mysql.backupServer.username", credentials.MySQL.BackupServer.Username},
		{"mysql.backupServer.password", credentials.MySQL.BackupServer.Password},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}
	return &credentials, nil
}

// ApplyRuntimeCredentials 用校验通过的凭证无条件覆盖内存配置中的账号密码与 app_secret。
// 地址、库名、表名、API 地址、bk_data_id 等非敏感配置保留原值。
func ApplyRuntimeCredentials(cfg *runtimeConfig, credentials *RuntimeCredentials) {
	cfg.BkAppCode = credentials.BkAppIdSecret.Default.AppCode
	cfg.BkAppSecret = credentials.BkAppIdSecret.Default.AppSecret
	cfg.Dsn.User = credentials.MySQL.BackupServer.Username
	cfg.Dsn.Password = credentials.MySQL.BackupServer.Password
}
