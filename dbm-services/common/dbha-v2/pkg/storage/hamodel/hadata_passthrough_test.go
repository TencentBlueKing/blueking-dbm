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

func TestNewDbhaDataProbeMapping(t *testing.T) {
	host := &haprobe.HostMetric{
		NetIPs:     []string{"127.0.0.1"},
		MemTotalMB: 1024,
		CpuLoad1:   0.5,
	}
	probe := &haprobe.ProbeMetric{
		Version:         "1.2.3",
		Pid:             99,
		CpuUsagePercent: 0,
		UptimeSeconds:   12,
	}

	withProbe := &haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			DbIp:   "127.0.0.1",
			DbPort: 3306,
			Host:   host,
			Probe:  probe,
		},
	}
	got := NewDbhaData(withProbe)
	if !got.Probe.Valid {
		t.Fatal("Probe.Valid = false, want true")
	}
	if got.Probe.Data == nil || got.Probe.Data.Version != "1.2.3" || got.Probe.Data.Pid != 99 {
		t.Errorf("unexpected probe mapping: %#v", got.Probe.Data)
	}
	if !got.Host.Valid || got.Host.Data == nil || got.Host.Data.MemTotalMB != 1024 {
		t.Errorf("Host mapping regresssed: %#v", got.Host)
	}
	if !got.IPs.Valid || len(got.IPs.Data) != 1 || got.IPs.Data[0] != "127.0.0.1" {
		t.Errorf("IPs mapping regresssed: %#v", got.IPs)
	}

	withoutProbe := &haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			DbIp:   "127.0.0.1",
			DbPort: 3306,
			Host:   host,
		},
	}
	gotNil := NewDbhaData(withoutProbe)
	if gotNil.Probe.Valid {
		t.Fatal("Probe.Valid = true when probe is nil, want false")
	}
	if !gotNil.Host.Valid {
		t.Fatal("Host.Valid = false, want true")
	}
}

func TestNewDbhaDataHarvestTypeFallback(t *testing.T) {
	got := NewDbhaData(&haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{DbIp: "127.0.0.1", DbPort: 3306},
	})
	if got.HarvestType != haprobe.HarvestTypeDefault {
		t.Errorf("empty harvest_type not filled, got: %s, want: %s", got.HarvestType, haprobe.HarvestTypeDefault)
	}

	got = NewDbhaData(&haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			DbIp:        "127.0.0.1",
			DbPort:      3306,
			HarvestType: haprobe.HarvestTypeHeartbeat,
		},
	})
	if got.HarvestType != haprobe.HarvestTypeHeartbeat {
		t.Errorf("harvest_type altered, got: %s, want: %s", got.HarvestType, haprobe.HarvestTypeHeartbeat)
	}
}
