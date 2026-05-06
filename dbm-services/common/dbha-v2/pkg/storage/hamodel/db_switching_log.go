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
	// DbSwitchingLog Table
	DbSwitchingLogTableName        = "t_db_switching_log"
	DbSwitchingLogFieldID          = "id"
	DbSwitchingLogFieldBkBizID     = "bk_biz_id"
	DbSwitchingLogFieldBkCloudID   = "bk_cloud_id"
	DbSwitchingLogFieldDbIP        = "db_ip"
	DbSwitchingLogFieldDbPort      = "db_port"
	DbSwitchingLogFieldClusterName = "cluster_name"
	DbSwitchingLogFieldDbTypeName  = "db_type_name"
	DbSwitchingLogFieldLevel       = "level"
	DbSwitchingLogFieldContent     = "content"
	DbSwitchingLogFieldCreatedTime = "created_time"
)

// DbSwitchingLog defines the log of database switching.
type DbSwitchingLog struct {
	ID          uint      `gorm:"column:id;primaryKey;autoIncrement"                json:"id"`
	SwitchID    string    `gorm:"column:switch_id;index:idx_switch_id"              json:"switch_id"`
	ActionScope string    `gorm:"column:action_scope;index:idx_scope"               json:"action_scope"`
	BkBizID     int       `gorm:"column:bk_biz_id;index:idx_biz"                    json:"bk_biz_id"`
	BkCloudID   int       `gorm:"column:bk_cloud_id"                                json:"bk_cloud_id"`
	DbIP        string    `gorm:"column:db_ip;index:idx_ip_port"                    json:"db_ip"`
	DbPort      int       `gorm:"column:db_port;index:idx_ip_port"                  json:"db_port"`
	ClusterID   int       `gorm:"column:cluster_id;index:idx_cluster_id"            json:"cluster_id"`
	ClusterName string    `gorm:"column:cluster_name;index:idx_cluster"             json:"cluster_name"`
	DbTypeName  string    `gorm:"column:db_type_name;index:idx_dbtype"              json:"db_type_name"`
	Level       string    `gorm:"column:level;index:idx_level"                      json:"level"`
	Content     string    `gorm:"column:content;type:mediumtext"                    json:"content"`
	CreatedTime time.Time `gorm:"column:created_time;autoCreateTime;index:idx_time" json:"created_time"`
}

// TableName returns the name of switching log table
func (t DbSwitchingLog) TableName() string {
	return DbSwitchingLogTableName
}
