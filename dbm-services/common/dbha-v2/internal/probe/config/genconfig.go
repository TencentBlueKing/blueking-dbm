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
	"sort"
	"strconv"
	"strings"

	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gopkg.in/yaml.v3"
)

// defaultProbeConfigVersion is the version string written into generated probe YAML
// when the payload does not carry a specific version.
const defaultProbeConfigVersion = "v2.0.0"

// GenProbeYAML builds the full probe config YAML from the payload returned by admin
// (gse reporter defaults, harvester credentials/timing, and per-cluster metadata).
//
// Probe routes harvester usage per endpoint based on (access_layer, machine_type):
//   - access_layer=proxy AND machine_type=proxy (TendbHA mysql-proxy): admin ports use
//     payload.ProxyAdmin credentials under harvester.mysqlProxyAdmin; data ports are additionally
//     routed under harvester.mysql with payload.MySQL credentials for a lightweight reachability
//     probe (see buildEndpointsFromMetadata).
//   - other mysql-family endpoints (incl. spider admin/ctl): use payload.MySQL credentials
//     under harvester.mysql.
//   - redis-family endpoints (incl. twemproxy/predixy admin ports): use payload.Redis
//     credentials under harvester.redis.
//
// When admin omits payload.ProxyAdmin (e.g. older admin), mysql-proxy admin-port endpoints fall
// back to harvester.mysql with payload.MySQL credentials so the probe degrades to legacy behavior.
func GenProbeYAML(payload probeconfig.ProbeConfigPayload) (string, error) {
	mysqlEndpoints, mysqlProxyAdminEndpoints, redisEndpoints, extraEndpoints :=
		buildEndpointsFromMetadata(payload.Metadata)

	if payload.ProxyAdmin == nil && len(mysqlProxyAdminEndpoints) > 0 {
		logger.Info(
			"payload missing proxy-admin creds, falling back to probeMysql for mysql-proxy admin ports, count: %d, hint: upgrade admin to enable proxy-admin block",
			len(mysqlProxyAdminEndpoints),
		)
		mysqlEndpoints = append(mysqlEndpoints, mysqlProxyAdminEndpoints...)
		mysqlProxyAdminEndpoints = nil
		sortEndpoints(mysqlEndpoints)
	}

	cfg := probeYAML{
		Name:    "probe",
		Version: defaultProbeConfigVersion,
		PidFile: "./pids/probe.pid",
		Reporter: probeReporterYAML{
			Name:            "gse",
			Endpoint:        payload.Gse.Endpoint,
			DataID:          payload.Gse.DataID,
			ConnTimeout:     payload.Gse.ConnTimeout,
			LocalSocketPort: payload.Gse.LocalSocketPort,
		},

		Harvester: probeHarvesterYAML{},

		Log: LogConfig{
			Path:      "./logs/probe.log",
			Level:     "info",
			FileCount: 10,
			FileSize:  500,
		},
	}

	if payload.MySQL != nil && len(mysqlEndpoints) > 0 {
		cfg.Harvester.MySQL = buildMySQLHarvester(
			payload.MySQL.User,
			payload.MySQL.Password,
			payload.MySQL.Interval,
			payload.MySQL.Timeout,
			mysqlEndpoints,
		)
	}

	if payload.ProxyAdmin != nil && len(mysqlProxyAdminEndpoints) > 0 {
		cfg.Harvester.MySQLProxyAdmin = buildMySQLHarvester(
			payload.ProxyAdmin.User,
			payload.ProxyAdmin.Password,
			payload.ProxyAdmin.Interval,
			payload.ProxyAdmin.Timeout,
			mysqlProxyAdminEndpoints,
		)
	}
	if payload.Redis != nil && len(redisEndpoints) > 0 {
		cfg.Harvester.Redis = buildRedisHarvester(
			payload.Redis.User,
			payload.Redis.Password,
			payload.Redis.Interval,
			payload.Redis.Timeout,
			redisEndpoints,
		)
	}

	if len(extraEndpoints) > 0 {
		cfg.Harvester.Extra = make(map[string]*probeGenericHarvesterYAML, len(extraEndpoints))
		for _, blockName := range sortedExtraBlockNames(extraEndpoints) {
			eps := extraEndpoints[blockName]
			if len(eps) == 0 {
				continue
			}
			cred, ok := lookupExtraHarvesterCred(payload, blockName)
			if !ok {
				logger.Info(
					"skip extra harvester block without payload credentials, block: %s, endpoints: %d",
					blockName, len(eps),
				)
				continue
			}
			cfg.Harvester.Extra[blockName] = &probeGenericHarvesterYAML{
				User:      cred.User,
				Password:  cred.Password,
				Interval:  cred.Interval,
				Timeout:   cred.Timeout,
				Endpoints: eps,
			}
		}
	}

	return marshalProbeYAML(cfg)
}

