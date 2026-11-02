// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

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

const credentialDirEnv = "BACKUP_CONSUMER_KMS_CREDENTIAL_DIR"

const testDocument = `{"bkapp_id_secret":{"default":{"app_code":"app-code","app_secret":"app-secret"}},` +
	`"mysql":{"backupServer":{"username":"backup-user","password":" pass!@#:%/ "},` +
	`"dbm":{"username":"other","password":"other"}},` +
	`"redis":{"default":{"password":"ignored"}},` +
	`"unrelated":{"token":"ignored"}}`

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
			t.Setenv(credentialDirEnv, dir)
			t.Setenv(kms.PrivateKeyEnv, privateKey)
			got, err := LoadRuntimeCredentials()
			if err != nil {
				t.Fatal(err)
			}
			if got.MySQL.BackupServer.Username != "backup-user" || got.MySQL.BackupServer.Password != " pass!@#:%/ " ||
				got.BkAppIdSecret.Default.AppCode != "app-code" || got.BkAppIdSecret.Default.AppSecret != "app-secret" {
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
			t.Setenv(credentialDirEnv, "")
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
	for _, input := range []string{"", "secret-input-marker",
		base64.StdEncoding.EncodeToString([]byte(`{"asymmetric_type":"secret-input-marker"}`))} {
		t.Run("invalid-envelope", func(t *testing.T) {
			resetCredentials(t)
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(input), 0600); err != nil {
				t.Fatal(err)
			}
			t.Setenv(kms.EnabledEnv, "true")
			t.Setenv(credentialDirEnv, dir)
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
	for _, path := range [][]string{
		{"bkapp_id_secret", "default", "app_code"},
		{"bkapp_id_secret", "default", "app_secret"},
		{"mysql", "backupServer", "username"},
		{"mysql", "backupServer", "password"},
	} {
		for _, mutate := range []string{"blank", "missing"} {
			var document map[string]any
			if err := json.Unmarshal([]byte(testDocument), &document); err != nil {
				t.Fatal(err)
			}
			group := document[path[0]].(map[string]any)[path[1]].(map[string]any)
			if mutate == "blank" {
				group[path[2]] = "  "
			} else {
				delete(group, path[2])
			}
			raw, err := json.Marshal(document)
			if err != nil {
				t.Fatal(err)
			}
			name := strings.Join(path, ".")
			if _, err := parseRuntimeCredentials(string(raw)); err == nil || !strings.Contains(err.Error(), name) {
				t.Fatalf("missing validation for %s (%s)", name, mutate)
			}
		}
	}
	for _, input := range []string{`null`, `{}`, `{"mysql":{"backupServer":{"password":123}}}`, `{"secret-marker":`} {
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
			t.Setenv(credentialDirEnv, t.TempDir())
			if missing == "private-key" {
				t.Setenv(kms.PrivateKeyEnv, "")
			}
			if missing == "directory" {
				t.Setenv(credentialDirEnv, "")
			}
			if got, err := LoadRuntimeCredentials(); got != nil || err == nil {
				t.Fatal("missing input accepted")
			}
		})
	}
}

// TestApplyRuntimeCredentials 验证覆盖语义：凭证被无条件覆盖（包括占位符场景），非凭证配置保留原值。
func TestApplyRuntimeCredentials(t *testing.T) {
	table := "tb_backup_tasklist"
	cfg := runtimeConfig{
		BkmApiInfo: BkmApiInfo{
			BkAppCode:       "kms-managed",
			BkAppSecret:     "kms-managed",
			BkBizId:         100,
			BkUsername:      "admin",
			BkmonitorApiUrl: "http://bkmonitor",
			BklogApiUrl:     "http://bklog",
		},
		BkDataId:        1000,
		BkCollectorName: "backup_stm_log",
		ClientId:        "backup-stm",
		GroupId:         "backup-stm",
	}
	cfg.Dsn.User = "kms-managed"
	cfg.Dsn.Password = "kms-managed"
	cfg.Dsn.Address = "db:3306"
	cfg.Dsn.Database = "bk_dbm_backup_server"
	cfg.Dsn.Charset = "utf8mb4"
	cfg.Dsn.Table = &table
	cfg.Dsn.ConnectionPerPartition = 2

	credentials, err := parseRuntimeCredentials(testDocument)
	if err != nil {
		t.Fatal(err)
	}
	ApplyRuntimeCredentials(&cfg, credentials)

	if cfg.Dsn.User != "backup-user" || cfg.Dsn.Password != " pass!@#:%/ " {
		t.Fatal("mysql.backupServer credentials were not applied")
	}
	if cfg.BkAppCode != "app-code" || cfg.BkAppSecret != "app-secret" {
		t.Fatal("bkapp credentials were not applied")
	}
	if cfg.Dsn.Address != "db:3306" || cfg.Dsn.Database != "bk_dbm_backup_server" || cfg.Dsn.Charset != "utf8mb4" ||
		cfg.Dsn.Table != &table || cfg.Dsn.ConnectionPerPartition != 2 {
		t.Fatal("dsn non-credential fields were modified")
	}
	if cfg.BkBizId != 100 || cfg.BkUsername != "admin" || cfg.BkmonitorApiUrl != "http://bkmonitor" ||
		cfg.BklogApiUrl != "http://bklog" || cfg.BkDataId != 1000 || cfg.BkCollectorName != "backup_stm_log" ||
		cfg.ClientId != "backup-stm" || cfg.GroupId != "backup-stm" {
		t.Fatal("non-credential fields were modified")
	}
}
