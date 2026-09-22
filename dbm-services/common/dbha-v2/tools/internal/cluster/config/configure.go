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

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gopkg.in/yaml.v3"
)

// Config represents the configuration of the cluster tool.
// Redis yaml keys use the standard cluster type names declared in cluster_type.go.
type Config struct {
	MysqlClusters []MysqlCluster `yaml:"mysqlClusters"`
	TenDBClusters []TenDBCluster `yaml:"tenDBClusters"`

	RedisInstance              []RedisCluster `yaml:"RedisInstance"`
	TwemproxyRedisInstance     []RedisCluster `yaml:"TwemproxyRedisInstance"`
	TwemproxyTendisSSDInstance []RedisCluster `yaml:"TwemproxyTendisSSDInstance"`
	PredixyTendisplusInstance  []RedisCluster `yaml:"PredixyTendisplusInstance"`
	PredixyRedisCluster        []RedisCluster `yaml:"PredixyRedisCluster"`
	PredixyTendisplusCluster   []RedisCluster `yaml:"PredixyTendisplusCluster"`

	DbmServices DbmApis  `yaml:"dbmServices"`
	AuthInfo    AuthInfo `yaml:"authInfo"`
}

type redisClusterGroup struct {
	clusterType haprobe.DbmMetadataClusterType
	clusters    *[]RedisCluster
}

func (c *Config) redisClusterGroups() []redisClusterGroup {
	return []redisClusterGroup{
		{ClusterTypeRedisInstance, &c.RedisInstance},
		{ClusterTypeTwemproxyRedisInstance, &c.TwemproxyRedisInstance},
		{ClusterTypeTwemproxyTendisSSDInstance, &c.TwemproxyTendisSSDInstance},
		{ClusterTypePredixyTendisplusInstance, &c.PredixyTendisplusInstance},
		{ClusterTypePredixyRedisCluster, &c.PredixyRedisCluster},
		{ClusterTypePredixyTendisplusCluster, &c.PredixyTendisplusCluster},
	}
}

// ClusterConfig represents the global cluster configuration instance
var ClusterConfig *Config

// SetClusterConfig sets the global configuration
func SetClusterConfig(config *Config) {
	ClusterConfig = config
}

// ClusterTypeOptions lists every --type value reset and show accept:
// the db-type family keywords, then each standard cluster type.
func ClusterTypeOptions() []string {
	options := []string{DbTypeMysql.String()}
	options = append(options, clusterTypeNames(mysqlClusterTypes)...)
	options = append(options, DbTypeRedis.String())
	return append(options, clusterTypeNames(allRedisClusterTypes())...)
}

// RedisClustersOfType returns the configured redis clusters of one type,
// or every redis cluster when clusterType is empty.
func (c *Config) RedisClustersOfType(clusterType haprobe.DbmMetadataClusterType) []*RedisCluster {
	targets := make([]*RedisCluster, 0)
	if c == nil {
		return targets
	}
	for _, group := range c.redisClusterGroups() {
		if clusterType != "" && group.clusterType != clusterType {
			continue
		}
		for i := range *group.clusters {
			targets = append(targets, &(*group.clusters)[i])
		}
	}
	return targets
}

// stampRedisClusterTypes stamps the cluster type to the redis cluster
func (c *Config) stampRedisClusterTypes() {
	for _, group := range c.redisClusterGroups() {
		for i := range *group.clusters {
			(*group.clusters)[i].ClusterType = group.clusterType
		}
	}
}

// LoadConfig loads configuration from YAML file
func LoadConfig(configFile string) (*Config, error) {
	data, err := os.ReadFile(configFile)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to read config file, errmsg: %s", err.Error())
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidYaml, "failed to parse config, errmsg: %s", err.Error())
	}

	config.stampRedisClusterTypes()
	if err := validateRedisClusters(&config); err != nil {
		return nil, err
	}

	return &config, nil
}
