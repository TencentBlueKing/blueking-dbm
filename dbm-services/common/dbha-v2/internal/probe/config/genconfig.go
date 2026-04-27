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

// GenProbeYAML builds the full probe config YAML from the payload returned by admin
// (gse reporter defaults, harvester credentials/timing, and per-cluster metadata).
//
// Harvester sections are emitted only when admin attached the matching credentials block
// (payload.MySQL / payload.Redis) AND the metadata yields at least one matching endpoint.
// MySQL / Redis credentials default to zero values; admin owns the source of truth.
func GenProbeYAML(payload probeconfig.ProbeConfigPayload) (string, error) {
	mysqlEndpoints, redisEndpoints := buildEndpointsFromMetadata(payload.Metadata)

	cfg := probeYAML{
		Name:    "probe",
		Version: "v2.0.0",
		PidFile: "./pids/probe.pid",
		Reporter: probeReporterYAML{
			Name:        "gse",
			Endpoint:    payload.Gse.Endpoint,
			DataID:      payload.Gse.DataID,
			ConnTimeout: payload.Gse.ConnTimeout,
		},

		Harvester: probeHarvesterYAML{},

		Log: LogConfig{
			Path:      "./logs/probe.log",
			Level:     "debug",
			FileCount: 10,
			FileSize:  100,
		},
	}

	if payload.MySQL != nil && len(mysqlEndpoints) > 0 {
		cfg.Harvester.MySQL = &struct {
			User      string             `yaml:"user"`
			Password  string             `yaml:"password"`
			Interval  string             `yaml:"interval"`
			Endpoints []DbEndpointConfig `yaml:"endpoints"`
		}{
			User:      payload.MySQL.User,
			Password:  payload.MySQL.Password,
			Interval:  payload.MySQL.Interval,
			Endpoints: mysqlEndpoints,
		}
	}
	if payload.Redis != nil && len(redisEndpoints) > 0 {
		cfg.Harvester.Redis = &struct {
			User      string             `yaml:"user"`
			Password  string             `yaml:"password"`
			Interval  string             `yaml:"interval"`
			Timeout   string             `yaml:"timeout"`
			Endpoints []DbEndpointConfig `yaml:"endpoints"`
		}{
			User:      payload.Redis.User,
			Password:  payload.Redis.Password,
			Interval:  payload.Redis.Interval,
			Timeout:   payload.Redis.Timeout,
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
		switch {
		case probeconfig.IsMySQLClusterType(k.clusterType):
			mysql = append(mysql, ep)
		case probeconfig.IsRedisClusterType(k.clusterType):
			redis = append(redis, ep)
		}
	}
	return mysql, redis
}
