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

package thirdapi

import (
	"dbm-services/common/go-pubpkg/kms"
	"dbm-services/common/go-pubpkg/kms/testhelper"
	"os"
	"path/filepath"
	"sync"
	"testing"
)

func TestAPIServiceKMSOverridesLegacyCredentials(t *testing.T) {
	// Keep the API singleton local to this test.
	savedInstance, savedErr := instance, dbmAPIInitErr
	once = sync.Once{}
	t.Cleanup(func() { instance = savedInstance; dbmAPIInitErr = savedErr; once = sync.Once{} })
	envelope, key := testhelper.Envelope(t, `{"mysql":{"k8sDbs":{"username":"kms-user","password":"kms-password"}},"bkapp_id_secret":{"default":{"app_code":"kms-code","app_secret":"kms-secret"}}}`)
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(envelope), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv(kms.EnabledEnv, "true")
	t.Setenv(kms.PrivateKeyEnv, key)
	t.Setenv("K8S_DBS_KMS_CREDENTIAL_DIR", dir)
	t.Setenv("INNER_BK_APP_CODE", "legacy-code")
	t.Setenv("INNER_BK_APP_SECRET", "legacy-secret")
	if err := InitDbmAPIService(); err != nil {
		t.Fatal(err)
	}
	got := GetDbmAPIService()
	if got.innerBkAppCode != "kms-code" || got.innerBkAppSecret != "kms-secret" {
		t.Fatal("API client did not use KMS credentials")
	}
}
