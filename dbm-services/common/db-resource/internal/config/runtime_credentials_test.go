/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package config

import (
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"dbm-services/common/go-pubpkg/kms"
	"dbm-services/common/go-pubpkg/kms/testhelper"
)

const testDocument = `{"bkapp_id_secret":{"default":{"app_code":"test-code","app_secret":"test-secret"}},"mysql":{"dbResource":{"username":"user@tenant","password":" pass!@#:%/ "},"dbm":{"username":"cmdb-user","password":"cmdb-pass"}},"redis":{"default":{"password":"redis-pass"}},"unrelated":{"token":"ignored"}}`

func resetCredentials(t *testing.T) {
	t.Helper()
	runtimeCredentials.Once = sync.Once{}
	runtimeCredentials.value = nil
	runtimeCredentials.err = nil
	t.Cleanup(func() {
		runtimeCredentials.Once = sync.Once{}
		runtimeCredentials.value = nil
		runtimeCredentials.err = nil
	})
}

func TestLoadRuntimeCredentialsSnapshot(t *testing.T) {
	for _, projected := range []bool{false, true} {
		t.Run(map[bool]string{false: "directory", true: "projected-secret"}[projected], func(t *testing.T) {
			resetCredentials(t)
			envelope, privateKey := testhelper.Envelope(t, testDocument)
			dir := t.TempDir()
			dataDir := dir
			if projected {
				dataDir = filepath.Join(dir, "generation")
				if err := os.Mkdir(dataDir, 0700); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink("generation", filepath.Join(dir, "..data")); err != nil {
					t.Fatal(err)
				}
			}
			path := filepath.Join(dataDir, "envelope")
			if err := os.WriteFile(path, []byte(envelope+"\n"), 0600); err != nil {
				t.Fatal(err)
			}
			t.Setenv(kms.EnabledEnv, "true")
			t.Setenv("DB_RESOURCE_KMS_CREDENTIAL_DIR", dir)
			t.Setenv(kms.PrivateKeyEnv, privateKey)
			got, err := LoadRuntimeCredentials()
			if err != nil {
				t.Fatal(err)
			}
			if got.MySQL.DbResource.Username != "user@tenant" || got.MySQL.DbResource.Password != " pass!@#:%/ " ||
				got.MySQL.Dbm.Username != "cmdb-user" || got.MySQL.Dbm.Password != "cmdb-pass" ||
				got.BkAppIDSecret.Default.AppCode != "test-code" || got.BkAppIDSecret.Default.AppSecret != "test-secret" ||
				got.Redis.Default.Password != "redis-pass" {
				t.Fatal("credentials were not preserved")
			}
			if err := os.WriteFile(path, []byte("invalid replacement"), 0600); err != nil {
				t.Fatal(err)
			}
			cached, err := LoadRuntimeCredentials()
			if err != nil || cached != got {
				t.Fatal("startup snapshot changed")
			}
		})
	}
}

func TestKMSGatingAndErrors(t *testing.T) {
	for _, flag := range []string{"", "false", "TRUE", "1", "true"} {
		t.Run("enabled="+flag, func(t *testing.T) {
			resetCredentials(t)
			t.Setenv(kms.EnabledEnv, flag)
			t.Setenv(kms.PrivateKeyEnv, "")
			t.Setenv("DB_RESOURCE_KMS_CREDENTIAL_DIR", "")
			got, err := LoadRuntimeCredentials()
			if flag == "" || flag == "false" {
				if got != nil || err != nil {
					t.Fatal("disabled KMS should not read credentials")
				}
			} else if err == nil {
				t.Fatal("invalid or incomplete KMS config accepted")
			}
		})
	}
	for _, input := range []string{"", "secret-input-marker", base64.StdEncoding.EncodeToString([]byte(`{"asymmetric_type":"secret-input-marker"}`))} {
		t.Run("invalid-envelope", func(t *testing.T) {
			resetCredentials(t)
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(input), 0600); err != nil {
				t.Fatal(err)
			}
			t.Setenv(kms.EnabledEnv, "true")
			t.Setenv("DB_RESOURCE_KMS_CREDENTIAL_DIR", dir)
			t.Setenv(kms.PrivateKeyEnv, "private-key-marker")
			got, err := LoadRuntimeCredentials()
			if got != nil || err == nil {
				t.Fatal("invalid envelope accepted")
			}
			if strings.Contains(err.Error(), "marker") {
				t.Fatal("error leaked input")
			}
		})
	}
}

