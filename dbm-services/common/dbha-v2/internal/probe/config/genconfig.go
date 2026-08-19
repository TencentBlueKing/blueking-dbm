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
// Endpoint-to-block routing is provided by provider registrations:
//   - MySQL family: RegisterEndpointRouter (TendbHA mysql-proxy dual-produce, etc.)
//   - Redis family / new DB types: RegisterHarvestBlock Match / nil-Match fallback
//
// Named credentials (payload.MySQL / ProxyAdmin / Redis) and the ProxyAdmin-nil
// legacy fallback remain here because the admin wire contract is unchanged.
//
// When admin omits payload.ProxyAdmin (e.g. older admin), mysql-proxy admin-port endpoints fall
// back to harvester.mysql with payload.MySQL credentials so the probe degrades to legacy behavior.
func GenProbeYAML(payload probeconfig.ProbeConfigPayload) (string, error) {
	byBlock := buildEndpointsFromMetadata(payload.Metadata)

	mysqlEndpoints := byBlock[HarvesterBlockMySQL]
	mysqlProxyAdminEndpoints := byBlock[HarvesterBlockMySQLProxyAdmin]
	redisEndpoints := byBlock[HarvesterBlockRedis]
	delete(byBlock, HarvesterBlockMySQL)
	delete(byBlock, HarvesterBlockMySQLProxyAdmin)
	delete(byBlock, HarvesterBlockRedis)
	extraEndpoints := byBlock

	if payload.ProxyAdmin == nil && len(mysqlProxyAdminEndpoints) > 0 {
		logger.Info(
			"payload missing proxy-admin creds, falling back to probeMysql for mysql-proxy admin ports, count: %d, hint: upgrade admin to enable proxy-admin block",
			len(mysqlProxyAdminEndpoints),
		)
		mysqlEndpoints = append(mysqlEndpoints, mysqlProxyAdminEndpoints...)
		mysqlProxyAdminEndpoints = nil
		sortEndpoints(mysqlEndpoints)
	}

	cfg := newProbeYAML(payload)

	fillNamedHarvesters(&cfg, payload, mysqlEndpoints, mysqlProxyAdminEndpoints, redisEndpoints)
	fillExtraHarvesters(&cfg, payload, extraEndpoints)

	if len(payload.Metadata) > 0 &&
		cfg.Harvester.MySQL == nil &&
		cfg.Harvester.MySQLProxyAdmin == nil &&
		cfg.Harvester.Redis == nil &&
		len(cfg.Harvester.Extra) == 0 {
		logger.Warn(
			"probe yaml has metadata but no harvester blocks; check provider harvest registration",
		)
	}

	return marshalProbeYAML(cfg)
}

