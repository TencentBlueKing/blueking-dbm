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
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gopkg.in/yaml.v3"
)

type credentialParsedHarvester struct {
	MySQL *struct {
		Endpoints []credentialParsedEndpoint `yaml:"endpoints"`
	} `yaml:"mysql,omitempty"`
	Redis *struct {
		Endpoints []credentialParsedEndpoint `yaml:"endpoints"`
	} `yaml:"redis,omitempty"`
}

type credentialParsedYAML struct {
	Harvester credentialParsedHarvester `yaml:"harvester"`
}

type credentialParsedEndpoint struct {
	Ip         string   `yaml:"ip"`
	Ports      []string `yaml:"ports,omitempty"`
	AdminPorts []string `yaml:"adminPorts,omitempty"`
	ClusterID  int      `yaml:"clusterID,omitempty"`
	User       string   `yaml:"user,omitempty"`
	Password   string   `yaml:"password,omitempty"`
}

func renderCredential(t *testing.T, payload probeconfig.ProbeConfigPayload) credentialParsedYAML {
	t.Helper()
	out, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	var got credentialParsedYAML
	if err := yaml.Unmarshal([]byte(out), &got); err != nil {
		t.Fatalf("yaml unmarshal failed, errmsg: %s", err)
	}
	return got
}

func redisClusterItem(ip string, port int, clusterID int, password string) probeconfig.ProbeMetadataItem {
	return probeconfig.ProbeMetadataItem{
		IP:          ip,
		Port:        port,
		ClusterType: string(haprobe.DbmMetadataClusterTypeTwemproxyRedis),
		MachineType: string(haprobe.DbmMetadataMachineTypeTendisCache),
		AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		ClusterID:   clusterID,
		Password:    password,
	}
}

func TestGenProbeYAML_RedisSplitsByCluster(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		redisClusterItem("127.0.0.10", 30000, 1001, "pwd-1001"),
		redisClusterItem("127.0.0.10", 31000, 1002, "pwd-1002"),
	})

	got := renderCredential(t, payload)
	if got.Harvester.Redis == nil {
		t.Fatal("expected redis harvester")
	}
	eps := got.Harvester.Redis.Endpoints
	if len(eps) != 2 {
		t.Fatalf("expected 2 endpoints (one per cluster), got: %d", len(eps))
	}
	byCluster := map[int]credentialParsedEndpoint{}
	for _, ep := range eps {
		byCluster[ep.ClusterID] = ep
	}
	if ep, ok := byCluster[1001]; !ok || ep.Password != "pwd-1001" {
		t.Errorf("cluster 1001 credential wrong: %+v", byCluster[1001])
	}
	if ep, ok := byCluster[1002]; !ok || ep.Password != "pwd-1002" {
		t.Errorf("cluster 1002 credential wrong: %+v", byCluster[1002])
	}
}

func TestGenProbeYAML_RedisMergesSameClusterPorts(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		redisClusterItem("127.0.0.10", 30000, 1001, "pwd-1001"),
		redisClusterItem("127.0.0.10", 30001, 1001, "pwd-1001"),
	})

	got := renderCredential(t, payload)
	if got.Harvester.Redis == nil {
		t.Fatal("expected redis harvester")
	}
	eps := got.Harvester.Redis.Endpoints
	if len(eps) != 1 {
		t.Fatalf("expected 1 merged endpoint, got: %d", len(eps))
	}
	ep := eps[0]
	if ep.ClusterID != 1001 {
		t.Errorf("expected clusterID 1001, got: %d", ep.ClusterID)
	}
	if ep.Password != "pwd-1001" {
		t.Errorf("expected password pwd-1001, got: %s", ep.Password)
	}
	if len(ep.Ports) != 2 {
		t.Errorf("expected 2 merged ports, got: %v", ep.Ports)
	}
}

func TestGenProbeYAML_MysqlNotSplitByCluster(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.1",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
			ClusterID:   5001,
		},
	})

	got := renderCredential(t, payload)
	if got.Harvester.MySQL == nil || len(got.Harvester.MySQL.Endpoints) != 1 {
		t.Fatalf("expected 1 mysql endpoint")
	}
	ep := got.Harvester.MySQL.Endpoints[0]
	if ep.ClusterID != 0 {
		t.Errorf("mysql endpoint must not carry clusterID, got: %d", ep.ClusterID)
	}
}

func TestGenProbeYAML_RedisDeterministicAcrossClusters(t *testing.T) {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		redisClusterItem("127.0.0.10", 30000, 1002, "pwd-1002"),
		redisClusterItem("127.0.0.10", 31000, 1001, "pwd-1001"),
		redisClusterItem("127.0.0.11", 30000, 1003, "pwd-1003"),
	})

	first, err := config.GenProbeYAML(payload)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	for i := 0; i < 10; i++ {
		out, err := config.GenProbeYAML(payload)
		if err != nil {
			t.Fatalf("GenProbeYAML failed on iter %d, errmsg: %s", i, err)
		}
		if out != first {
			t.Fatalf("GenProbeYAML output not deterministic on iter %d", i)
		}
	}
}