// lookupExtraHarvesterCred finds credentials for an extra block.
// Prefer PayloadKey from HarvestBlock; fall back to BlockName as the map key.
// Both keys are normalized: admin viper lowercases probeHarvesters map keys, while
// provider PayloadKey / BlockName may keep camelCase in source.
func lookupExtraHarvesterCred(
	payload probeconfig.ProbeConfigPayload, blockName string,
) (probeconfig.ProbeHarvesterConfig, bool) {
	if len(payload.Harvesters) == 0 {
		return probeconfig.ProbeHarvesterConfig{}, false
	}
	if b, ok := dbtype.HarvestBlockByName(blockName); ok && b.PayloadKey != "" {
		if cred, ok := payload.Harvesters[dbtype.NormalizeBlockName(b.PayloadKey)]; ok {
			return cred, true
		}
	}
	cred, ok := payload.Harvesters[dbtype.NormalizeBlockName(blockName)]
	return cred, ok
}

// isMysqlProxyEndpoint reports whether a metadata entry is a TendbHA mysql-proxy node
// (the only role that requires distinct proxy-admin credentials in this design):
// mysql-family clusterType AND access_layer=proxy AND machine_type=proxy.
// Spider / Twemproxy / Predixy proxies are intentionally excluded; they are probed with
// regular probeMysql / probeRedis credentials via their AdminPorts. Non-mysql clusterType
// with (proxy, proxy) is treated as malformed metadata and skipped from the proxy-admin route.
func isMysqlProxyEndpoint(clusterType, machineType, accessLayer string) bool {
	return probeconfig.IsMySQLClusterType(clusterType) &&
		accessLayer == string(haprobe.DbmMetadataAccessLayerTypeProxy) &&
		machineType == string(haprobe.DbmMetadataMachineTypeProxy)
}

func buildMySQLHarvester(
	user string,
	password string,
	interval string,
	timeout string,
	endpoints []DbEndpointConfig,
) *probeMySQLHarvesterYAML {
	return &probeMySQLHarvesterYAML{
		User:      user,
		Password:  password,
		Interval:  interval,
		Timeout:   timeout,
		Endpoints: endpoints,
	}
}

func buildRedisHarvester(
	user string,
	password string,
	interval string,
	timeout string,
	endpoints []DbEndpointConfig,
) *probeRedisHarvesterYAML {
	return &probeRedisHarvesterYAML{
		User:      user,
		Password:  password,
		Interval:  interval,
		Timeout:   timeout,
		Endpoints: endpoints,
	}
}

func marshalProbeYAML(cfg probeYAML) (string, error) {
	out, err := yaml.Marshal(&cfg)
	if err != nil {
		return "", err
	}
	return string(out), nil
}

// endpointKey is the dedup / grouping key used by buildEndpointsFromMetadata to
// fold metadata items sharing the same (ip, cluster_type, machine_type, instance_role, access_layer)
// tuple into one DbEndpointConfig with merged Ports / AdminPorts.
type endpointKey struct {
	ip           string
	clusterType  string
	machineType  string
	instanceRole string
	accessLayer  string
}

// newEndpointKey extracts the grouping key from a metadata item.
func newEndpointKey(m probeconfig.ProbeMetadataItem) endpointKey {
	return endpointKey{
		ip:           m.IP,
		clusterType:  m.ClusterType,
		machineType:  m.MachineType,
		instanceRole: m.InstanceRole,
		accessLayer:  m.AccessLayer,
	}
}

