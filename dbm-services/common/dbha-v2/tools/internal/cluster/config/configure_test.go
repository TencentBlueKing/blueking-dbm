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
	"os"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestClusterTypeOptionsUsesHaprobeNames(t *testing.T) {
	t.Parallel()

	options := ClusterTypeOptions()
	assert.Equal(t, []string{
		DbTypeMysql.String(),
		ClusterTypeTendbha.String(),
		ClusterTypeTendbCluster.String(),
		DbTypeRedis.String(),
		ClusterTypeRedisInstance.String(),
		ClusterTypeTwemproxyRedisInstance.String(),
		ClusterTypeTwemproxyTendisSSDInstance.String(),
		ClusterTypePredixyTendisplusInstance.String(),
		ClusterTypePredixyRedisCluster.String(),
		ClusterTypePredixyTendisplusCluster.String(),
	}, options)
}

func TestNormalizeRedisClusterType(t *testing.T) {
	t.Parallel()

	got, ok := NormalizeRedisClusterType("twemproxyredisinstance")
	require.True(t, ok)
	assert.Equal(t, ClusterTypeTwemproxyRedisInstance, got)

	_, ok = NormalizeRedisClusterType(ClusterTypeTendbha.String())
	assert.False(t, ok)
}

func TestRedisClusterKindLookup(t *testing.T) {
	t.Parallel()

	assert.True(t, IsMasterSlaveRedisClusterType(ClusterTypeTwemproxyRedisInstance))
	assert.True(t, IsTwemproxyRedisClusterType(ClusterTypeTwemproxyRedisInstance))
	assert.False(t, IsPredixyRedisClusterType(ClusterTypeTwemproxyRedisInstance))
	assert.True(t, HasRedisProxy(ClusterTypeTwemproxyRedisInstance))

	proxyMachine, ok := RedisProxyMachineType(ClusterTypeTwemproxyRedisInstance)
	assert.True(t, ok)
	assert.Equal(t, haprobe.DbmMetadataMachineTypeTwemProxy, proxyMachine)

	assert.True(t, IsClusterProtocolRedisClusterType(ClusterTypePredixyRedisCluster))
	assert.True(t, IsPredixyRedisClusterType(ClusterTypePredixyRedisCluster))
	assert.False(t, IsTwemproxyRedisClusterType(ClusterTypePredixyRedisCluster))

	proxyMachine, ok = RedisProxyMachineType(ClusterTypePredixyRedisCluster)
	assert.True(t, ok)
	assert.Equal(t, haprobe.DbmMetadataMachineTypePredixy, proxyMachine)

	assert.False(t, HasRedisProxy(ClusterTypeRedisInstance))
	_, ok = RedisProxyMachineType(ClusterTypeRedisInstance)
	assert.False(t, ok)

	machineType, err := RedisStorageMachineType(ClusterTypeTwemproxyTendisSSDInstance)
	require.NoError(t, err)
	assert.Equal(t, haprobe.DbmMetadataMachineTypeTendisSSD, machineType)

	machineType, err = RedisStorageMachineType(ClusterTypePredixyRedisCluster)
	require.NoError(t, err)
	assert.Equal(t, haprobe.DbmMetadataMachineTypeTendisCache, machineType)
}

func TestLoadRedisClustersFromYAML(t *testing.T) {
	t.Parallel()

	const body = `
TwemproxyRedisInstance:
  - domain: cache.example.db
    clusterId: 1001
    shards:
      - master:
          host: 127.0.0.1
          port: 30000
PredixyRedisCluster:
  - domain: cluster.example.db
`
	tmp := t.TempDir() + "/cluster.yaml"
	require.NoError(t, os.WriteFile(tmp, []byte(body), 0644))

	cfg, err := LoadConfig(tmp)
	require.NoError(t, err)

	twem := cfg.RedisClustersOfType(ClusterTypeTwemproxyRedisInstance)
	require.Len(t, twem, 1)
	assert.Equal(t, "cache.example.db", twem[0].Domain)
	assert.Equal(t, ClusterTypeTwemproxyRedisInstance, twem[0].ClusterType)

	predixy := cfg.RedisClustersOfType(ClusterTypePredixyRedisCluster)
	require.Len(t, predixy, 1)
	assert.Equal(t, "cluster.example.db", predixy[0].Domain)

	assert.Len(t, cfg.RedisClustersOfType(""), 2)
}
