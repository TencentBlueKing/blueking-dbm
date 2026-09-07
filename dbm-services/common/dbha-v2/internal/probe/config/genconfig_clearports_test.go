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

package config_test

import (
	"reflect"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	_ "dbm-services/common/dbha-v2/internal/provider/mysql/harvest"
	_ "dbm-services/common/dbha-v2/internal/provider/redis/harvest"
)

// zeroMetadataPorts is the former gen-config filtering step: matching Port / AdminPort values
// are set to 0 so grouping skips them. Kept only to prove the post-render cut is equivalent.
func zeroMetadataPorts(metadata []probeconfig.ProbeMetadataItem, ports []int) {
	cleared := make(map[int]struct{}, len(ports))
	for _, port := range ports {
		cleared[port] = struct{}{}
	}
	for i := range metadata {
		if _, ok := cleared[metadata[i].Port]; ok {
			metadata[i].Port = 0
		}
		if _, ok := cleared[metadata[i].AdminPort]; ok {
			metadata[i].AdminPort = 0
		}
	}
}

func TestWithClearPorts_MatchesLegacyZeroing(t *testing.T) {
	cases := []struct {
		name     string
		ports    []int
		metadata []probeconfig.ProbeMetadataItem
		// noProxyAdmin drops the proxy-admin credentials from the payload, which makes
		// GenProbeYAML fall back to merging proxy admin ports into the mysql block.
		noProxyAdmin bool
	}{
		{
			name:  "clears data port keeps admin port",
			ports: []int{20000},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlItem("127.0.0.1", 20000, 4001),
			},
		},
		{
			name:  "clears admin port keeps data port",
			ports: []int{4001},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlItem("127.0.0.1", 20000, 4001),
			},
		},
		{
			name:  "clears every port of a redis block",
			ports: []int{6379},
			metadata: []probeconfig.ProbeMetadataItem{
				redisItem("127.0.0.1", 6379, 0),
			},
		},
		{
			name:  "mysql-proxy admin port drop also drops data port",
			ports: []int{10000},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlProxyItem("127.0.0.1", 3306, 10000),
			},
		},
		{
			name:  "mysql-proxy data port drop keeps admin",
			ports: []int{3306},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlProxyItem("127.0.0.1", 3306, 10000),
			},
		},
		{
			name:  "one port on both fields empties the endpoint",
			ports: []int{20000},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlItem("127.0.0.1", 20000, 20000),
			},
		},
		{
			name:  "several ports across several items",
			ports: []int{20000, 4001},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlItem("127.0.0.1", 20000, 0),
				mysqlItem("127.0.0.1", 20001, 4001),
			},
		},
		{
			name:  "port absent from the payload is a no-op",
			ports: []int{30000},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlItem("127.0.0.1", 20000, 4001),
			},
		},
		{
			name:     "empty metadata is a no-op",
			ports:    []int{20000},
			metadata: nil,
		},
		{
			name:  "proxy-admin fallback drops the data port with the admin port",
			ports: []int{10000},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlProxyItem("127.0.0.1", 3306, 10000),
			},
			noProxyAdmin: true,
		},
		{
			name:  "proxy-admin fallback keeps the admin port when the data port goes",
			ports: []int{3306},
			metadata: []probeconfig.ProbeMetadataItem{
				mysqlProxyItem("127.0.0.1", 3306, 10000),
			},
			noProxyAdmin: true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			build := func(metadata []probeconfig.ProbeMetadataItem) probeconfig.ProbeConfigPayload {
				p := newPayload(metadata)
				if tc.noProxyAdmin {
					p.ProxyAdmin = nil
				}
				return p
			}
			payload := build(append([]probeconfig.ProbeMetadataItem(nil), tc.metadata...))
			legacyMeta := append([]probeconfig.ProbeMetadataItem(nil), tc.metadata...)
			zeroMetadataPorts(legacyMeta, tc.ports)
			legacy, err := config.GenProbeYAML(build(legacyMeta))
			if err != nil {
				t.Fatalf("legacy render failed, errmsg: %s", err)
			}
			got, err := config.GenProbeYAML(payload, config.WithClearPorts(tc.ports))
			if err != nil {
				t.Fatalf("WithClearPorts render failed, errmsg: %s", err)
			}
			legacyParsed, err := config.ParseBytes([]byte(legacy))
			if err != nil {
				t.Fatalf("parse legacy failed, errmsg: %s", err)
			}
			gotParsed, err := config.ParseBytes([]byte(got))
			if err != nil {
				t.Fatalf("parse got failed, errmsg: %s", err)
			}
			gotParsed.ClearPorts = nil
			if !reflect.DeepEqual(legacyParsed.Harvester, gotParsed.Harvester) {
				t.Errorf("harvester differs, legacy: %+v, got: %+v", legacyParsed.Harvester, gotParsed.Harvester)
			}
		})
	}
}

func TestWithClearPorts_PersistsSortedUniqueList(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{mysqlItem("127.0.0.1", 3306, 0)})
	first, err := config.GenProbeYAML(payload, config.WithClearPorts([]int{13306, 10000, 13306}))
	if err != nil {
		t.Fatalf("first render failed, errmsg: %s", err)
	}
	second, err := config.GenProbeYAML(payload, config.WithClearPorts([]int{10000, 13306}))
	if err != nil {
		t.Fatalf("second render failed, errmsg: %s", err)
	}
	if first != second {
		t.Fatalf("port order must not change rendered bytes")
	}
	if !strings.Contains(first, "clearPorts:") {
		t.Fatal("expected clearPorts key in rendered yaml")
	}
	parsed, err := config.ParseBytes([]byte(first))
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(parsed.ClearPorts, []int{10000, 13306}) {
		t.Errorf("clearPorts: %v, want: [10000 13306]", parsed.ClearPorts)
	}
}

func TestWithClearPorts_EmptyOmitsKey(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{mysqlItem("127.0.0.1", 3306, 0)})
	out, err := config.GenProbeYAML(payload, config.WithClearPorts(nil), config.WithClearPorts([]int{}))
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if strings.Contains(out, "clearPorts:") {
		t.Fatal("empty clearPorts must be omitted")
	}
	parsed, err := config.ParseBytes([]byte(out))
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if parsed.ClearPorts != nil {
		t.Errorf("parsed clearPorts should be nil, got: %v", parsed.ClearPorts)
	}
}

func TestWithClearPorts_DropsEmptyHarvesterBlock(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{redisItem("127.0.0.1", 6379, 0)})
	out, err := config.GenProbeYAML(payload, config.WithClearPorts([]int{6379}))
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if strings.Contains(out, "redis:") {
		t.Fatal("expected redis harvester block to disappear")
	}
}

func mysqlItem(ip string, port, adminPort int) probeconfig.ProbeMetadataItem {
	return probeconfig.ProbeMetadataItem{
		IP:          ip,
		Port:        port,
		AdminPort:   adminPort,
		ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
		MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
		AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
	}
}

func redisItem(ip string, port, adminPort int) probeconfig.ProbeMetadataItem {
	return probeconfig.ProbeMetadataItem{
		IP:          ip,
		Port:        port,
		AdminPort:   adminPort,
		ClusterType: string(haprobe.DbmMetadataClusterTypeRedis),
		MachineType: string(haprobe.DbmMetadataMachineTypePredixy),
		AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
	}
}

func mysqlProxyItem(ip string, port, adminPort int) probeconfig.ProbeMetadataItem {
	return probeconfig.ProbeMetadataItem{
		IP:          ip,
		Port:        port,
		AdminPort:   adminPort,
		ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
		MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
		AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
	}
}
