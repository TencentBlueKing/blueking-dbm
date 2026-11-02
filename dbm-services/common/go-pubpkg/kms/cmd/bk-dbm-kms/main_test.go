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

package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/kms"
	"dbm-services/common/go-pubpkg/kms/testhelper"
)

const secret = " $keep:spaces@/中文\" "

func setup(t *testing.T, plaintext string) {
	t.Helper()
	envelope, key := testhelper.Envelope(t, plaintext)
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "envelope"), []byte(envelope+"\n"), 0400); err != nil {
		t.Fatal(err)
	}
	t.Setenv(kms.EnabledEnv, "true")
	t.Setenv(kms.PrivateKeyEnv, key)
	t.Setenv(CredentialDirEnv, dir)
}

func TestGet(t *testing.T) {
	setup(t, `{"bkapp_id_secret":{"default":{"app_code":"bk_dbm","app_secret":"`+
		strings.ReplaceAll(secret, `"`, `\"`)+`"}}}`)
	var stdout, stderr bytes.Buffer
	if code := run([]string{"get", "bkapp_id_secret.default.app_secret"}, &stdout, &stderr); code != 0 {
		t.Fatalf("exit %d: %s", code, stderr.String())
	}
	if stdout.String() != secret {
		t.Fatal("credential was not printed verbatim")
	}
}

func TestGetErrorsDoNotLeak(t *testing.T) {
	setup(t, `{"bkapp_id_secret":{"default":{"app_code":"`+secret+`","blank":" ","number":1}}}`)
	for _, path := range []string{
		"bkapp_id_secret.default.missing",
		"bkapp_id_secret.default.blank",
		"bkapp_id_secret.default.number",
		"bkapp_id_secret.default.app_code.deeper",
		"bkapp_id_secret..app_code",
		"bkapp_id_secret.default",
	} {
		t.Run(path, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			if code := run([]string{"get", path}, &stdout, &stderr); code != 1 {
				t.Fatalf("exit %d, want 1", code)
			}
			if stdout.Len() != 0 || strings.Contains(stderr.String(), "keep:spaces") {
				t.Fatal("error output leaked credential contents")
			}
		})
	}
}

func TestDisabledOrMisconfigured(t *testing.T) {
	var stdout, stderr bytes.Buffer
	t.Setenv(kms.EnabledEnv, "false")
	if code := run([]string{"get", "a.b"}, &stdout, &stderr); code != 1 {
		t.Fatalf("disabled KMS: exit %d, want 1", code)
	}
	t.Setenv(kms.EnabledEnv, "true")
	t.Setenv(kms.PrivateKeyEnv, "")
	if code := run([]string{"get", "a.b"}, &stdout, &stderr); code != 1 {
		t.Fatalf("missing private key: exit %d, want 1", code)
	}
	for _, args := range [][]string{nil, {"get"}, {"get", ""}, {"put", "a.b"}, {"get", "a", "b"}} {
		if code := run(args, &stdout, &stderr); code != 2 {
			t.Fatalf("args %q: exit %d, want 2", args, code)
		}
	}
}
