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
)

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	// DbSwitchingSnapshotLog Table
	DbSwitchingSnapshotLogTableName         = "t_db_switching_snapshot_log"
	DbSwitchingSnapshotLogFieldID           = "id"
	DbSwitchingSnapshotLogFieldSwitchID     = "switch_id"
	DbSwitchingSnapshotLogFieldActionScope  = "action_scope"
	DbSwitchingSnapshotLogFieldBkBizID      = "bk_biz_id"
	DbSwitchingSnapshotLogFieldBkCloudID    = "bk_cloud_id"
	DbSwitchingSnapshotLogFieldInstances    = "instances"
	DbSwitchingSnapshotLogFieldReason       = "reason"
	DbSwitchingSnapshotLogFieldResult       = "result"
	DbSwitchingSnapshotLogFieldStatus       = "status"
	DbSwitchingSnapshotLogFieldStartTime    = "start_time"
	DbSwitchingSnapshotLogFieldFinishedTime = "finished_time"
)

// SwitchingSnapshotInstance is the data structure for switching snapshot instance.
type SwitchingSnapshotInstance struct {
	ClusterID         int        `json:"cluster_id"`
	ClusterName       string     `json:"cluster_name"`
	IP                string     `json:"ip"`
	Port              int        `json:"port"`
	MachineType       string     `json:"machine_type"`
	InstanceRole      string     `json:"instance_role"`
	NewMasterIP       string     `json:"new_master_ip"`
	NewMasterPort     int        `json:"new_master_port"`
	BkIdcID           int        `json:"idc_id"`
	CheckStartTime    *time.Time `json:"check_start_time,omitempty"`
	CheckFinishedTime *time.Time `json:"check_finished_time,omitempty"`
}

type DbSwitchingSnapshotLogStatus string

const (
	DbSwitchingSnapshotLogStatusDoing   DbSwitchingSnapshotLogStatus = "doing"
	DbSwitchingSnapshotLogStatusSuccess DbSwitchingSnapshotLogStatus = "success"
	DbSwitchingSnapshotLogStatusFailed  DbSwitchingSnapshotLogStatus = "failed"
)

func (t DbSwitchingSnapshotLogStatus) String() string {
	return string(t)
}

// DbSwitchingSnapshotLog defines the log of database switching.
type DbSwitchingSnapshotLog struct {
	ID           uint                               `gorm:"column:id;primaryKey;autoIncrement"                json:"id"`
	SwitchID     string                             `gorm:"column:switch_id;uniqueIndex:idx_switch_id"        json:"switch_id"`
	DbType       string                             `gorm:"column:db_type;index:idx_db_type"                  json:"db_type"`
	ActionScope  string                             `gorm:"column:action_scope;index:idx_scope"               json:"action_scope"`
	BkBizID      int                                `gorm:"column:bk_biz_id;index:idx_biz"                    json:"bk_biz_id"`
	BkCloudID    int                                `gorm:"column:bk_cloud_id"                                json:"bk_cloud_id"`
	Instances    JSON[[]*SwitchingSnapshotInstance] `gorm:"column:instances;type:json"                        json:"instances,omitempty"`
	Reason       string                             `gorm:"column:reason"                                     json:"reason,omitempty"`
	Result       string                             `gorm:"column:result"                                     json:"result,omitempty"`
	Status       DbSwitchingSnapshotLogStatus       `gorm:"column:status;index:idx_status"                    json:"status,omitempty"`
	StartTime    *time.Time                         `gorm:"column:start_time;autoCreateTime;index:idx_time"   json:"start_time"`
	FinishedTime *time.Time                         `gorm:"column:finished_time;type:datetime"                json:"finished_time,omitempty"`
}

// SetInstances sets the Instances field.
func (t *DbSwitchingSnapshotLog) SetInstances(instances []*SwitchingSnapshotInstance) {
	t.Instances = JSON[[]*SwitchingSnapshotInstance]{Data: instances, Valid: true}
}

// TableName returns the name of switching log table
func (t DbSwitchingSnapshotLog) TableName() string {
	return DbSwitchingSnapshotLogTableName
}
