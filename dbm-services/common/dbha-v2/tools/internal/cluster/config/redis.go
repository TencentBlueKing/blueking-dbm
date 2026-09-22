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
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// RedisShard represents one redis master-slave group, i.e. one twemproxy backend shard.
// It carries no redis-cluster slot information.
type RedisShard struct {
	Master InstanceAddress   `yaml:"master"`
	Slave  []InstanceAddress `yaml:"slave"`
}

// RedisCluster represents a redis cluster handled by dbha-v2 switch.
type RedisCluster struct {
	Domain      string                         `yaml:"domain"`
	ClusterId   int                            `yaml:"clusterId"`
	BkBizId     int                            `yaml:"bkBizId"`
	BkCloudId   int                            `yaml:"bkCloudId"`
	Proxy       []ProxyAddress                 `yaml:"proxy"`
	Shards      []RedisShard                   `yaml:"shards,omitempty"`
	Clb         []ClbConfig                    `yaml:"clb,omitempty"`
	ClusterType haprobe.DbmMetadataClusterType `yaml:"-"`
}

type redisProxyLayer int

const (
	redisProxyNone redisProxyLayer = iota
	redisProxyTwemproxy
	redisProxyPredixy
)

type redisStorageLayer int

const (
	redisStorageMasterSlave redisStorageLayer = iota
	redisStorageClusterProtocol
)

// redisClusterKind is the single registration of one redis cluster type.
// Adding a type only requires appending one entry here.
type redisClusterKind struct {
	clusterType    haprobe.DbmMetadataClusterType
	proxy          redisProxyLayer
	proxyMachine   haprobe.DbmMetadataMachineType
	storage        redisStorageLayer
	storageMachine haprobe.DbmMetadataMachineType
}

var redisClusterKinds = []redisClusterKind{
	{
		clusterType:    ClusterTypeRedisInstance,
		proxy:          redisProxyNone,
		storage:        redisStorageMasterSlave,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisCache,
	},
	{
		clusterType:    ClusterTypeTwemproxyRedisInstance,
		proxy:          redisProxyTwemproxy,
		proxyMachine:   haprobe.DbmMetadataMachineTypeTwemProxy,
		storage:        redisStorageMasterSlave,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisCache,
	},
	{
		clusterType:    ClusterTypeTwemproxyTendisSSDInstance,
		proxy:          redisProxyTwemproxy,
		proxyMachine:   haprobe.DbmMetadataMachineTypeTwemProxy,
		storage:        redisStorageMasterSlave,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisSSD,
	},
	{
		clusterType:    ClusterTypePredixyTendisplusInstance,
		proxy:          redisProxyPredixy,
		proxyMachine:   haprobe.DbmMetadataMachineTypePredixy,
		storage:        redisStorageMasterSlave,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisPlus,
	},
	{
		clusterType:    ClusterTypePredixyRedisCluster,
		proxy:          redisProxyPredixy,
		proxyMachine:   haprobe.DbmMetadataMachineTypePredixy,
		storage:        redisStorageClusterProtocol,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisCache,
	},
	{
		clusterType:    ClusterTypePredixyTendisplusCluster,
		proxy:          redisProxyPredixy,
		proxyMachine:   haprobe.DbmMetadataMachineTypePredixy,
		storage:        redisStorageClusterProtocol,
		storageMachine: haprobe.DbmMetadataMachineTypeTendisPlus,
	},
}

func redisClusterKindOf(clusterType haprobe.DbmMetadataClusterType) (redisClusterKind, bool) {
	for _, kind := range redisClusterKinds {
		if kind.clusterType == clusterType {
			return kind, true
		}
	}
	return redisClusterKind{}, false
}

func allRedisClusterTypes() []haprobe.DbmMetadataClusterType {
	out := make([]haprobe.DbmMetadataClusterType, 0, len(redisClusterKinds))
	for _, kind := range redisClusterKinds {
		out = append(out, kind.clusterType)
	}
	return out
}

// IsMasterSlaveRedisClusterType reports whether the storage layer of this cluster type is switched by dbha-v2.
func IsMasterSlaveRedisClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	kind, ok := redisClusterKindOf(clusterType)
	return ok && kind.storage == redisStorageMasterSlave
}

// IsClusterProtocolRedisClusterType reports whether the cluster elects a new master by itself.
func IsClusterProtocolRedisClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	kind, ok := redisClusterKindOf(clusterType)
	return ok && kind.storage == redisStorageClusterProtocol
}

// IsTwemproxyRedisClusterType reports whether the proxy layer of this cluster type is twemproxy.
func IsTwemproxyRedisClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	kind, ok := redisClusterKindOf(clusterType)
	return ok && kind.proxy == redisProxyTwemproxy
}

// IsPredixyRedisClusterType reports whether the proxy layer of this cluster type is predixy.
func IsPredixyRedisClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	kind, ok := redisClusterKindOf(clusterType)
	return ok && kind.proxy == redisProxyPredixy
}

// HasRedisProxy reports whether the cluster type has a proxy layer.
func HasRedisProxy(clusterType haprobe.DbmMetadataClusterType) bool {
	kind, ok := redisClusterKindOf(clusterType)
	return ok && kind.proxy != redisProxyNone
}

// RedisProxyMachineType returns the proxy machine type registered for a cluster type.
func RedisProxyMachineType(clusterType haprobe.DbmMetadataClusterType) (haprobe.DbmMetadataMachineType, bool) {
	kind, ok := redisClusterKindOf(clusterType)
	if !ok || kind.proxyMachine == "" {
		return "", false
	}
	return kind.proxyMachine, true
}

// RedisStorageMachineType returns the storage machine type registered for a cluster type.
func RedisStorageMachineType(clusterType haprobe.DbmMetadataClusterType) (haprobe.DbmMetadataMachineType, error) {
	kind, ok := redisClusterKindOf(clusterType)
	if !ok || kind.storageMachine == "" {
		return "", gerrors.Newf(gerrors.InvalidParameter,
			"cluster type has no storage machine type, cluster_type: %s", clusterType)
	}
	return kind.storageMachine, nil
}

// NormalizeRedisClusterType resolves a user-supplied cluster type to its canonical
// haprobe name, matching case-insensitively so the flag does not need exact camel case.
func NormalizeRedisClusterType(clusterType string) (haprobe.DbmMetadataClusterType, bool) {
	for _, known := range allRedisClusterTypes() {
		if strings.EqualFold(known.String(), clusterType) {
			return known, true
		}
	}
	return "", false
}

// validateRedisClusters only rejects entries the reset flow would choke on.
// Settings that simply do not apply to a cluster type are left alone here and
// reported as skipped while the cluster is being reset.
func validateRedisClusters(cfg *Config) error {
	for _, cluster := range cfg.RedisClustersOfType("") {
		if cluster.Domain == "" {
			return gerrors.Newf(gerrors.InvalidConfiguration,
				"redis cluster domain is required, cluster_type: %s", cluster.ClusterType)
		}

		if !IsMasterSlaveRedisClusterType(cluster.ClusterType) || len(cluster.Shards) == 0 {
			continue
		}

		if cluster.ClusterId <= 0 {
			return gerrors.Newf(gerrors.InvalidConfiguration,
				"redis cluster clusterId is required to query the storage password, domain: %s", cluster.Domain)
		}

		for j := range cluster.Shards {
			if cluster.Shards[j].Master.Host == "" || cluster.Shards[j].Master.Port <= 0 {
				return gerrors.Newf(gerrors.InvalidConfiguration,
					"redis cluster shard has no valid master, domain: %s, shard: %d", cluster.Domain, j)
			}
		}
	}

	return nil
}
