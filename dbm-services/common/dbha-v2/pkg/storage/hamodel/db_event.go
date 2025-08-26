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
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	DbEventFieldMachineID = "machine_id"
	DbEventFieldBkCloudID = "bk_cloud_id"
	DbEventFieldIP        = "ip"
	DbEventFieldPort      = "port"
	DbEventFieldEndpoint  = "endpoint"
	DbEventFieldType      = "db_event_type"
	DbEventFieldMessage   = "messge"
	DbEventFieldCreatedAt = "created_at"
	DbEventFieldUpdatedAt = "updated_at"
	DbEventFieldDeletedAt = "deleted_at"
)

type DbEvent struct {
	// Keys
	MachineID   string              `gorm:"column:machine_id;primaryKey"`
	BkCloudID   int                 `gorm:"column:bk_cloud_id;primaryKey"`
	IP          string              `gorm:"column:ip;primaryKey"`
	Port        int                 `gorm:"column:port;primaryKey"`
	Endpoint    string              `gorm:"column:endpoint"`
	DbEventType haprobe.DbEventType `gorm:"column:db_event_type"`
	Message     string              `gorm:"column:message"`

	// Time automatically managed by GORM
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt time.Time `gorm:"column:deleted_at"`
}

func (t DbEvent) TableName() string {
	return "t_db_event"
}
