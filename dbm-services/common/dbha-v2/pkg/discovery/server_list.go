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

package discovery

import (
	"context"
	"encoding/json"
	"sort"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// PrefixReader reads every key-value pair under an etcd key prefix.
// *Discovery satisfies this interface.
type PrefixReader interface {
	GetWithPrefix(ctx context.Context, key string) (map[string][]byte, error)
}

// HA server roles that register themselves under the self segment.
const (
	HaServerRoleAdmin    = "admin"
	HaServerRoleAnalysis = "analysis"
	HaServerRoleReceiver = "receiver"
)

const etcdKeySeparator = "/"

// HaServer is one live HA server instance parsed from a self registration.
type HaServer struct {
	Role      string
	ID        string
	IPs       []string
	StartTime time.Time
	UpdatedAt time.Time
	Uptime    string
}

// HaServerList is the merged view of all live HA server instances.
// IPs is derived from Servers, deduplicated and sorted.
type HaServerList struct {
	Servers []HaServer
	IPs     []string
}

// HaServerRoles returns the HA server roles in output order: admin, analysis, receiver.
func HaServerRoles() []string {
	return []string{HaServerRoleAdmin, HaServerRoleAnalysis, HaServerRoleReceiver}
}

// HaServerSelfPrefix returns the self registration prefix of role under the default
// registry root, e.g. /dbha/registry/analysis/self. Custom registry roots are not supported.
func HaServerSelfPrefix(role string) string {
	return defaultRegistryRootKeyPrefix + etcdKeySeparator + role + etcdKeySeparator + etcdKeySegmentSelf
}

// ListHaServers reads the self prefix of every HA server role and returns the merged list.
// All reads share one deadline of timeout; a non-positive timeout falls back to
// constant.DefaultServiceUpdateTimeout. Any read error fails the whole call and no partial
// result is returned. Invalid registrations are skipped. On success Servers and IPs are
// never nil.
func ListHaServers(ctx context.Context, reader PrefixReader, timeout time.Duration) (*HaServerList, error) {
	if timeout <= 0 {
		timeout = constant.DefaultServiceUpdateTimeout
	}

	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	kvs := map[string][]byte{}
	for _, role := range HaServerRoles() {
		roleKvs, err := reader.GetWithPrefix(ctx, HaServerSelfPrefix(role))
		if err != nil {
			return nil, err
		}

		for key, value := range roleKvs {
			kvs[key] = value
		}
	}

	return ParseHaServers(kvs), nil
}

// ParseHaServers converts raw self registrations into a sorted HaServerList.
// kvs is keyed by the full etcd key. Only keys shaped like {root}/{role}/self/{id} with a
// known role are accepted; records with an empty value, invalid JSON, a name that differs
// from the key role, an empty id, or no non-empty IP are skipped and logged.
// Servers are ordered by role (admin, analysis, receiver) then id, and each instance's IPs
// are sorted. Servers and IPs are never nil.
func ParseHaServers(kvs map[string][]byte) *HaServerList {
	servers := make([]HaServer, 0, len(kvs))
	for key, value := range kvs {
		server, ok := parseHaServer(key, value)
		if ok {
			servers = append(servers, server)
		}
	}

	sortHaServers(servers)

	return &HaServerList{Servers: servers, IPs: collectHaServerIPs(servers)}
}

func parseHaServer(key string, value []byte) (HaServer, bool) {
	role, ok := haServerRoleOfKey(key)
	if !ok {
		logger.Warn("skip ha server registration, key: %s, reason: invalid key", key)
		return HaServer{}, false
	}

	if len(value) == 0 {
		logger.Debug("skip ha server registration, key: %s, reason: empty value", key)
		return HaServer{}, false
	}

	var info ServiceInfo
	if err := json.Unmarshal(value, &info); err != nil {
		logger.Warn("skip ha server registration, key: %s, reason: invalid json, errmsg: %s", key, err)
		return HaServer{}, false
	}

	reason := validateHaServerInfo(role, &info)
	if reason != "" {
		logger.Warn("skip ha server registration, key: %s, reason: %s", key, reason)
		return HaServer{}, false
	}

	return HaServer{
		Role:      role,
		ID:        info.ID,
		IPs:       info.IPs,
		StartTime: info.StartTime,
		UpdatedAt: info.UpdatedAt,
		Uptime:    info.Uptime,
	}, true
}

// validateHaServerInfo drops empty IPs in place and returns the skip reason, or "" if valid.
func validateHaServerInfo(role string, info *ServiceInfo) string {
	if info.Name != role {
		return "name does not match key role"
	}

	if info.ID == "" {
		return "empty id"
	}

	info.IPs = nonEmptyStrings(info.IPs)
	if len(info.IPs) == 0 {
		return "empty ips"
	}

	sort.Strings(info.IPs)

	return ""
}

// haServerRoleOfKey returns the role of a key shaped exactly like {root}/{role}/self/{id}.
func haServerRoleOfKey(key string) (string, bool) {
	rest, ok := strings.CutPrefix(key, defaultRegistryRootKeyPrefix+etcdKeySeparator)
	if !ok {
		return "", false
	}

	parts := strings.Split(rest, etcdKeySeparator)
	if len(parts) != 3 || parts[1] != etcdKeySegmentSelf || parts[2] == "" {
		return "", false
	}

	if haServerRoleRank(parts[0]) < 0 {
		return "", false
	}

	return parts[0], true
}

// haServerRoleRank returns the output position of role, or -1 if role is not an HA server role.
func haServerRoleRank(role string) int {
	for i, r := range HaServerRoles() {
		if r == role {
			return i
		}
	}

	return -1
}

func sortHaServers(servers []HaServer) {
	sort.SliceStable(servers, func(i, j int) bool {
		ri, rj := haServerRoleRank(servers[i].Role), haServerRoleRank(servers[j].Role)
		if ri != rj {
			return ri < rj
		}

		return servers[i].ID < servers[j].ID
	})
}

func collectHaServerIPs(servers []HaServer) []string {
	seen := map[string]struct{}{}
	ips := make([]string, 0)
	for _, server := range servers {
		for _, ip := range server.IPs {
			if _, ok := seen[ip]; ok {
				continue
			}

			seen[ip] = struct{}{}
			ips = append(ips, ip)
		}
	}

	sort.Strings(ips)

	return ips
}

func nonEmptyStrings(values []string) []string {
	result := make([]string, 0, len(values))
	for _, v := range values {
		if v != "" {
			result = append(result, v)
		}
	}

	return result
}