// sortEndpointKeys sorts the keys in place by (ip, cluster_type, machine_type, instance_role, access_layer)
// so the rendered yaml is deterministic across runs.
func sortEndpointKeys(keys []endpointKey) {
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].ip != keys[j].ip {
			return keys[i].ip < keys[j].ip
		}
		if keys[i].clusterType != keys[j].clusterType {
			return keys[i].clusterType < keys[j].clusterType
		}
		if keys[i].machineType != keys[j].machineType {
			return keys[i].machineType < keys[j].machineType
		}
		if keys[i].instanceRole != keys[j].instanceRole {
			return keys[i].instanceRole < keys[j].instanceRole
		}
		return keys[i].accessLayer < keys[j].accessLayer
	})
}

// groupMetadataByEndpointKey folds raw metadata items into ports / adminPorts grouped by
// endpointKey and returns the keys sorted for deterministic yaml output. Port 0 / AdminPort 0
// entries are dropped here so callers don't have to special-case them again.
func groupMetadataByEndpointKey(
	list []probeconfig.ProbeMetadataItem,
) ([]endpointKey, map[endpointKey][]string, map[endpointKey][]string) {
	keys := make(map[endpointKey]struct{})
	portsByKey := make(map[endpointKey][]string)
	adminPortsByKey := make(map[endpointKey][]string)

	for _, m := range list {
		k := newEndpointKey(m)
		keys[k] = struct{}{}
		if m.Port > 0 {
			portsByKey[k] = append(portsByKey[k], strconv.Itoa(m.Port))
		}
		if m.AdminPort > 0 {
			adminPortsByKey[k] = append(adminPortsByKey[k], strconv.Itoa(m.AdminPort))
		}
	}

	ordered := make([]endpointKey, 0, len(keys))
	for k := range keys {
		ordered = append(ordered, k)
	}
	sortEndpointKeys(ordered)
	return ordered, portsByKey, adminPortsByKey
}

// buildEndpointsFromMetadata groups metadata into named mysql/mysqlProxyAdmin/redis slices
// (zero-regression path) plus an extra map keyed by HarvestBlock.BlockName for new DB types.
//
// Routing rules:
//   - port 0 entries are dropped silently (no "0" noise in yaml output)
//   - mysql-proxy endpoints (access_layer=proxy AND machine_type=proxy) dual-produce: the admin
//     port goes to mysqlProxyAdmin (AdminPorts only), and when a data port exists it additionally
//     goes to mysql (Ports only) for the lightweight data-port probe; endpoints without AdminPorts
//     are skipped. Note: the mysql plugin treats any AdminPorts as an admin collector, so
//     mysql-proxy data-port endpoints must not carry AdminPorts when dual-produced into mysql.
//   - other mysql-family endpoints go to mysql with both Ports and AdminPorts
//   - redis-family endpoints go to redis with both Ports and AdminPorts
//   - other registered DbTypes with HarvestBlock descriptors go to extra[BlockName]
//   - unknown cluster types are skipped
//
// Output slices are sorted by (ip, cluster_type, machine_type, instance_role, access_layer) for deterministic yaml.
func buildEndpointsFromMetadata(
	list []probeconfig.ProbeMetadataItem,
) (mysql, mysqlProxyAdmin, redis []DbEndpointConfig, extra map[string][]DbEndpointConfig) {
	extra = map[string][]DbEndpointConfig{}
	ordered, portsByKey, adminPortsByKey := groupMetadataByEndpointKey(list)

	for _, k := range ordered {
		ports := portsByKey[k]
		adminPorts := adminPortsByKey[k]
		if len(ports) == 0 && len(adminPorts) == 0 {
			continue
		}

		ep := DbEndpointConfig{
			Proto:        "tcp",
			ClusterType:  haprobe.DbmMetadataClusterType(k.clusterType),
			MachineType:  haprobe.DbmMetadataMachineType(k.machineType),
			InstanceRole: haprobe.DbmMetadataInstanceRole(k.instanceRole),
			AccessLayer:  haprobe.DbmMetadataAccessLayerType(k.accessLayer),
			Ip:           k.ip,
		}

		if isMysqlProxyEndpoint(k.clusterType, k.machineType, k.accessLayer) {
			if len(adminPorts) == 0 {
				logger.Info(
					"skip mysql-proxy endpoint without admin ports, ip: %s, data_ports: %v",
					k.ip, ports,
				)
				continue
			}

			adminEp := ep
			adminEp.AdminPorts = adminPorts
			mysqlProxyAdmin = append(mysqlProxyAdmin, adminEp)

			if len(ports) > 0 {
				dataEp := ep
				dataEp.Ports = ports
				mysql = append(mysql, dataEp)
			}
			continue
		}

		ep.Ports = ports
		ep.AdminPorts = adminPorts

		switch {
		case probeconfig.IsMySQLClusterType(k.clusterType):
			mysql = append(mysql, ep)
		case probeconfig.IsRedisClusterType(k.clusterType):
			redis = append(redis, ep)
		default:
			routeExtraEndpoint(k.clusterType, ep, extra)
		}
	}

	for _, name := range sortedExtraBlockNames(extra) {
		sortEndpoints(extra[name])
	}

	return mysql, mysqlProxyAdmin, redis, extra
}

