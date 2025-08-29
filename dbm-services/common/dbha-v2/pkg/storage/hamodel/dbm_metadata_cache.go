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

package hamodel

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// DbmMetadataClusterType the cluster type for the metadata.
type DbmMetadataClusterType string

// DbmMetadataMachineType the machine type for the metadata.
type DbmMetadataMachineType string

const (
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

func (m DbmMetadataClusterType) String() string {
	return string(m)
}

func (m DbmMetadataMachineType) String() string {
	return string(m)
}

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	DbmMetadataTableName            = "t_dbm_metadata"
	DbmMetadataFieldBkCloudID       = "bk_cloud_id"
	DbmMetadataFieldListenIP        = "ip"
	DbmMetadataFieldListenPort      = "port"
	DbmMetadataFieldBkIdcCityID     = "bk_idc_city_id"
	DbmMetadataFieldBkBizID         = "bk_biz_id"
	DbmMetadataFieldLogicalCityID   = "logical_city_id"
	DbmMetadataFieldLogicalCityName = "logical_city_name"
	DbmMetadataFieldCluster         = "cluster"
	DbmMetadataFieldClusterID       = "cluster_id"
	DbmMetadataFieldClusterType     = "cluster_type"
	DbmMetadataFieldMachineType     = "machine_type"
	DbmMetadataFieldStatus          = "status"
	DbmMetadataFieldBindEntry       = "bind_entry"
	DbmMetadataFieldCreatedAt       = "created_at"
	DbmMetadataFieldUpdatedAt       = "updated_at"
	DbmMetadataFieldDeletedAt       = "deleted_at"
	DbmMetadataFieldSyncDuration    = "sync_duration"
)

type BindEntry struct {
	BindPort       int      `json:"bind_port"`
	BindIps        []string `json:"bind_ips"`
	Domain         string   `json:"domain"`
	EntryRole      string   `json:"entry_role"`
	ForwardEntryId any      `json:"forward_entry_id"`
	ClbIP          string   `json:"clb_ip"`
	ClbID          string   `json:"clb_id"`
	ClbListenerID  string   `json:"listener_id"`
	ClbRegion      string   `json:"clb_region"`
}

type BindEntryType map[string][]BindEntry

// Scan Implement Scanner interface for reading from DB.
func (be *BindEntryType) Scan(value interface{}) error {
	if value == nil {
		*be = nil
		return nil
	}

	bytes, ok := value.([]byte)
	if !ok {
		return gerrors.Newf(gerrors.Failure, "failed to scan BindEntryType: expected []byte, got: %T", value)
	}

	return json.Unmarshal(bytes, be)
}

// Value Implement Valuer interface for writing to DB.
func (be BindEntryType) Value() (driver.Value, error) {
	if be == nil {
		return nil, nil
	}

	return json.Marshal(be)
}

type DbmMetadata struct {
	BkCloudID       int                    `gorm:"column:bk_cloud_id;primaryKey"`
	IP              string                 `gorm:"column:ip;primaryKey"`
	Port            int                    `gorm:"column:port;primaryKey"`
	BkIdcCityID     int                    `gorm:"column:bk_idc_city_id"`
	BkBizID         int                    `gorm:"column:bk_biz_id"`
	LogicalCityID   int                    `gorm:"column:logical_city_id"`
	LogicalCityName string                 `gorm:"column:logcial_city_name"`
	Cluster         string                 `gorm:"column:cluster"`
	ClusterID       int                    `gorm:"column:cluster_id"`
	ClusterType     DbmMetadataClusterType `gorm:"column:cluster_type"`
	MachineType     DbmMetadataMachineType `gorm:"column:machine_type"`
	Status          string                 `gorm:"column:status"`
	BindEntry       BindEntryType          `gorm:"column:bind_entry;type:json"`
	CreatedAt       time.Time              `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt       time.Time              `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt       time.Time              `gorm:"column:deleted_at;index"`
	SyncDuration    time.Duration          `gorm:"column:sync_duration;type:bigint"`
}

func (t DbmMetadata) TableName() string {
	return DbmMetadataTableName
}