// newProbeYAML builds the probe config skeleton: fixed process/log defaults plus the
// gse reporter block taken from the payload. Harvester blocks are filled separately.
func newProbeYAML(payload probeconfig.ProbeConfigPayload) probeYAML {
	return probeYAML{
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
}

// fillNamedHarvesters writes the three well-known harvester blocks; a block is emitted
// only when both its credentials and its routed endpoints are present.
func fillNamedHarvesters(
	cfg *probeYAML,
	payload probeconfig.ProbeConfigPayload,
	mysqlEndpoints []DbEndpointConfig,
	mysqlProxyAdminEndpoints []DbEndpointConfig,
	redisEndpoints []DbEndpointConfig,
) {
	if payload.MySQL != nil && len(mysqlEndpoints) > 0 {
		cfg.Harvester.MySQL = buildMySQLHarvester(
			payload.MySQL.User,
			payload.MySQL.Password,
			payload.MySQL.Interval,
			payload.MySQL.Timeout,
			mysqlEndpoints,
			payload.MySQL.HeartbeatInterval,
			payload.MySQL.ReplDelayInterval,
		)
	}

	if payload.ProxyAdmin != nil && len(mysqlProxyAdminEndpoints) > 0 {
		cfg.Harvester.MySQLProxyAdmin = buildMySQLHarvester(
			payload.ProxyAdmin.User,
			payload.ProxyAdmin.Password,
			payload.ProxyAdmin.Interval,
			payload.ProxyAdmin.Timeout,
			mysqlProxyAdminEndpoints,
			payload.ProxyAdmin.HeartbeatInterval,
			payload.ProxyAdmin.ReplDelayInterval,
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
}

// fillExtraHarvesters writes the harvester blocks of newly added DB types, in sorted
// block-name order. Blocks whose credentials are absent from the payload are skipped.
func fillExtraHarvesters(
	cfg *probeYAML,
	payload probeconfig.ProbeConfigPayload,
	extraEndpoints map[string][]DbEndpointConfig,
) {
	if len(extraEndpoints) == 0 {
		return
	}

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

func buildMySQLHarvester(
	user string,
	password string,
	interval string,
	timeout string,
	endpoints []DbEndpointConfig,
	heartbeatInterval string,
	replDelayInterval string,
) *probeMySQLHarvesterYAML {
	return &probeMySQLHarvesterYAML{
		User:              user,
		Password:          password,
		Interval:          interval,
		HeartbeatInterval: heartbeatInterval,
		ReplDelayInterval: replDelayInterval,
		Timeout:           timeout,
		Endpoints:         endpoints,
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

// buildEndpointsFromMetadata groups metadata into harvester blocks via provider
// RouteEndpoint / HarvestBlock registrations. Named mysql / mysqlProxyAdmin / redis
// keys use config.HarvesterBlock* original casing so GenProbeYAML can split them
// back onto named YAML fields; other BlockNames land in Extra.
//
// PortKindData / PortKindAdmin endpoints clear the unused port side so mysql collectors
// do not dual-start from a single endpoint. Empty port sets for a given PortKind are skipped.
func buildEndpointsFromMetadata(list []probeconfig.ProbeMetadataItem) map[string][]DbEndpointConfig {
	out := map[string][]DbEndpointConfig{}
	ordered, portsByKey, adminPortsByKey := groupMetadataByEndpointKey(list)

	for _, k := range ordered {
		ports := portsByKey[k]
		adminPorts := adminPortsByKey[k]
		if len(ports) == 0 && len(adminPorts) == 0 {
			continue
		}

		dt := dbtype.DbTypeOf(haprobe.DbmMetadataClusterType(k.clusterType))
		if dt == haprobe.DbTypeNone {
			continue
		}

		attrs := dbtype.EndpointAttrs{
			ClusterType:  haprobe.DbmMetadataClusterType(k.clusterType),
			MachineType:  haprobe.DbmMetadataMachineType(k.machineType),
			InstanceRole: haprobe.DbmMetadataInstanceRole(k.instanceRole),
			AccessLayer:  haprobe.DbmMetadataAccessLayerType(k.accessLayer),
			Ip:           k.ip,
			Ports:        ports,
			AdminPorts:   adminPorts,
		}

		base := DbEndpointConfig{
			Proto:        "tcp",
			ClusterType:  attrs.ClusterType,
			MachineType:  attrs.MachineType,
			InstanceRole: attrs.InstanceRole,
			AccessLayer:  attrs.AccessLayer,
			Ip:           attrs.Ip,
		}

		for _, route := range dbtype.RouteEndpoint(dt, attrs) {
			ep, ok := endpointForPortKind(base, ports, adminPorts, route.Ports)
			if !ok {
				continue
			}
			out[route.BlockName] = append(out[route.BlockName], ep)
		}
	}

	for _, name := range sortedExtraBlockNames(out) {
		sortEndpoints(out[name])
	}
	return out
}

// endpointForPortKind builds an endpoint carrying only the ports selected by kind.
// Returns ok=false when the selected port set is empty (caller must skip).
func endpointForPortKind(
	base DbEndpointConfig,
	ports, adminPorts []string,
	kind dbtype.PortKind,
) (DbEndpointConfig, bool) {
	ep := base
	switch kind {
	case dbtype.PortKindAll:
		ep.Ports = ports
		ep.AdminPorts = adminPorts
		return ep, true
	case dbtype.PortKindData:
		if len(ports) == 0 {
			return DbEndpointConfig{}, false
		}
		ep.Ports = ports
		// AdminPorts intentionally left nil.
		return ep, true
	case dbtype.PortKindAdmin:
		if len(adminPorts) == 0 {
			return DbEndpointConfig{}, false
		}
		ep.AdminPorts = adminPorts
		// Ports intentionally left nil.
		return ep, true
	default:
		return DbEndpointConfig{}, false
	}
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
