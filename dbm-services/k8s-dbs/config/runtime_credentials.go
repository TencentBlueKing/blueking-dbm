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

package config

import (
	"dbm-services/common/go-pubpkg/kms"
	"sync"
)

var kmsOptions = kms.LoadOptions{
	CredentialDirEnv: "K8S_DBS_KMS_CREDENTIAL_DIR",
}

// RuntimeCredentials contains only the credentials consumed by k8s-dbs.
// Unknown fields are allowed because the envelope is shared with other DBM services.
type RuntimeCredentials struct {
	BkAppIDSecret struct {
		Default struct {
			AppCode   string `json:"app_code"`
			AppSecret string `json:"app_secret"`
		} `json:"default"`
	} `json:"bkapp_id_secret"`
	MySQL struct {
		K8sDbs struct {
			Username string `json:"username"`
			Password string `json:"password"`
		} `json:"k8sDbs"`
	} `json:"mysql"`
}

var runtimeCredentials struct {
	sync.Once
	value *RuntimeCredentials
	err   error
}

// LoadRuntimeCredentials decrypts and validates one startup snapshot. When KMS
// is disabled, callers retain their existing environment configuration.
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
		{"mysql.k8sDbs.username", credentials.MySQL.K8sDbs.Username},
		{"mysql.k8sDbs.password", credentials.MySQL.K8sDbs.Password},
		{"bkapp_id_secret.default.app_code", credentials.BkAppIDSecret.Default.AppCode},
		{"bkapp_id_secret.default.app_secret", credentials.BkAppIDSecret.Default.AppSecret},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}
	return &credentials, nil
}
