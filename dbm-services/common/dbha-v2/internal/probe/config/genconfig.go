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

package config

import (
	"strconv"

	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gopkg.in/yaml.v3"
)

// GenProbeYAML builds full probe config YAML from metadata items (returned by admin).
func GenProbeYAML(metadata []probeconfig.ProbeMetadataItem) (string, error) {
	mysqlEndpoints, redisEndpoints := buildEndpointsFromMetadata(metadata)

	cfg := probeYAML{
		Name:    "probe",
		Version: "v2.0.0",
		PidFile: "./pids/probe.pid",
		Reporter: probeReporterYAML{
			Name:        "gse",
			Endpoint:    "/usr/local/gse2_bkte/agent/data/ipc.state.report",
			DataID:      0,
			ConnTimeout: "5s",
		},

		Harvester: probeHarvesterYAML{},

		Log: LogConfig{
			Path:      "./logs/probe.log",
			Level:     "debug",
			FileCount: 10,
			FileSize:  100,
		},
	}

	if len(mysqlEndpoints) > 0 {
		cfg.Harvester.MySQL = &struct {
			User      string             `yaml:"user"`
			Password  string             `yaml:"password"`
			Interval  string             `yaml:"interval"`
			Endpoints []DbEndpointConfig `yaml:"endpoints"`
		}{
			User:      "root",
			Password:  "root",
			Interval:  "20s",
			Endpoints: mysqlEndpoints,
		}
	}
	if len(redisEndpoints) > 0 {
		cfg.Harvester.Redis = &struct {
			Password  string             `yaml:"password"`
			Interval  string             `yaml:"interval"`
			Timeout   string             `yaml:"timeout"`
			Endpoints []DbEndpointConfig `yaml:"endpoints"`
		}{
			Password:  "",
			Interval:  "20s",
			Timeout:   "5s",
			Endpoints: redisEndpoints,
		}
	}

	out, err := yaml.Marshal(&cfg)
	if err != nil {
		return "", err
	}
	return string(out), nil
}

func buildEndpointsFromMetadata(list []probeconfig.ProbeMetadataItem) (mysql, redis []DbEndpointConfig) {
	type key struct {
		ip          string
		clusterType string
		machineType string
		accessLayer string
	}
	portsByKey := make(map[key][]string)
	adminPortsByKey := make(map[key][]string)

	for _, m := range list {
		k := key{
			ip:          m.IP,
			clusterType: m.ClusterType,
			machineType: m.MachineType,
			accessLayer: m.AccessLayer,
		}
		portsByKey[k] = append(portsByKey[k], strconv.Itoa(m.Port))
		if m.AdminPort > 0 {
			adminPortsByKey[k] = append(adminPortsByKey[k], strconv.Itoa(m.AdminPort))
		}
	}

	for k, ports := range portsByKey {
		ep := DbEndpointConfig{
			Proto:       "tcp",
			ClusterType: haprobe.DbmMetadataClusterType(k.clusterType),
			MachineType: haprobe.DbmMetadataMachineType(k.machineType),
			AccessLayer: haprobe.DbmMetadataAccessLayerType(k.accessLayer),
			Ip:          k.ip,
			Ports:       ports,
			AdminPorts:  adminPortsByKey[k],
		}
		if isMySQLClusterType(k.clusterType) {
			mysql = append(mysql, ep)
		} else if isRedisClusterType(k.clusterType) {
			redis = append(redis, ep)
		}
	}
	return mysql, redis
}

func isMySQLClusterType(ct string) bool {
	return ct == string(haprobe.DbmMetadataClusterTypeTendbha) ||
		ct == string(haprobe.DbmMetadataClusterTypeTendbCluster)
}

func isRedisClusterType(ct string) bool {
	switch haprobe.DbmMetadataClusterType(ct) {
	case haprobe.DbmMetadataClusterTypeRedis,
		haprobe.DbmMetadataClusterTypeTwemproxyRedis,
		haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD,
		haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
		haprobe.DbmMetadataClusterTypePredixyRedisCluster:
		return true
	}
	return false
}