func TestCredentialDocumentValidation(t *testing.T) {
	for _, group := range []string{"dbResource", "dbm"} {
		for _, field := range []string{"username", "password"} {
			var document map[string]any
			if err := json.Unmarshal([]byte(testDocument), &document); err != nil {
				t.Fatal(err)
			}
			document["mysql"].(map[string]any)[group].(map[string]any)[field] = "  "
			raw, err := json.Marshal(document)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := parseRuntimeCredentials(string(raw)); err == nil || !strings.Contains(err.Error(), field) {
				t.Fatalf("missing validation for mysql.%s.%s", group, field)
			}
		}
	}
	for _, field := range []string{"app_code", "app_secret"} {
		var document map[string]any
		if err := json.Unmarshal([]byte(testDocument), &document); err != nil {
			t.Fatal(err)
		}
		group := document["bkapp_id_secret"].(map[string]any)["default"].(map[string]any)
		group[field] = "  "
		raw, err := json.Marshal(document)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := parseRuntimeCredentials(string(raw)); err == nil || !strings.Contains(err.Error(), field) {
			t.Fatalf("missing validation for bkapp_id_secret.default.%s", field)
		}
	}
	for _, field := range []string{"password"} {
		var document map[string]any
		if err := json.Unmarshal([]byte(testDocument), &document); err != nil {
			t.Fatal(err)
		}
		group := document["redis"].(map[string]any)["default"].(map[string]any)
		group[field] = "  "
		raw, err := json.Marshal(document)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := parseRuntimeCredentials(string(raw)); err == nil || !strings.Contains(err.Error(), field) {
			t.Fatal("missing validation for redis.default.password")
		}
	}
	for _, input := range []string{`null`, `{}`, `{"mysql":{"dbResource":{"password":123}}}`, `{"secret-marker":`} {
		if _, err := parseRuntimeCredentials(input); err == nil || strings.Contains(err.Error(), "secret-marker") {
			t.Fatal("invalid document accepted or leaked")
		}
	}
}

func TestMissingCredentialInputs(t *testing.T) {
	for _, missing := range []string{"private-key", "directory", "envelope"} {
		t.Run(missing, func(t *testing.T) {
			resetCredentials(t)
			t.Setenv(kms.EnabledEnv, "true")
			t.Setenv(kms.PrivateKeyEnv, "dummy-key")
			t.Setenv("DB_RESOURCE_KMS_CREDENTIAL_DIR", t.TempDir())
			if missing == "private-key" {
				t.Setenv(kms.PrivateKeyEnv, "")
			}
			if missing == "directory" {
				t.Setenv("DB_RESOURCE_KMS_CREDENTIAL_DIR", "")
			}
			if got, err := LoadRuntimeCredentials(); got != nil || err == nil {
				t.Fatal("missing input accepted")
			}
		})
	}
}

// TestApplyRuntimeCredentials 验证覆盖语义：凭证被无条件覆盖（包括占位符场景），
// 非凭证配置（地址、库名、连接池参数、用户名等其他字段）保留原值。
func TestApplyRuntimeCredentials(t *testing.T) {
	cfg := Config{
		Db: Db{
			Name:         "db_resource",
			Addr:         "mysql:3306",
			UserName:     "kms-managed",
			PassWord:     "kms-managed",
			MaxOpenConns: 100,
			MaxIdleConns: 10,
			MaxLifetime:  2,
		},
		CmdbDb: Db{
			Name:     "dbm",
			Addr:     "mysql:3306",
			UserName: "kms-managed",
			PassWord: "kms-managed",
		},
		BkSecretConfig: BkSecretConfig{
			BkAppCode:   "kms-managed",
			BKAppSecret: "kms-managed",
			BkUserName:  "admin",
			BkBaseUrl:   "http://bk-api",
		},
		Redis: Redis{
			Addr:     "redis:6379",
			Password: "kms-managed",
		},
	}
	credentials, err := parseRuntimeCredentials(testDocument)
	if err != nil {
		t.Fatal(err)
	}
	applyRuntimeCredentials(&cfg, credentials)

	if cfg.Db.UserName != "user@tenant" || cfg.Db.PassWord != " pass!@#:%/ " {
		t.Fatal("mysql.dbResource credentials were not applied")
	}
	if cfg.CmdbDb.UserName != "cmdb-user" || cfg.CmdbDb.PassWord != "cmdb-pass" {
		t.Fatal("mysql.dbm credentials were not applied")
	}
	if cfg.BkSecretConfig.BkAppCode != "test-code" || cfg.BkSecretConfig.BKAppSecret != "test-secret" {
		t.Fatal("bkapp_id_secret credentials were not applied")
	}
	if cfg.Redis.Password != "redis-pass" {
		t.Fatal("redis password was not applied")
	}
	if cfg.Db.Name != "db_resource" || cfg.Db.Addr != "mysql:3306" ||
		cfg.Db.MaxOpenConns != 100 || cfg.Db.MaxIdleConns != 10 || cfg.Db.MaxLifetime != 2 {
		t.Fatal("db connection settings were modified")
	}
	if cfg.CmdbDb.Name != "dbm" || cfg.CmdbDb.Addr != "mysql:3306" {
		t.Fatal("cmdb_db connection settings were modified")
	}
	if cfg.BkSecretConfig.BkUserName != "admin" || cfg.BkSecretConfig.BkBaseUrl != "http://bk-api" {
		t.Fatal("bkSecretConfig non-credential fields were modified")
	}
	if cfg.Redis.Addr != "redis:6379" {
		t.Fatal("redis address was modified")
	}
}
