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

package util

import (
	"dbm-services/common/go-pubpkg/kms"
	"dbm-services/common/go-pubpkg/kms/testhelper"
	"os"
	"path/filepath"
	"testing"
)

func TestDBConfigKMSOverridesLegacyCredentials(t *testing.T) {
	envelope, key := testhelper.Envelope(t, `{"mysql":{"k8sDbs":{"username":"kms-user","password":"kms-pass!@#:%/"}},"bkapp_id_secret":{"default":{"app_code":"kms-code","app_secret":"kms-secret"}}}`)
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(envelope), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(kms.PrivateKeyEnv, key)
	t.Setenv("K8S_DBS_KMS_CREDENTIAL_DIR", dir)
	t.Setenv("DBS_MYSQL_USER", "legacy-user")
	t.Setenv("DBS_MYSQL_PASSWORD", "legacy-password")
	t.Setenv("DBS_MYSQL_HOST", "db.example.com")
	t.Setenv("DBS_MYSQL_PORT", "3306")
	t.Setenv("DBS_MYSQL_DBNAME", "dbs")
	t.Setenv(kms.EnabledEnv, "false")
	legacy, err := dbConfig()
	if err != nil {
		t.Fatal(err)
	}
	if legacy.User != "legacy-user" || legacy.Password != "legacy-password" {
		t.Fatal("legacy credentials changed")
	}
	t.Setenv(kms.EnabledEnv, "true")
	got, err := dbConfig()
	if err != nil {
		t.Fatal(err)
	}
	if got.User != "kms-user" || got.Password != "kms-pass!@#:%/" {
		t.Fatal("KMS did not override credentials")
	}
	if got.Host != legacy.Host || got.Port != legacy.Port || got.DBName != legacy.DBName {
		t.Fatal("non-credential config changed")
	}
}
