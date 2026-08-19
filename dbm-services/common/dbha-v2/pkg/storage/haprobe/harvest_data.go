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

import (
	"encoding/json"
)

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
	DbmMetadataClusterTypeTendbha                  DbmMetadataClusterType = "tendbha"
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
	DbmMetadataMachineTypePulsarBroker     DbmMetadataMachineType = "pulsar_broker"
	DbmMetadataMachineTypePulsarZookeeper  DbmMetadataMachineType = "pulsar_zookeeper"
)

// DbmMetadataInstanceRole the instance role for the metadata.
type DbmMetadataInstanceRole string

const (
	// mysql instance role
	MySQLStorageMaster   DbmMetadataInstanceRole = "backend_master"
	MySQLStorageSlave    DbmMetadataInstanceRole = "backend_slave"
	MySQLStorageRepeater DbmMetadataInstanceRole = "backend_repeater"

	// tendbcluster instance role
	TenDBClusterStorageMaster DbmMetadataInstanceRole = "remote_master"
	TenDBClusterStorageSlave  DbmMetadataInstanceRole = "remote_slave"
	TenDBClusterProxyMaster   DbmMetadataInstanceRole = "spider_master"
	TenDBClusterProxySlave    DbmMetadataInstanceRole = "spider_slave"
)

// String returns the string representation of DbmMetadataInstanceRole.
func (d DbmMetadataInstanceRole) String() string {
	return string(d)
}

// DbmMetadataSpiderRole the spider role for the metadata.
type DbmMetadataSpiderRole string

const (
	TenDBClusterSpiderMaster DbmMetadataSpiderRole = "spider_master"
	TenDBClusterSpiderSlave  DbmMetadataSpiderRole = "spider_slave"
)

// HarvestType identifies which collection group a HarvestData belongs to.
type HarvestType string

const (
	// HarvestTypeDefault is the original full-snapshot collection group.
	HarvestTypeDefault HarvestType = "default"
	// HarvestTypeHeartbeat is the high-frequency heartbeat-only collection group.
	HarvestTypeHeartbeat HarvestType = "heartbeat"
	// HarvestTypeReplDelay is the low-frequency replication-delay (slave status) collection group.
	HarvestTypeReplDelay HarvestType = "repldelay"
)

// String returns the string representation of HarvestType.
func (t HarvestType) String() string {
	return string(t)
}

// HarvestBaseData represents the base data collected by harvester
type HarvestBaseData struct {
	HarvestType     HarvestType                `json:"harvest_type"`
	SequenceID      uint64                     `json:"sequence_id,omitempty"`
	MachineID       string                     `json:"machine_id,omitempty"`
	AgentID         string                     `json:"agent_id,omitempty"`
	BkCloudID       int                        `json:"bk_cloud_id,omitempty"`
	MessageID       string                     `json:"message_id,omitempty"`
	ServiceID       string                     `json:"service_id,omitempty"`
	DbTypeName      DbType                     `json:"db_type_name,omitempty"`
	AccessLayer     DbmMetadataAccessLayerType `json:"access_layer,omitempty"`
	ClusterType     DbmMetadataClusterType     `json:"cluster_type,omitempty"`
	MachineType     DbmMetadataMachineType     `json:"machine_type,omitempty"`
	InstanceRole    DbmMetadataInstanceRole    `json:"instance_role,omitempty"`
	DbIp            string                     `json:"db_ip,omitempty"`
	DbPort          int                        `json:"db_port,omitempty"`
	ReportTimestamp uint64                     `json:"report_timestamp,omitempty"`
	Events          []*DbEvent                 `json:"events,omitempty"`
	Host            *HostMetric                `json:"host,omitempty"`
	Probe           *ProbeMetric               `json:"probe,omitempty"`
}

// HarvestData contains the data collected by harvester
type HarvestData struct {
	HarvestBaseData
	Value    DBTyper         `json:"data,omitempty"`
	RawValue json.RawMessage `json:"-"`
}

// UnmarshalJSON implements the json.Unmarshaler interface
func (h *HarvestData) UnmarshalJSON(data []byte) error {
	var temp struct {
		HarvestBaseData
		Value json.RawMessage `json:"data,omitempty"`
	}

	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}

	h.HarvestBaseData = temp.HarvestBaseData
	h.RawValue = temp.Value

	return nil
}
