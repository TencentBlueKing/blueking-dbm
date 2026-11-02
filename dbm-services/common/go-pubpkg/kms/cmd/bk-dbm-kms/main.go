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

// bk-dbm-kms decrypts the mounted KMS envelope and prints one credential field,
// for shell entrypoints that cannot call the SDK directly.
//
// Usage: bk-dbm-kms get <json.path>, e.g. bk-dbm-kms get bkapp_id_secret.default.app_secret
package main

import (
	"errors"
	"fmt"
	"io"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/kms"
)

// CredentialDirEnv names the envelope mount directory; it shares the tool's prefix with kms.PrivateKeyEnv.
const CredentialDirEnv = "BK_DBM_KMS_CREDENTIAL_DIR"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) != 2 || args[0] != "get" || args[1] == "" {
		fmt.Fprintln(stderr, "usage: bk-dbm-kms get <json.path>")
		return 2
	}
	value, err := get(args[1])
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	// 不带换行，便于 shell 用 $(...) 原样取值
	fmt.Fprint(stdout, value)
	return 0
}

func get(path string) (string, error) {
	plaintext, enabled, err := kms.LoadEnvelope(kms.LoadOptions{CredentialDirEnv: CredentialDirEnv})
	if err != nil {
		return "", err
	}
	if !enabled {
		return "", fmt.Errorf("%s is not true", kms.EnabledEnv)
	}
	var doc any
	if err := kms.DecodeJSON(plaintext, &doc); err != nil {
		return "", err
	}
	return lookup(doc, path)
}

// lookup walks a dot-separated path; errors carry only the path, never credential contents.
func lookup(doc any, path string) (string, error) {
	current := doc
	for _, part := range strings.Split(path, ".") {
		node, ok := current.(map[string]any)
		if !ok || part == "" {
			return "", errors.New("KMS credential field " + path + " not found")
		}
		if current, ok = node[part]; !ok {
			return "", errors.New("KMS credential field " + path + " not found")
		}
	}
	value, ok := current.(string)
	if !ok {
		return "", errors.New("KMS credential field " + path + " must be a string")
	}
	if err := kms.RequireNonEmpty(value, path); err != nil {
		return "", err
	}
	return value, nil
}
