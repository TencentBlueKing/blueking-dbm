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

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
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
	DbmMetadataFieldDeletedAt       = "deleted_at"
	DbmMetadataFieldSyncDuration    = "sync_duration"
)

type BindEntry struct {
	BindPort       int         `json:"bind_port"`
	BindIps        []string    `json:"bind_ips"`
	Domain         string      `json:"domain"`
	EntryRole      string      `json:"entry_role"`
	ForwardEntryId interface{} `json:"forward_entry_id"`
	ClbIP          string      `json:"clb_ip"`
	ClbID          string      `json:"clb_id"`
	ClbListenerID  string      `json:"listener_id"`
	ClbRegion      string      `json:"clb_region"`
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
	BkCloudID       int           `gorm:"column:bk_cloud_id;primaryKey"`
	ListenIP        string        `gorm:"column:ip;primaryKey"`
	ListenPort      int           `gorm:"column:port;primaryKey"`
	BkIdcCityID     int           `gorm:"column:bk_idc_city_id"`
	BkBizID         int           `gorm:"column:bk_biz_id"`
	LogicalCityID   int           `gorm:"column:logical_city_id"`
	LogicalCityName string        `gorm:"column:logcial_city_name"`
	Cluster         string        `gorm:"column:cluster"`
	ClusterID       int           `gorm:"column:cluster_id"`
	ClusterType     string        `gorm:"column:cluster_type"`
	MachineType     string        `gorm:"column:machine_type"`
	Status          string        `gorm:"column:status"`
	BindEntry       BindEntryType `gorm:"column:bind_entry;type:json"`
	CreatedAt       time.Time     `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt       time.Time     `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt       time.Time     `gorm:"column:deleted_at;index"`
	SyncDuration    time.Duration `gorm:"column:sync_duration;type:bigint"`
}

func (t DbmMetadata) TableName() string {
	return "t_dbm_metadata"
}
