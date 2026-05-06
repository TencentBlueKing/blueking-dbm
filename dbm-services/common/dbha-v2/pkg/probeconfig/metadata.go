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

// Package probeconfig defines shared types for probe config generation (e.g. metadata from admin to probe).
package probeconfig

import "dbm-services/common/dbha-v2/pkg/storage/haprobe"

// ProbeMetadataItem is a single instance metadata entry for probe config generation (ip, port, cluster type, etc.).
type ProbeMetadataItem struct {
	IP          string `json:"ip"`
	Port        int    `json:"port"`
	AdminPort   int    `json:"admin_port"`
	ClusterType string `json:"cluster_type"`
	MachineType string `json:"machine_type"`
	AccessLayer string `json:"access_layer"`
}

// GseConfig carries GSE reporter defaults from admin to probe (loaded from admin YAML).
type GseConfig struct {
	Endpoint    string `json:"endpoint"`
	DataID      uint64 `json:"data_id"`
	ConnTimeout string `json:"conn_timeout"`
}

// ProbeMySQLConfig carries MySQL harvester credentials/timing from admin to probe.
// Interval is the YAML duration string (e.g. "20s") emitted verbatim into probe.yaml.
type ProbeMySQLConfig struct {
	User     string `json:"user"`
	Password string `json:"password"`
	Interval string `json:"interval"`
}

// ProbeRedisConfig carries Redis harvester credentials/timing from admin to probe.
// Interval / Timeout are YAML duration strings (e.g. "20s") emitted verbatim into probe.yaml.
type ProbeRedisConfig struct {
	User     string `json:"user"`
	Password string `json:"password"`
	Interval string `json:"interval"`
	Timeout  string `json:"timeout"`
}

// ProbeProxyAdminConfig carries proxy-admin harvester credentials/timing from admin to probe.
// Interval / Timeout are YAML duration strings (e.g. "20s") emitted verbatim into probe.yaml.
type ProbeProxyAdminConfig struct {
	User     string `json:"user"`
	Password string `json:"password"`
	Interval string `json:"interval"`
	Timeout  string `json:"timeout"`
}

// ProbeConfigPayload is the JSON payload returned by admin GetProbeConfig.
// Probe parses it to render the final probe YAML (gse reporter + harvester credentials + db endpoints).
// MySQL / Redis are pointers so admin can omit them when the requesting probe's metadata
// has no matching cluster family.
type ProbeConfigPayload struct {
	Gse        GseConfig              `json:"gse"`
	MySQL      *ProbeMySQLConfig      `json:"mysql,omitempty"`
	Redis      *ProbeRedisConfig      `json:"redis,omitempty"`
	ProxyAdmin *ProbeProxyAdminConfig `json:"proxy_admin,omitempty"`
	Metadata   []ProbeMetadataItem    `json:"metadata"`
}

// IsMySQLClusterType reports whether the cluster type belongs to the MySQL family
// (tendbha / tendbcluster).
func IsMySQLClusterType(ct string) bool {
	return ct == string(haprobe.DbmMetadataClusterTypeTendbha) ||
		ct == string(haprobe.DbmMetadataClusterTypeTendbCluster)
}

// IsRedisClusterType reports whether the cluster type belongs to the Redis family
// (redis / twemproxy / predixy variants).
func IsRedisClusterType(ct string) bool {
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

// MetadataFamilies scans the metadata items once and reports whether MySQL / Redis families
// are present, so admin can decide which credential blocks to attach to the payload.
func MetadataFamilies(items []ProbeMetadataItem) (hasMySQL, hasRedis bool) {
	for _, m := range items {
		switch {
		case IsMySQLClusterType(m.ClusterType):
			hasMySQL = true
		case IsRedisClusterType(m.ClusterType):
			hasRedis = true
		}
		if hasMySQL && hasRedis {
			return
		}
	}
	return
}
