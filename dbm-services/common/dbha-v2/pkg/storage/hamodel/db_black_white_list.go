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

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	// DbBlackWhiteList Table
	DbBlackWhiteListTableName          = "t_db_black_white_list"
	DbBlackWhiteListFieldID            = "id"
	DbBlackWhiteListFieldBkBizID       = "bk_biz_id"
	DbBlackWhiteListFieldBkCloudID     = "bk_cloud_id"
	DbBlackWhiteListFieldClusterID     = "cluster_id"
	DbBlackWhiteListFieldClusterName   = "cluster_name"
	DbBlackWhiteListFieldStatus        = "status"
	DbBlackWhiteListFieldSwitchVersion = "switch_version"
	DbBlackWhiteListFieldCreatedAt     = "created_at"
	DbBlackWhiteListFieldUpdatedAt     = "updated_at"
)

// SwitchVersionType defines the type of switch version.
type SwitchVersionType string

const (
	SwitchVersionV1 SwitchVersionType = "v1"
	SwitchVersionV2 SwitchVersionType = "v2"
)

func (s SwitchVersionType) String() string {
	return string(s)
}

// DbBlackWhiteList defines the black and white list of database switching (v2 uses whitelist).
type DbBlackWhiteList struct {
	ID            uint              `gorm:"column:id;primaryKey;autoIncrement"`
	BkBizID       int               `gorm:"column:bk_biz_id;uniqueIndex:idx_biz_cloud_cluster"`
	BkCloudID     int               `gorm:"column:bk_cloud_id;uniqueIndex:idx_biz_cloud_cluster"`
	ClusterID     int               `gorm:"column:cluster_id;uniqueIndex:idx_biz_cloud_cluster"`
	ClusterName   string            `gorm:"column:cluster_name;index:idx_cluster"`
	SwitchVersion SwitchVersionType `gorm:"column:switch_version"`
	Status        StatusType        `gorm:"column:status"`
	CreatedAt     time.Time         `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt     time.Time         `gorm:"column:updated_at;autoUpdateTime"`
}

// TableName returns the name of the black-white list table.
func (t DbBlackWhiteList) TableName() string {
	return DbBlackWhiteListTableName
}
