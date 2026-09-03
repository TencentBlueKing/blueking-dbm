/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"strings"
	"testing"
)

func TestStorageDeviceJSONPath(t *testing.T) {
	cases := []struct {
		mount  string
		fields []string
		want   string
	}{
		{"/data", nil, `$."/data"`},
		{"/data", []string{"size"}, `$."/data".size`},
		{"/data", []string{"disk_type"}, `$."/data".disk_type`},
		{"/data1", []string{"size"}, `$."/data1".size`},
	}
	for _, c := range cases {
		got := storageDeviceJSONPath(c.mount, c.fields...)
		if got != c.want {
			t.Errorf("storageDeviceJSONPath(%q, %v)=%q, want %q", c.mount, c.fields, got, c.want)
		}
	}
}

func TestNormalizeStorageDeviceJSONPath(t *testing.T) {
	cases := map[string]string{
		"/data/size":          `$."/data".size`,
		"/data/disk_type":     `$."/data".disk_type`,
		"/data":               `$."/data"`,
		"/data1/size":         `$."/data1".size`,
		"$./data.size":        `$."/data".size`,
		"$./data.disk_type":   `$."/data".disk_type`,
		"$./data":             `$."/data"`,
		`$."/data".size`:      `$."/data".size`,
		`$."/data".disk_type`: `$."/data".disk_type`,
		`$."/data"`:           `$."/data"`,
		"cpu_num":             "cpu_num",
	}
	for in, want := range cases {
		if got := normalizeStorageDeviceJSONPath(in); got != want {
			t.Errorf("normalizeStorageDeviceJSONPath(%q)=%q, want %q", in, got, want)
		}
	}
}

func TestRewriteStorageDeviceJSONExtract(t *testing.T) {
	sql := `SELECT COUNT(*) FROM tb_rp_detail WHERE JSON_EXTRACT(storage_device, '/data/size') >= 3000 AND JSON_EXTRACT(storage_device, '/data/size') <= 3800 AND JSON_UNQUOTE(JSON_EXTRACT(storage_device, '/data/disk_type')) = 'SSD'`
	got, changed := rewriteStorageDeviceJSONExtract(sql)
	if !changed {
		t.Fatal("expected path rewrite")
	}
	if !strings.Contains(got, `$."/data".size`) || !strings.Contains(got, `$."/data".disk_type`) {
		t.Errorf("rewritten SQL missing correct JSON path: %s", got)
	}
	if strings.Contains(got, `'/data/size'`) || strings.Contains(got, `'/data/disk_type'`) {
		t.Errorf("rewritten SQL still contains filesystem path: %s", got)
	}

	already := `SELECT JSON_EXTRACT(storage_device, '$."/data".size') FROM tb_rp_detail`
	got, changed = rewriteStorageDeviceJSONExtract(already)
	if changed {
		t.Errorf("correct path should stay unchanged, got %s", got)
	}

	doubleQuoted := `SELECT JSON_EXTRACT(storage_device, "/data/size") FROM tb_rp_detail`
	got, changed = rewriteStorageDeviceJSONExtract(doubleQuoted)
	if !changed {
		t.Fatal("expected double-quoted filesystem path to be rewritten")
	}
	want := `JSON_EXTRACT(storage_device, '$."/data".size')`
	if !strings.Contains(got, want) {
		t.Errorf("rewritten SQL = %s, want substring %s", got, want)
	}
	if strings.Contains(got, `"$."/data".size"`) {
		t.Errorf("rewritten SQL reused double quotes and broke the literal: %s", got)
	}
}
