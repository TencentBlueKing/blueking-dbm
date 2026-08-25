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

package main

import (
	"encoding/json"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	mockListenIP       = "127.0.0.1"
	mockMySQLPort      = 13306
	mockProxyDataPort  = 10000
	mockProxyAdminPort = 15306
	mockRedisPort      = 16379
	mockCredUser       = "sandbox"
	mockCredPassword   = "sandbox-secret"
)

func defaultPayload() probeconfig.ProbeConfigPayload {
	return probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{
			Endpoint:    "127.0.0.1:1",
			DataID:      1,
			ConnTimeout: "2s",
		},
		MySQL: &probeconfig.ProbeMySQLConfig{
			User:              mockCredUser,
			Password:          mockCredPassword,
			Interval:          "3s",
			HeartbeatInterval: "3s",
			ReplDelayInterval: "5s",
			Timeout:           "2s",
		},
		Redis: &probeconfig.ProbeRedisConfig{
			User:     mockCredUser,
			Password: mockCredPassword,
			Interval: "3s",
			Timeout:  "2s",
		},
		ProxyAdmin: &probeconfig.ProbeProxyAdminConfig{
			User:              mockCredUser,
			Password:          mockCredPassword,
			Interval:          "3s",
			HeartbeatInterval: "3s",
			ReplDelayInterval: "5s",
			Timeout:           "2s",
		},
		Metadata: []probeconfig.ProbeMetadataItem{
			{
				IP:           mockListenIP,
				Port:         mockMySQLPort,
				ClusterType:  string(haprobe.DbmMetadataClusterTypeTendbha),
				MachineType:  string(haprobe.DbmMetadataMachineTypeBackend),
				InstanceRole: string(haprobe.MySQLStorageMaster),
				AccessLayer:  string(haprobe.DbmMetadataAccessLayerTypeStorage),
			},
			{
				IP:          mockListenIP,
				Port:        mockProxyDataPort,
				AdminPort:   mockProxyAdminPort,
				ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
				MachineType: string(haprobe.DbmMetadataMachineTypeProxy),
				AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeProxy),
			},
			{
				IP:           mockListenIP,
				Port:         mockRedisPort,
				ClusterType:  string(haprobe.DbmMetadataClusterTypeTwemproxyRedis),
				MachineType:  string(haprobe.DbmMetadataMachineTypeTendisCache),
				InstanceRole: "redis_master",
				AccessLayer:  string(haprobe.DbmMetadataAccessLayerTypeStorage),
			},
		},
	}
}

func defaultPayloadJSON() ([]byte, error) {
	return json.Marshal(defaultPayload())
}
