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

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/common/go-pubpkg/kms"
	"dbm-services/common/go-pubpkg/kms/testhelper"
)

const credentialDirEnv = "DB_EVENT_CONSUMER_KMS_CREDENTIAL_DIR"

const testDocument = `{"bkapp_id_secret":{"default":{"app_code":"app-code","app_secret":"app-secret"}},` +
	`"mysql":{"dbmReport":{"username":"report-user","password":" pass!@#:%/ "},` +
	`"dbmStats":{"username":"stats-user","password":"stats-pass"},` +
	`"dbm":{"username":"other","password":"other"}},` +
	`"kafka":{"default":{"username":"kafka-user","password":"kafka-pass"}},` +
	`"bkmonitor":{"default":{"bkm_dbm_token":"bkm-token"}},` +
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
			if got.MySQL.DbmReport.Username != "report-user" || got.MySQL.DbmReport.Password != " pass!@#:%/ " ||
				got.MySQL.DbmStats.Username != "stats-user" || got.MySQL.DbmStats.Password != "stats-pass" ||
				got.Kafka.Default.Username != "kafka-user" || got.Kafka.Default.Password != "kafka-pass" ||
				got.BkAppIdSecret.Default.AppCode != "app-code" || got.BkAppIdSecret.Default.AppSecret != "app-secret" ||
				got.BkMonitor.Default.BkmDbmToken != "bkm-token" {
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
		{"mysql", "dbmReport", "username"},
		{"mysql", "dbmReport", "password"},
		{"mysql", "dbmStats", "username"},
		{"mysql", "dbmStats", "password"},
		{"kafka", "default", "username"},
		{"kafka", "default", "password"},
		{"bkmonitor", "default", "bkm_dbm_token"},
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
	for _, input := range []string{`null`, `{}`, `{"mysql":{"dbmReport":{"password":123}}}`, `{"secret-marker":`} {
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
	cfg := mainConfig{
		KafkaInfo: &KafkaMeta{},
		BkmApiInfo: &BkmApiInfo{
			BkAppCode:       "kms-managed",
			BkAppSecret:     "kms-managed",
			BkBizId:         100,
			BkUsername:      "admin",
			BkmonitorApiUrl: "http://bkmonitor",
			BklogApiUrl:     "http://bklog",
		},
		BkmReport: &base.BKReportConfig{Token: "kms-managed", DataID: 1, ReportUrl: "http://report"},
		OtelPort:  8000,
	}
	cfg.KafkaInfo.ClusterConfig.Brokers = "kafka"
	cfg.KafkaInfo.ClusterConfig.Port = 9092
	cfg.KafkaInfo.AuthInfo.Username = "kms-managed"
	cfg.KafkaInfo.AuthInfo.Password = "kms-managed"
	cfg.KafkaInfo.AuthInfo.SaslMechanisms = "SCRAM-SHA-512"
	cfg.KafkaInfo.AuthInfo.SecurityProtocol = "SASL_PLAINTEXT"

	credentials, err := parseRuntimeCredentials(testDocument)
	if err != nil {
		t.Fatal(err)
	}
	ApplyRuntimeCredentials(&cfg, credentials)

	if cfg.KafkaInfo.AuthInfo.Username != "kafka-user" || cfg.KafkaInfo.AuthInfo.Password != "kafka-pass" {
		t.Fatal("kafka credentials were not applied")
	}
	if cfg.BkmApiInfo.BkAppCode != "app-code" || cfg.BkmApiInfo.BkAppSecret != "app-secret" {
		t.Fatal("bkapp credentials were not applied")
	}
	if cfg.BkmReport.Token != "bkm-token" {
		t.Fatal("bkmonitor token was not applied")
	}
	if cfg.KafkaInfo.ClusterConfig.Brokers != "kafka" || cfg.KafkaInfo.ClusterConfig.Port != 9092 ||
		cfg.KafkaInfo.AuthInfo.SaslMechanisms != "SCRAM-SHA-512" ||
		cfg.KafkaInfo.AuthInfo.SecurityProtocol != "SASL_PLAINTEXT" {
		t.Fatal("kafka non-credential fields were modified")
	}
	if cfg.BkmApiInfo.BkBizId != 100 || cfg.BkmApiInfo.BkUsername != "admin" ||
		cfg.BkmApiInfo.BkmonitorApiUrl != "http://bkmonitor" || cfg.BkmApiInfo.BklogApiUrl != "http://bklog" {
		t.Fatal("bkm_api_info non-credential fields were modified")
	}
	if cfg.BkmReport.DataID != 1 || cfg.BkmReport.ReportUrl != "http://report" || cfg.OtelPort != 8000 {
		t.Fatal("bkm_report non-credential fields were modified")
	}
}

func TestApplyDatasourceCredentials(t *testing.T) {
	credentials, err := parseRuntimeCredentials(testDocument)
	if err != nil {
		t.Fatal(err)
	}
	newDsn := func() map[string]interface{} {
		return map[string]interface{}{
			"address": "db:3306", "user": "kms-managed", "password": "kms-managed",
			"database": "db", "charset": "utf8mb4",
		}
	}
	datasources := map[string]*sinker.Datasource{
		"prod_bk_dbm_report":      {Name: "prod_bk_dbm_report", Type: "mysql", Dsn: newDsn()},
		"prod_bk_dbm_report_raw":  {Name: "prod_bk_dbm_report_raw", Type: "mysql_raw", Dsn: newDsn()},
		"mysql_bk_dbm_stats":      {Name: "mysql_bk_dbm_stats", Type: "mysql", Dsn: newDsn()},
		"doris_bk_dbm_stats":      {Name: "doris_bk_dbm_stats", Type: "doris", Dsn: newDsn()},
		"doris_http_bk_dbm_stats": {Name: "doris_http_bk_dbm_stats", Type: "doris_http", Dsn: newDsn()},
		"custom_stats": {Name: "custom_stats", Type: "doris", Dsn: newDsn(),
			KMSCredential: KMSCredentialDbmStats},
		"prod_bk_dbm_report_override": {Name: "prod_bk_dbm_report_override", Type: "mysql", Dsn: newDsn(),
			KMSCredential: KMSCredentialDbmReport},
	}
	if err := ApplyDatasourceCredentials(datasources, credentials); err != nil {
		t.Fatal(err)
	}
	expect := map[string][2]string{
		"prod_bk_dbm_report":          {"report-user", " pass!@#:%/ "},
		"prod_bk_dbm_report_raw":      {"report-user", " pass!@#:%/ "},
		"prod_bk_dbm_report_override": {"report-user", " pass!@#:%/ "},
		"mysql_bk_dbm_stats":          {"stats-user", "stats-pass"},
		"doris_bk_dbm_stats":          {"stats-user", "stats-pass"},
		"doris_http_bk_dbm_stats":     {"stats-user", "stats-pass"},
		"custom_stats":                {"stats-user", "stats-pass"},
	}
	for name, want := range expect {
		dsn := datasources[name].Dsn
		if dsn["user"] != want[0] || dsn["password"] != want[1] {
			t.Fatalf("datasource %s credentials were not applied", name)
		}
		if dsn["address"] != "db:3306" || dsn["database"] != "db" || dsn["charset"] != "utf8mb4" {
			t.Fatalf("datasource %s non-credential fields were modified", name)
		}
	}

	for _, ds := range []*sinker.Datasource{
		{Name: "unknown_ds", Type: "mysql", Dsn: newDsn()},
		{Name: "bad_ds", Type: "mysql", Dsn: newDsn(), KMSCredential: "dbm"},
	} {
		err := ApplyDatasourceCredentials(map[string]*sinker.Datasource{ds.Name: ds}, credentials)
		if err == nil || !strings.Contains(err.Error(), ds.Name) {
			t.Fatalf("datasource %s should be rejected", ds.Name)
		}
		if strings.Contains(err.Error(), "report-user") || strings.Contains(err.Error(), "stats-pass") {
			t.Fatal("error leaked credentials")
		}
	}
}
