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

package hamodel

import (
	"bytes"
	"encoding/json"
	"fmt"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// TestNewDbhaDataPassthrough locks the receiver storage contract: NewDbhaData copies
// cluster_type / db_type_name / machine_type / data verbatim and never rewrites them
// based on dbtype registration (including unregistered or provider-owned types).
func TestNewDbhaDataPassthrough(t *testing.T) {
	cases := []struct {
		name        string
		clusterType string
		dbTypeName  string
		machineType string
		rawData     string
	}{
		{
			name:        "provider redis cluster type",
			clusterType: "RedisInstance",
			dbTypeName:  "redis",
			machineType: "tendiscache",
			rawData:     `{"role":"master","nested":{"k":1}}`,
		},
		{
			name:        "unregistered future cluster type",
			clusterType: "someFutureDb",
			dbTypeName:  "future",
			machineType: "future_machine",
			rawData:     `{"x":[1,2,{"y":3}]}`,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			payload := fmt.Sprintf(`{
				"cluster_type":%q,
				"db_type_name":%q,
				"machine_type":%q,
				"db_ip":"127.0.0.1",
				"db_port":6379,
				"data":%s
			}`, tc.clusterType, tc.dbTypeName, tc.machineType, tc.rawData)

			var hd haprobe.HarvestData
			if err := json.Unmarshal([]byte(payload), &hd); err != nil {
				t.Fatalf("unmarshal harvest data failed, errmsg: %s", err)
			}

			got := NewDbhaData(&hd)
			if string(got.ClusterType) != tc.clusterType {
				t.Errorf("ClusterType = %q, want %q", got.ClusterType, tc.clusterType)
			}
			if string(got.DbTypeName) != tc.dbTypeName {
				t.Errorf("DbTypeName = %q, want %q", got.DbTypeName, tc.dbTypeName)
			}
			if string(got.MachineType) != tc.machineType {
				t.Errorf("MachineType = %q, want %q", got.MachineType, tc.machineType)
			}
			if !got.Value.Valid {
				t.Fatal("Value.Valid = false, want true")
			}
			if !bytes.Equal(got.Value.Data, []byte(tc.rawData)) {
				t.Errorf("Value.Data = %s, want %s", got.Value.Data, tc.rawData)
			}
		})
	}
}
