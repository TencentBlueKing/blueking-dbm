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

// ProbeMetadataItem is a single instance metadata entry for probe config generation (ip, port, cluster type, etc.).
type ProbeMetadataItem struct {
	IP           string `json:"ip"`
	Port         int    `json:"port"`
	AdminPort    int    `json:"admin_port"`
	ClusterType  string `json:"cluster_type"`
	MachineType  string `json:"machine_type"`
	InstanceRole string `json:"instance_role"`
	AccessLayer  string `json:"access_layer"`
}

// GseConfig carries GSE reporter defaults from admin to probe (loaded from admin YAML).
type GseConfig struct {
	Endpoint    string `json:"endpoint"`
	DataID      uint64 `json:"data_id"`
	ConnTimeout string `json:"conn_timeout"`
	// LocalSocketPort is the local TCP port the GSE agent-report SDK uses on
	// Windows. Optional and omitempty: a zero value / missing field means "unset",
	// so older admin builds that never send it, and Linux probes that never need
	// it, stay fully backward compatible (probe falls back to the domain socket).
	LocalSocketPort uint `json:"local_socket_port,omitempty"`
}

// ProbeMySQLConfig carries MySQL harvester credentials/timing from admin to probe.
// Interval / Timeout are YAML duration strings (e.g. "20s") emitted verbatim into probe.yaml.
// Timeout bounds DSN dial timeout and per-query context timeout in the mysql harvester.
// Admin clamps Timeout at minProbeHarvesterTimeout before sending.
type ProbeMySQLConfig struct {
	User              string `json:"user"`
	Password          string `json:"password"`
	Interval          string `json:"interval"`
	HeartbeatInterval string `json:"heartbeat_interval"`
	ReplDelayInterval string `json:"repl_delay_interval"`
	Timeout           string `json:"timeout"`
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
	User              string `json:"user"`
	Password          string `json:"password"`
	Interval          string `json:"interval"`
	HeartbeatInterval string `json:"heartbeat_interval"`
	ReplDelayInterval string `json:"repl_delay_interval"`
	Timeout           string `json:"timeout"`
}

// ProbeHarvesterConfig carries credentials/timing for a generic (non-named) harvester block.
// Used by ProbeConfigPayload.Harvesters for newly added DB types.
type ProbeHarvesterConfig struct {
	User     string `json:"user"`
	Password string `json:"password"`
	Interval string `json:"interval"`
	Timeout  string `json:"timeout"`
}

// ProbeConfigPayload is the JSON payload returned by admin GetProbeConfig.
// Probe parses it to render the final probe YAML (gse reporter + harvester credentials + db endpoints).
// Admin always populates MySQL / Redis / ProxyAdmin defaults; probe routes per endpoint based on
// (access_layer, machine_type) when generating the final YAML, and merges ports by endpoint key
// (ip, cluster_type, machine_type, instance_role, access_layer). The credential blocks remain pointers
// so older admin builds that omit a block still degrade gracefully on newer probes.
// Harvesters carries credentials for newly added DB types (pass-through from admin probeHarvesters).
type ProbeConfigPayload struct {
	Gse        GseConfig                       `json:"gse"`
	MySQL      *ProbeMySQLConfig               `json:"mysql,omitempty"`
	Redis      *ProbeRedisConfig               `json:"redis,omitempty"`
	ProxyAdmin *ProbeProxyAdminConfig          `json:"proxy_admin,omitempty"`
	Harvesters map[string]ProbeHarvesterConfig `json:"harvesters,omitempty"`
	Metadata   []ProbeMetadataItem             `json:"metadata"`
}
