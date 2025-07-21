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

import "time"

type DBMMetadata struct {
	BkIDCCityID     int           `json:"bk_idc_city_id"    gorm:"column:bk_idc_city_id"`
	BkBizID         int           `json:"bk_biz_id"         gorm:"column:bk_biz_id"`
	BkCloudID       int           `json:"bk_cloud_id"       gorm:"column:bk_cloud_id"`
	LogicalCityID   int           `json:"logical_city_id"   gorm:"column:logical_city_id"`
	LogicalCityName string        `json:"logical_city_name" gorm:"column:logcial_city_name"`
	ListenPort      int           `json:"port"              gorm:"column:port"`
	ListenIP        string        `json:"ip"                gorm:"column:ip"`
	Cluster         string        `json:"cluster"           gorm:"column:cluster"`
	ClusterID       int           `json:"cluster_id"        gorm:"column:cluster_id"`
	ClusterType     string        `json:"cluster_type"      gorm:"column:cluster_type"`
	MachineType     string        `json:"machine_type"      gorm:"column:machine_type"`
	Status          string        `json:"status"            gorm:"column:status"`
	BindEntries     string        `json:"bind_entries"      gorm:"column:bind_entries"`
	CreatedAt       time.Time     `json:"-"                 gorm:"column:created_at"`
	UpdatedAt       time.Time     `json:"-"                 gorm:"column:updated_at"`
	DeletedAt       time.Time     `json:"-"                 gorm:"column:deleted_at;index"`
	SyncedAt        time.Time     `json:"-"                 gorm:"column:synced_at"`
	SyncDuration    time.Duration `json:"-"                 gorm:"column:sync_duration;type:bigint"`
}

func (t DBMMetadata) TableName() string {
	return "t_dbm_metadata"
}
