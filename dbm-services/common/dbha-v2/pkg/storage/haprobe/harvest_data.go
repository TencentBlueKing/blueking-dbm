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

package haprobe

// DbmMetadataAccessLayerType the access layer type for the metadata.
type DbmMetadataAccessLayerType string

func (m DbmMetadataAccessLayerType) String() string {
	return string(m)
}

// DbmMetadataClusterType the cluster type for the metadata.
type DbmMetadataClusterType string

func (m DbmMetadataClusterType) String() string {
	return string(m)
}

// DbmMetadataMachineType the machine type for the metadata.
type DbmMetadataMachineType string

func (m DbmMetadataMachineType) String() string {
	return string(m)
}

const (
	// Access Layer
	DbmMetadataAccessLayerTypeProxy   DbmMetadataAccessLayerType = "proxy"
	DbmMetadataAccessLayerTypeStorage DbmMetadataAccessLayerType = "storage"

	// Cluster Type
	DbmMetadataClusterTypeTendb                    DbmMetadataClusterType = "tendbha"
	DbmMetadataClusterTypeSqlServer                DbmMetadataClusterType = "sqlserver_ha"
	DbmMetadataClusterTypeTendbCluster             DbmMetadataClusterType = "tendbcluster"
	DbmMetadataClusterTypeSqlServerSingle          DbmMetadataClusterType = "sqlserver_single"
	DbmMetadataClusterTypeMongoReplicaSet          DbmMetadataClusterType = "MongoReplicaSet"
	DbmMetadataClusterTypeRiak                     DbmMetadataClusterType = "riak"
	DbmMetadataClusterTypeHdfs                     DbmMetadataClusterType = "hdfs"
	DbmMetadataClusterTypeTwemproxyRedis           DbmMetadataClusterType = "TwemproxyRedisInstance"
	DbmMetadataClusterTypeRedis                    DbmMetadataClusterType = "RedisInstance"
	DbmMetadataClusterTypeEs                       DbmMetadataClusterType = "es"
	DbmMetadataClusterTypeTwemproxyTendisSSD       DbmMetadataClusterType = "TwemproxyTendisSSDInstance"
	DbmMetadataClusterTypeKafka                    DbmMetadataClusterType = "kafka"
	DbmMetadataClusterTypeMongoShardeCluster       DbmMetadataClusterType = "MongoShardedCluster"
	DbmMetadataClusterTypeDoris                    DbmMetadataClusterType = "doris"
	DbmMetadataClusterTypePredixyTendisplusCluster DbmMetadataClusterType = "PredixyTendisplusCluster"
	DbmMetadataClusterTypePredixyRedisCluster      DbmMetadataClusterType = "PredixyRedisCluster"
	DbmMetadataClusterTypePulsar                   DbmMetadataClusterType = "pulsar"

	// Machine Type
	DbmMetadataMachineTypeSingle           DbmMetadataMachineType = "single"
	DbmMetadataMachineTypeSqlServer        DbmMetadataMachineType = "sqlserver_ha"
	DbmMetadataMachineTypeProxy            DbmMetadataMachineType = "proxy"
	DbmMetadataMachineTypeBackend          DbmMetadataMachineType = "backend"
	DbmMetadataMachineTypeRemote           DbmMetadataMachineType = "remote"
	DbmMetadataMachineTypeSqlServerSingle  DbmMetadataMachineType = "sqlserver_single"
	DbmMetadataMachineTypeMongoDB          DbmMetadataMachineType = "mongodb"
	DbmMetadataMachineTypeRiak             DbmMetadataMachineType = "riak"
	DbmMetadataMachineTypeHdfsDataNode     DbmMetadataMachineType = "hdfs_datanode"
	DbmMetadataMachineTypeTwemProxy        DbmMetadataMachineType = "twemproxy"
	DbmMetadataMachineTypeTendisCache      DbmMetadataMachineType = "tendiscache"
	DbmMetadataMachineTypeEsDataNode       DbmMetadataMachineType = "es_datanode"
	DbmMetadataMachineTypeZookeeper        DbmMetadataMachineType = "zookeeper"
	DbmMetadataMachineTypeBroker           DbmMetadataMachineType = "broker"
	DbmMetadataMachineTypeTendisSSD        DbmMetadataMachineType = "tendisssd"
	DbmMetadataMachineTypeHdfsMaster       DbmMetadataMachineType = "hdfs_master"
	DbmMetadataMachineTypeDorisBackend     DbmMetadataMachineType = "doris_backend"
	DbmMetadataMachineTypeSpider           DbmMetadataMachineType = "spider"
	DbmMetadataMachineTypeMongos           DbmMetadataMachineType = "mongos"
	DbmMetadataMachineTypeEsClient         DbmMetadataMachineType = "es_client"
	DbmMetadataMachineTypeEsMaster         DbmMetadataMachineType = "es_master"
	DbmMetadataMachineTypeMongoConfig      DbmMetadataMachineType = "mongo_config"
	DbmMetadataMachineTypeTendisPlus       DbmMetadataMachineType = "tendisplus"
	DbmMetadataMachineTypePredixy          DbmMetadataMachineType = "predixy"
	DbmMetadataMachineTypePulsarBookKeeper DbmMetadataMachineType = "pulsar_bookkeeper"
	DbmMetadataMachineTypeDorisFollower    DbmMetadataMachineType = "doris_follower"
	DbmMetadataMachineTypePulsarBroker     DbmMetadataMachineType = "doris_broker"
	DbmMetadataMachineTypePulsarZookeeper  DbmMetadataMachineType = "pulsar_zookeeper"
)

type HarvestData struct {
	AccessLayer DbmMetadataAccessLayerType `json:"access_layer,omitempty"`
	ClusterType DbmMetadataClusterType     `json:"cluster_type,omitempty"`
	MachineType DbmMetadataMachineType     `json:"machine_type,omitempty"`
	Value       any                        `json:"data,omitempty"`
}
