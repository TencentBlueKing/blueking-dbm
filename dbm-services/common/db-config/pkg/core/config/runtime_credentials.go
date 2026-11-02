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

	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/kms"
)

var kmsOptions = kms.LoadOptions{
	CredentialDirEnv: "DBCONFIG_KMS_CREDENTIAL_DIR",
}

// RuntimeCredentials 只声明本服务实际消费的信封字段；共享信封允许包含其他服务的未知字段。
// JSON tag 与共享信封结构保持一致。
type RuntimeCredentials struct {
	BkAppIdSecret struct {
		Default struct {
			AppSecret string `json:"app_secret"`
		} `json:"default"`
	} `json:"bkapp_id_secret"`
	MySQL struct {
		DbConfig struct {
			Username string `json:"username"`
			Password string `json:"password"`
		} `json:"dbConfig"`
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
		{"bkapp_id_secret.default.app_secret", credentials.BkAppIdSecret.Default.AppSecret},
		{"mysql.dbConfig.username", credentials.MySQL.DbConfig.Username},
		{"mysql.dbConfig.password", credentials.MySQL.DbConfig.Password},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}
	return &credentials, nil
}

// ApplyKMSCredentials 在 config.yaml 加载之后、建立数据库连接之前调用。
// KMS 关闭时不做任何修改；开启后加载失败返回错误，调用方应停止启动，不回退配置文件中的旧凭证。
func ApplyKMSCredentials() (bool, error) {
	credentials, err := LoadRuntimeCredentials()
	if err != nil || credentials == nil {
		return false, err
	}
	applyRuntimeCredentials(viper.GetViper(), credentials)
	return true, nil
}

// applyRuntimeCredentials 通过 viper.Set 覆盖 db.username / db.password / encrypt.keyPrefix，
// 优先级高于配置文件与环境变量。db.addr、db.name 等非敏感配置保留原值。
// encrypt.keyPrefix 即 bk_app_secret，用作敏感配置项加解密的密钥前缀。
func applyRuntimeCredentials(v *viper.Viper, credentials *RuntimeCredentials) {
	v.Set("db.username", credentials.MySQL.DbConfig.Username)
	v.Set("db.password", credentials.MySQL.DbConfig.Password)
	v.Set("encrypt.keyPrefix", credentials.BkAppIdSecret.Default.AppSecret)
}
