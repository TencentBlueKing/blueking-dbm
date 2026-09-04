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
	"flag"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	_ "dbm-services/common/dbha-v2/internal/provider/mysql/harvest"
	_ "dbm-services/common/dbha-v2/internal/provider/redis/harvest"
)

var updateGolden = flag.Bool("update", false, "update GenProbeYAML golden files")

func goldenPayloadProxyDualProduce() probeconfig.ProbeConfigPayload {
	return newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.2",
			Port:        10000,
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})
}

func goldenPayloadProxyAdminFallback() probeconfig.ProbeConfigPayload {
	payload := newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.22",
			Port:        10000,
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
	})
	payload.ProxyAdmin = nil
	return payload
}

func goldenPayloadMultiFamily() probeconfig.ProbeConfigPayload {
	return newPayload([]probeconfig.ProbeMetadataItem{
		{
			IP:          "127.0.0.4",
			Port:        3306,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
		{
			IP:          "127.0.0.5",
			AdminPort:   4001,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
		},
		{
			IP:          "127.0.0.6",
			Port:        6379,
			ClusterType: string(haprobe.DbmMetadataClusterTypeRedis),
			MachineType: string(haprobe.DbmMetadataMachineTypeTendisCache),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		},
	})
}

func TestGenProbeYAML_GoldenFiles(t *testing.T) {
	cases := []struct {
		name    string
		file    string
		payload probeconfig.ProbeConfigPayload
	}{
		{
			name:    "proxy_dual_produce",
			file:    "proxy_dual_produce.yaml",
			payload: goldenPayloadProxyDualProduce(),
		},
		{
			name:    "proxy_admin_fallback",
			file:    "proxy_admin_fallback.yaml",
			payload: goldenPayloadProxyAdminFallback(),
		},
		{
			name:    "multi_family",
			file:    "multi_family.yaml",
			payload: goldenPayloadMultiFamily(),
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := config.GenProbeYAML(tc.payload)
			if err != nil {
				t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
			}

			path := filepath.Join("testdata", tc.file)
			if *updateGolden {
				if err := os.WriteFile(path, []byte(got), 0o644); err != nil {
					t.Fatalf("write golden failed, path: %s, errmsg: %s", path, err)
				}
				t.Logf("updated golden, path: %s", path)
				return
			}

			wantBytes, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("read golden failed, path: %s, errmsg: %s", path, err)
			}
			want := string(wantBytes)
			if got != want {
				t.Fatalf(
					"GenProbeYAML golden mismatch, file: %s\n--- got ---\n%s\n--- want ---\n%s",
					tc.file, got, want,
				)
			}

			// Lock the original camelCase block key for mysqlProxyAdmin when present.
			if strings.Contains(want, "mysqlProxyAdmin:") && !strings.Contains(got, "mysqlProxyAdmin:") {
				t.Fatal("expected mysqlProxyAdmin key with original casing")
			}
			if strings.Contains(got, "mysqlproxyadmin:") {
				t.Fatal("unexpected lowercased mysqlproxyadmin key")
			}
		})
	}
}
