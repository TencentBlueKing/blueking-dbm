/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package model

import (
	"errors"
	"fmt"
	"time"

	"gorm.io/gorm"

	"dbm-services/common/go-pubpkg/logger"
)

// TbSimulationTask [...]
// MEDIUMTEXT
type TbSimulationTask struct {
	ID            int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	TaskId        string    `gorm:"unique;column:task_id;type:varchar(256);not null" json:"task_id"`
	BillTaskId    string    `gorm:"column:bill_task_id;type:varchar(128);not null" json:"bill_task_id"`
	RequestID     string    `gorm:"unique;column:request_id;type:varchar(64);not null" json:"request_id"`
	MySQLVersion  string    `gorm:"column:mysql_version;type:varchar(64);not null" json:"mysql_version"`
	Phase         string    `gorm:"column:phase;type:varchar(16);not null" json:"phase"`
	Status        string    `gorm:"column:status;type:varchar(16);not null" json:"status"`
	Stdout        string    `gorm:"column:stdout;type:mediumtext" json:"stdout"`
	Stderr        string    `gorm:"column:stderr;type:mediumtext" json:"stderr"`
	SysErrMsg     string    `gorm:"column:sys_err_msg;type:text" json:"sys_err_msg"`
	Extra         string    `gorm:"column:extra;type:varchar(512);not null" json:"extra"`
	HeartbeatTime time.Time `gorm:"column:heartbeat_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"heartbeat_time"`
	UpdateTime    time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
	CreateTime    time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
}

const (
	// PhaseWaitting TODO
	PhaseWaitting = "Waitting"
	// PhaseCreatePod TODO
	PhaseCreatePod = "PodCreating"
	// PhaseLoadSchema TODO
	PhaseLoadSchema = "SchemaLoading"
	// PhaseRunning TODO
	PhaseRunning = "Running"
	// PhaseReloading 重载任务
	PhaseReloading = "Reloading"
	// PhaseDone TODO
	PhaseDone = "Done"
)

const (
	// TaskFailed task failed
	TaskFailed = "Failed"
	// TaskSuccess task successful
	TaskSuccess = "Success"
)

// CompleteTask end the task and update the task status
func CompleteTask(task_id, version, status, stderr, stdout, syserrMsg string) (err error) {
	return DB.Model(TbSimulationTask{}).Where("task_id = ? and mysql_version = ? ", task_id, version).Updates(
		TbSimulationTask{
			Phase:      PhaseDone,
			Status:     status,
			Stdout:     stdout,
			Stderr:     stderr,
			SysErrMsg:  syserrMsg,
			UpdateTime: time.Now()}).Error
}

// UpdateHeartbeat update task heartbeat
func UpdateHeartbeat(taskid string) {
	err := DB.Model(TbSimulationTask{}).Where("task_id = ?", taskid).Updates(
		TbSimulationTask{
			HeartbeatTime: time.Now(),
		}).Error
	if err != nil {
		logger.Error("update heartbeat time failed %s", err.Error())
	}
}

// UpdatePhase update task phase
func UpdatePhase(taskid, version, phase string) {
	err := DB.Model(TbSimulationTask{}).Where("task_id = ? and mysql_version = ? ", taskid, version).Updates(
		TbSimulationTask{
			Phase:      phase,
			UpdateTime: time.Now(),
		}).Error
	if err != nil {
		logger.Error("update heartbeat time failed %s", err.Error())
	}
}

// CreateTask create task
func CreateTask(taskid, requestid, version string, billTaskId string) (err error) {
	var task TbSimulationTask
	err = DB.Where(&TbSimulationTask{TaskId: taskid}).First(&task).Error
	if err == nil {
		return fmt.Errorf("this task exists:%s", taskid)
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		logger.Error("create task failed %s", err.Error())
		return err
	}
	return DB.Create(&TbSimulationTask{
		TaskId:        taskid,
		RequestID:     requestid,
		BillTaskId:    billTaskId,
		MySQLVersion:  version,
		Phase:         PhaseWaitting,
		HeartbeatTime: time.Now(),
		CreateTime:    time.Now(),
	}).Error
}
