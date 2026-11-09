/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package serializer

import (
	"encoding/json"
	"errors"
	"reflect"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"
)

func sampleHaServerList() *discovery.HaServerList {
	start := time.Date(2026, 11, 4, 6, 0, 0, 0, time.UTC)
	return &discovery.HaServerList{
		Servers: []discovery.HaServer{{
			Role:      discovery.HaServerRoleAdmin,
			ID:        "admin-1",
			IPs:       []string{"127.0.0.1", "::1"},
			StartTime: start,
			UpdatedAt: start.Add(30 * time.Minute),
			Uptime:    "30 minutes",
		}},
		IPs: []string{"127.0.0.1", "::1"},
	}
}

func TestNewHaServerListData(t *testing.T) {
	got := NewHaServerListData(sampleHaServerList())
	want := HaServerListData{
		Servers: []HaServerOutputInfo{{
			Role:      "admin",
			ID:        "admin-1",
			IPs:       []string{"127.0.0.1", "::1"},
			StartTime: "2026-11-04T14:00:00+08:00",
			UpdatedAt: "2026-11-04T14:30:00+08:00",
			Uptime:    "30 minutes",
		}},
		IPs: []string{"127.0.0.1", "::1"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("C01 C02 data: %+v, want: %+v", got, want)
	}
}

func TestHaServerListDataJSONFields(t *testing.T) {
	encoded, err := json.Marshal(NewHaServerListData(sampleHaServerList()))
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}

	var decoded struct {
		Servers []map[string]any `json:"servers"`
	}
	if err := json.Unmarshal(encoded, &decoded); err != nil {
		t.Fatalf("unmarshal failed, errmsg: %s", err)
	}

	wantKeys := []string{"id", "ips", "role", "start_time", "updated_at", "uptime"}
	gotKeys := make([]string, 0, len(decoded.Servers[0]))
	for _, k := range wantKeys {
		if _, ok := decoded.Servers[0][k]; ok {
			gotKeys = append(gotKeys, k)
		}
	}
	if len(decoded.Servers[0]) != len(wantKeys) || !reflect.DeepEqual(gotKeys, wantKeys) {
		t.Fatalf("C03 server keys: %v, want exactly: %v", decoded.Servers[0], wantKeys)
	}
}

func TestLoadShanghaiLocationFallback(t *testing.T) {
	loc := loadShanghaiLocation(func(string) (*time.Location, error) {
		return nil, errors.New("tzdata missing")
	})

	ts := time.Date(2026, 11, 4, 6, 0, 0, 0, time.UTC)
	if got := formatHaServerTime(ts, loc); got != "2026-11-04T14:00:00+08:00" {
		t.Fatalf("C04 fallback time: %s", got)
	}

	if got := formatHaServerTime(time.Time{}, loc); got != "" {
		t.Fatalf("zero time: %s, want empty", got)
	}
}

func TestNewHaServerListDataEmpty(t *testing.T) {
	for name, list := range map[string]*discovery.HaServerList{
		"nil list":     nil,
		"empty list":   {Servers: []discovery.HaServer{}, IPs: []string{}},
		"nil children": {},
	} {
		encoded, err := json.Marshal(NewHaServerListData(list))
		if err != nil {
			t.Fatalf("%s marshal failed, errmsg: %s", name, err)
		}
		if string(encoded) != `{"servers":[],"ips":[]}` {
			t.Fatalf("C06 %s json: %s", name, encoded)
		}
	}
}
