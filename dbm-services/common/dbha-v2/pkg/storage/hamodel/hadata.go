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
	"encoding/json"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	DatabaseName            = "dbha_data"
	DbhaDataStatusTableName = "t_dbha_status"

	DbhaStatusFieldSequenceID      = "sequence_id"
	DbhaStatusFieldMachineID       = "machine_id"
	DbhaStatusFieldAgentID         = "agent_id"
	DbhaStatusFieldBkCloudID       = "bk_cloud_id"
	DbhaStatusFieldHarvestType     = "harvest_type"
	DbhaStatusFieldIPs             = "ips"
	DbhaStatusFieldMessageID       = "message_id"
	DbhaStatusFieldServiceID       = "service_id"
	DbhaStatusFieldAccessLayer     = "access_layer"
	DbhaStatusFieldClusterType     = "cluster_type"
	DbhaStatusFieldMachineType     = "machine_type"
	DbhaStatusFieldInstanceRole    = "instance_role"
	DbhaStatusFieldDbTypeName      = "db_type_name"
	DbhaStatusFieldDbIp            = "db_ip"
	DbhaStatusFieldDbPort          = "db_port"
	DbhaStatusFieldReportTimestamp = "report_timestamp"
	DbhaStatusFieldHost            = "host"
	DbhaStatusFieldData            = "data"
	DbhaStatusFieldCreatedAt       = "created_at"
	DbhaStatusFieldUpdatedAt       = "updated_at"
	DbhaStatusFieldDeletedAt       = "deleted_at"
)

// DbhaDataStatus contains system and databases metrics.
// Primary key includes harvest_type so one instance can keep one row per collection group
// (default / heartbeat / repldelay) in the same table.
type DbhaDataStatus struct {
	MachineID       string                             `gorm:"column:machine_id;primaryKey"`
	BkCloudID       int                                `gorm:"column:bk_cloud_id;primaryKey"`
	DbIp            string                             `gorm:"column:db_ip;primaryKey"`
	DbPort          int                                `gorm:"column:db_port;primaryKey"`
	HarvestType     haprobe.HarvestType                `gorm:"column:harvest_type;primaryKey;type:varchar(32);not null"`
	SequenceID      uint64                             `gorm:"column:sequence_id"`
	AgentID         string                             `gorm:"column:agent_id"`
	IPs             JSON[[]string]                     `gorm:"column:ips;type:json"`
	MessageID       string                             `gorm:"column:message_id"`
	ServiceID       string                             `gorm:"column:service_id"`
	DbTypeName      haprobe.DbType                     `gorm:"column:db_type_name"`
	AccessLayer     haprobe.DbmMetadataAccessLayerType `gorm:"column:access_layer"`
	ClusterType     haprobe.DbmMetadataClusterType     `gorm:"column:cluster_type"`
	MachineType     haprobe.DbmMetadataMachineType     `gorm:"column:machine_type"`
	InstanceRole    haprobe.DbmMetadataInstanceRole    `gorm:"column:instance_role"`
	ReportTimestamp uint64                             `gorm:"column:report_timestamp"`
	Host            JSON[*haprobe.HostMetric]          `gorm:"column:host;type:json"`
	Events          JSON[[]*haprobe.DbEvent]           `gorm:"column:event;type:json"`
	Value           JSON[json.RawMessage]              `gorm:"column:data;type:json"`

	// Time automatically managed by GORM
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt time.Time `gorm:"column:deleted_at"`
}

// NewDbhaData creates a new DbhaDataStatus
func NewDbhaData(msg *haprobe.HarvestData) *DbhaDataStatus {
	data := &DbhaDataStatus{}

	data.SequenceID = msg.SequenceID
	data.MachineID = msg.MachineID
	data.AgentID = msg.AgentID
	data.BkCloudID = msg.BkCloudID
	data.MessageID = msg.MessageID
	data.ServiceID = msg.ServiceID
	data.DbTypeName = msg.DbTypeName
	data.AccessLayer = msg.AccessLayer
	data.ClusterType = msg.ClusterType
	data.MachineType = msg.MachineType
	data.InstanceRole = msg.InstanceRole
	data.DbIp = msg.DbIp
	data.DbPort = msg.DbPort
	data.HarvestType = msg.HarvestType
	data.ReportTimestamp = msg.ReportTimestamp

	if msg.Host != nil {
		data.IPs = JSON[[]string]{Data: msg.Host.NetIPs, Valid: true}
		data.Host = JSON[*haprobe.HostMetric]{Data: msg.Host, Valid: true}
	}

	if msg.Events != nil {
		data.Events = JSON[[]*haprobe.DbEvent]{Data: msg.Events, Valid: true}
	}

	if msg.RawValue != nil {
		data.Value = JSON[json.RawMessage]{Data: msg.RawValue, Valid: true}
	}

	return data
}

// TableName returns the table name
func (t DbhaDataStatus) TableName() string {
	return DbhaDataStatusTableName
}