// routeExtraEndpoint appends ep to extra[BlockName] when the cluster type maps to a
// DbType that registered HarvestBlock descriptors. Prefers a Match hit; falls back
// to the nil-Match block; skips with a log when nothing matches.
func routeExtraEndpoint(
	clusterType string, ep DbEndpointConfig, extra map[string][]DbEndpointConfig,
) {
	dt := dbtype.DbTypeOf(haprobe.DbmMetadataClusterType(clusterType))
	if dt == haprobe.DbTypeNone {
		return
	}
	blocks := dbtype.HarvestBlocksOf(dt)
	if len(blocks) == 0 {
		return
	}

	attrs := dbtype.EndpointAttrs{
		ClusterType:  ep.ClusterType,
		MachineType:  ep.MachineType,
		InstanceRole: ep.InstanceRole,
		AccessLayer:  ep.AccessLayer,
	}

	var fallback *dbtype.HarvestBlock
	for i := range blocks {
		b := &blocks[i]
		if b.Match == nil {
			fallback = b
			continue
		}
		if b.Match(attrs) {
			extra[b.BlockName] = append(extra[b.BlockName], ep)
			return
		}
	}
	if fallback != nil {
		extra[fallback.BlockName] = append(extra[fallback.BlockName], ep)
		return
	}
	logger.Info(
		"skip endpoint with no matching harvest block, db_type: %s, cluster_type: %s, access_layer: %s",
		dt, clusterType, ep.AccessLayer,
	)
}

// sortEndpoints sorts in-place by (ip, cluster_type, machine_type, instance_role, access_layer) to
// keep yaml output deterministic after merges (e.g. fallback path). After the mysql-proxy
// dual-produce change, the fallback path can place two endpoints with an identical 5-tuple key
// into the mysql slice (a data-port endpoint carrying Ports and an admin-port endpoint carrying
// AdminPorts). To keep the (non-stable) sort deterministic we add Ports / AdminPorts as
// secondary tie-breakers.
func sortEndpoints(endpoints []DbEndpointConfig) {
	sort.Slice(endpoints, func(i, j int) bool {
		if endpoints[i].Ip != endpoints[j].Ip {
			return endpoints[i].Ip < endpoints[j].Ip
		}
		if endpoints[i].ClusterType != endpoints[j].ClusterType {
			return endpoints[i].ClusterType < endpoints[j].ClusterType
		}
		if endpoints[i].MachineType != endpoints[j].MachineType {
			return endpoints[i].MachineType < endpoints[j].MachineType
		}
		if endpoints[i].InstanceRole != endpoints[j].InstanceRole {
			return endpoints[i].InstanceRole < endpoints[j].InstanceRole
		}
		if endpoints[i].AccessLayer != endpoints[j].AccessLayer {
			return endpoints[i].AccessLayer < endpoints[j].AccessLayer
		}
		if pi, pj := strings.Join(endpoints[i].Ports, ","), strings.Join(endpoints[j].Ports, ","); pi != pj {
			return pi < pj
		}
		return strings.Join(endpoints[i].AdminPorts, ",") < strings.Join(endpoints[j].AdminPorts, ",")
	})
}
