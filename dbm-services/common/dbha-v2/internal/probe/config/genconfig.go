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
	"time"

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
func GenProbeYAML(payload probeconfig.ProbeConfigPayload, opts ...GenOption) (string, error) {
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

	for _, opt := range opts {
		if opt == nil {
			continue
		}
		opt(&cfg)
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

// sortedPortStrings sorts every port slice numerically and renders it to strings. Sorting by
// value rather than lexically keeps "80" before "3306". Duplicates are preserved: dropping them
// would change which endpoints probe collects, which is out of scope here.
func sortedPortStrings(byKey map[endpointKey][]int) map[endpointKey][]string {
	out := make(map[endpointKey][]string, len(byKey))
	for k, ports := range byKey {
		sort.Ints(ports)
		rendered := make([]string, 0, len(ports))
		for _, p := range ports {
			rendered = append(rendered, strconv.Itoa(p))
		}
		out[k] = rendered
	}
	return out
}

// groupMetadataByEndpointKey folds raw metadata items into ports / adminPorts grouped by
// endpointKey and returns the keys sorted for deterministic yaml output. Port 0 / AdminPort 0
// entries are dropped here so callers don't have to special-case them again.
// Both the key order and the ports within each key are sorted, so the rendered yaml depends
// only on the metadata contents and not on the order the items arrived in.
func groupMetadataByEndpointKey(
	list []probeconfig.ProbeMetadataItem,
) ([]endpointKey, map[endpointKey][]string, map[endpointKey][]string) {
	keys := make(map[endpointKey]struct{})
	portsByKey := make(map[endpointKey][]int)
	adminPortsByKey := make(map[endpointKey][]int)

	for _, m := range list {
		k := newEndpointKey(m)
		keys[k] = struct{}{}
		if m.Port > 0 {
			portsByKey[k] = append(portsByKey[k], m.Port)
		}
		if m.AdminPort > 0 {
			adminPortsByKey[k] = append(adminPortsByKey[k], m.AdminPort)
		}
	}

	ordered := make([]endpointKey, 0, len(keys))
	for k := range keys {
		ordered = append(ordered, k)
	}
	sortEndpointKeys(ordered)
	return ordered, sortedPortStrings(portsByKey), sortedPortStrings(adminPortsByKey)
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

// GenOption sets a field of the rendered config that does not come from the admin payload.
type GenOption func(*probeYAML)

// LocalFields returns the options that carry over every part of cfg that a rendered config
// cannot derive from the admin payload.
func LocalFields(cfg Configuration) []GenOption {
	opts := []GenOption{
		WithVersion(cfg.Version),
		WithServiceID(cfg.ServiceID),
		WithPidFile(cfg.PidFile),
		WithLog(cfg.Log),
		WithClient(cfg.Client),
		WithAdmin(cfg.Admin),
		WithClearPorts(cfg.ClearPorts),
	}
	if cfg.Reporter != nil {
		opts = append(opts, WithBkCloudID(cfg.Reporter.BkCloudID))
	}
	return opts
}

// WithVersion overrides the rendered config version.
//
// An empty version is ignored rather than rendered: a config written before the version field
// existed parses as empty, and echoing that back would replace the current default with
// version: "" on the first sync.
func WithVersion(version string) GenOption {
	return func(cfg *probeYAML) {
		if version == "" {
			return
		}
		cfg.Version = version
	}
}

// WithServiceID carries the probe's service identity over. Admin does not send it, so dropping
// it would restart the runtime under an empty identity and strip it from reported data.
func WithServiceID(serviceID string) GenOption {
	return func(cfg *probeYAML) {
		cfg.ServiceID = serviceID
	}
}

// WithPidFile keeps the local pid file path. An empty value falls through to the rendered
// default rather than blanking the key, mirroring how Parse normalizes it.
func WithPidFile(pidFile string) GenOption {
	return func(cfg *probeYAML) {
		if pidFile == "" {
			return
		}
		cfg.PidFile = pidFile
	}
}

// WithLog keeps the local logging settings. A zero-valued block would render a log destination
// of "" with level "", so it is ignored in favour of the rendered default.
func WithLog(log LogConfig) GenOption {
	return func(cfg *probeYAML) {
		if log == (LogConfig{}) {
			return
		}
		cfg.Log = log
	}
}

// WithBkCloudID keeps the cloud id the reporter tags data with. It is not part of the admin
// payload's reporter block, so without this a rewrite would silently reset it to 0.
func WithBkCloudID(bkCloudID int) GenOption {
	return func(cfg *probeYAML) {
		cfg.Reporter.BkCloudID = bkCloudID
	}
}

// WithClient keeps the local gRPC client tuning. A zero-valued block is left out entirely
// instead of being rendered: the pointer would not be nil, so omitempty alone would still emit
// an empty client: {} and make every sync look like a change.
func WithClient(client ClientConfig) GenOption {
	return func(cfg *probeYAML) {
		if client == (ClientConfig{}) {
			return
		}
		cfg.Client = &probeClientYAML{
			PingTime:                     durationToYAML(client.PingTime),
			PingTimeout:                  durationToYAML(client.PingTimeout),
			MaxReceiveMessageSize:        client.MaxReceiveMessageSize,
			MaxSendMessageSize:           client.MaxSendMessageSize,
			ReceiverReconnectInterval:    durationToYAML(client.ReceiverReconnectInterval),
			ReceiverMaxReconnectAttempts: client.ReceiverMaxReconnectAttempts,
		}
	}
}

// WithAdmin keeps the block describing how to reach admin. Same zero-value handling as
// WithClient, for the same reason.
func WithAdmin(admin AdminConfig) GenOption {
	return func(cfg *probeYAML) {
		if admin.IsZero() {
			return
		}
		endpoints := make([]string, len(admin.Endpoints))
		copy(endpoints, admin.Endpoints)
		cfg.Admin = &probeAdminYAML{
			Endpoints:    endpoints,
			BkCloudID:    admin.BkCloudID,
			LocalIP:      admin.LocalIP,
			SyncInterval: durationToYAML(admin.SyncInterval),
		}
	}
}

// WithClearPorts persists the operator's port exclusions and applies them to the rendered
// harvester. An empty list is a no-op so configs that predate the field round-trip unchanged.
//
// Ports are sorted and deduplicated before writing so two writers that carry the same set
// produce the same YAML bytes. Filtering happens after the payload has been rendered: that
// keeps GenProbeYAML's signature stable and lets periodic sync reuse this option through
// LocalFields instead of re-implementing the cut.
func WithClearPorts(ports []int) GenOption {
	return func(cfg *probeYAML) {
		if len(ports) == 0 {
			return
		}
		cfg.ClearPorts = normalizeClearPorts(ports)
		dropClearedPorts(&cfg.Harvester, cfg.ClearPorts)
	}
}

func normalizeClearPorts(ports []int) []int {
	seen := make(map[int]struct{}, len(ports))
	out := make([]int, 0, len(ports))
	for _, port := range ports {
		if port < 1 || port > 65535 {
			continue
		}
		if _, ok := seen[port]; ok {
			continue
		}
		seen[port] = struct{}{}
		out = append(out, port)
	}
	sort.Ints(out)
	return out
}

func dropClearedPorts(h *probeHarvesterYAML, ports []int) {
	drop := make(map[string]struct{}, len(ports))
	for _, port := range ports {
		drop[strconv.Itoa(port)] = struct{}{}
	}

	proxyAdminBefore := mysqlProxyAdminOwners(h)
	h.MySQL = filterMySQLHarvester(h.MySQL, drop)
	h.MySQLProxyAdmin = filterMySQLHarvester(h.MySQLProxyAdmin, drop)
	h.Redis = filterRedisHarvester(h.Redis, drop)
	if h.Extra != nil {
		for name, block := range h.Extra {
			filtered := filterMySQLHarvester(block, drop)
			if filtered == nil {
				delete(h.Extra, name)
			} else {
				h.Extra[name] = filtered
			}
		}
		if len(h.Extra) == 0 {
			h.Extra = nil
		}
	}
	dropOrphanMysqlProxyData(h, proxyAdminBefore)
}

func mysqlProxyAdminOwners(h *probeHarvesterYAML) map[endpointKey]struct{} {
	keys := make(map[endpointKey]struct{})
	for _, block := range []*probeMySQLHarvesterYAML{h.MySQLProxyAdmin, h.MySQL} {
		if block == nil {
			continue
		}
		for _, ep := range block.Endpoints {
			if len(ep.AdminPorts) == 0 {
				continue
			}
			if !isMysqlProxyEndpoint(string(ep.ClusterType), string(ep.MachineType), string(ep.AccessLayer)) {
				continue
			}
			keys[endpointIdentity(ep)] = struct{}{}
		}
	}
	return keys
}

func endpointIdentity(ep DbEndpointConfig) endpointKey {
	return endpointKey{
		ip:           ep.Ip,
		clusterType:  string(ep.ClusterType),
		machineType:  string(ep.MachineType),
		instanceRole: string(ep.InstanceRole),
		accessLayer:  string(ep.AccessLayer),
	}
}

func dropOrphanMysqlProxyData(h *probeHarvesterYAML, proxyAdminBefore map[endpointKey]struct{}) {
	if h.MySQL == nil || len(proxyAdminBefore) == 0 {
		return
	}
	remaining := mysqlProxyAdminOwners(h)
	kept := h.MySQL.Endpoints[:0]
	for _, ep := range h.MySQL.Endpoints {
		if isMysqlProxyEndpoint(string(ep.ClusterType), string(ep.MachineType), string(ep.AccessLayer)) {
			key := endpointIdentity(ep)
			if _, had := proxyAdminBefore[key]; had {
				if _, still := remaining[key]; !still {
					continue
				}
			}
		}
		kept = append(kept, ep)
	}
	h.MySQL.Endpoints = kept
	if len(h.MySQL.Endpoints) == 0 {
		h.MySQL = nil
	}
}

func filterMySQLHarvester(block *probeMySQLHarvesterYAML, drop map[string]struct{}) *probeMySQLHarvesterYAML {
	if block == nil {
		return nil
	}
	block.Endpoints = filterEndpoints(block.Endpoints, drop)
	if len(block.Endpoints) == 0 {
		return nil
	}
	return block
}

func filterRedisHarvester(block *probeRedisHarvesterYAML, drop map[string]struct{}) *probeRedisHarvesterYAML {
	if block == nil {
		return nil
	}
	block.Endpoints = filterEndpoints(block.Endpoints, drop)
	if len(block.Endpoints) == 0 {
		return nil
	}
	return block
}

func filterEndpoints(endpoints []DbEndpointConfig, drop map[string]struct{}) []DbEndpointConfig {
	out := make([]DbEndpointConfig, 0, len(endpoints))
	for _, ep := range endpoints {
		ep.Ports = filterPortStrings(ep.Ports, drop)
		ep.AdminPorts = filterPortStrings(ep.AdminPorts, drop)
		if len(ep.Ports) == 0 && len(ep.AdminPorts) == 0 {
			continue
		}
		out = append(out, ep)
	}
	return out
}

func filterPortStrings(ports []string, drop map[string]struct{}) []string {
	if len(ports) == 0 {
		return nil
	}
	out := make([]string, 0, len(ports))
	for _, port := range ports {
		if _, ok := drop[port]; ok {
			continue
		}
		out = append(out, port)
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func durationToYAML(d time.Duration) string {
	if d == 0 {
		return ""
	}
	return d.String()
}

func isMysqlProxyEndpoint(clusterType, machineType, accessLayer string) bool {
	return clusterType == string(haprobe.DbmMetadataClusterTypeTendbha) &&
		accessLayer == string(haprobe.DbmMetadataAccessLayerTypeProxy) &&
		machineType == string(haprobe.DbmMetadataMachineTypeProxy)
}
