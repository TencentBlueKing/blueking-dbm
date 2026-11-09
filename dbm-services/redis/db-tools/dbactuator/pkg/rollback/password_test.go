// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// passwordRoot points portPassword at a fresh dir of per-port config dirs.
func passwordRoot(t *testing.T) string {
	t.Helper()
	root, orig := t.TempDir(), passwordDir
	passwordDir = func(port int) string { return filepath.Join(root, fmt.Sprint(port)) }
	t.Cleanup(func() { passwordDir = orig })
	return root
}

func writeConf(t *testing.T, root string, port int, name, body string) string {
	t.Helper()
	dir := filepath.Join(root, fmt.Sprint(port))
	if err := os.MkdirAll(dir, 0755); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, []byte(body), 0644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestPortPasswordReusesUntilConfChanges(t *testing.T) {
	root := passwordRoot(t)
	conf := writeConf(t, root, 30000, "redis.conf",
		"port 30000\n# requirepass commented\nrequirepass \"p@ss\"\nrequirepass second\n")
	if got, err := portPassword(30000); err != nil || got != "p@ss" {
		t.Fatalf("got %q, %v", got, err)
	}
	if got, err := portPassword(30000); err != nil || got != "p@ss" {
		t.Fatalf("not reused: %q, %v", got, err)
	}
	if err := os.WriteFile(conf, []byte("requirepass next\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if got, err := portPassword(30000); err != nil || got != "next" {
		t.Fatalf("rewritten conf not reread: %q, %v", got, err)
	}
}

func TestPortPasswordFallsBackToInstanceConf(t *testing.T) {
	root := passwordRoot(t)
	writeConf(t, root, 30001, "redis.conf", "port 30001\n")
	writeConf(t, root, 30001, "instance.conf", "requirepass fromInstance\n")
	if got, err := portPassword(30001); err != nil || got != "fromInstance" {
		t.Fatalf("got %q, %v", got, err)
	}

	empty := writeConf(t, root, 30002, "redis.conf", "port 30002\nrequirepass\n")
	if got, err := portPassword(30002); err != nil || got != "" {
		t.Fatalf("no password: %q, %v", got, err)
	}
	if err := os.WriteFile(empty, []byte("requirepass later\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if got, err := portPassword(30002); err != nil || got != "later" {
		t.Fatalf("empty password stuck: %q, %v", got, err)
	}

	if _, err := portPassword(30003); err == nil {
		t.Fatal("want an error without any config file")
	}
	writeConf(t, root, 30003, "redis.conf", "requirepass late\n")
	if got, err := portPassword(30003); err != nil || got != "late" {
		t.Fatalf("a failed read must not be kept: %q, %v", got, err)
	}
}
