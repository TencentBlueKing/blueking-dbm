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

	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/gorm"
)

// TbSimulationTask [...]
// MEDIUMTEXT
type TbSimulationTask struct {
	ID            int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	TaskId        string    `gorm:"unique;column:task_id;type:varchar(256);not null" json:"task_id"`
	RequestID     string    `gorm:"unique;column:request_id;type:varchar(64);not null" json:"request_id"`
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
	// Phase_Waitting TODO
	Phase_Waitting = "Waitting"
	// Phase_CreatePod TODO
	Phase_CreatePod = "PodCreating"
	// Phase_LoadSchema TODO
	Phase_LoadSchema = "SchemaLoading"
	// Phase_Running TODO
	Phase_Running = "Running"
	// Phase_Done TODO
	Phase_Done = "Done"
)

const (
	// Task_Failed TODO
	Task_Failed = "Failed"
	// Task_Success TODO
	Task_Success = "Success"
)

// CompleteTask TODO
func CompleteTask(task_id, status, stderr, stdout, syserrMsg string) (err error) {
	return DB.Model(TbSimulationTask{}).Where("task_id = ?", task_id).Updates(
		TbSimulationTask{
			Phase:      Phase_Done,
			Status:     status,
			Stdout:     stdout,
			Stderr:     stderr,
			SysErrMsg:  syserrMsg,
			UpdateTime: time.Now()}).Error
}

// UpdateHeartbeat TODO
func UpdateHeartbeat(taskid, stderr, stdout string) {
	err := DB.Model(TbSimulationTask{}).Where("task_id = ?", taskid).Updates(
		TbSimulationTask{
			Stdout:        stdout,
			Stderr:        stderr,
			HeartbeatTime: time.Now(),
		}).Error
	if err != nil {
		logger.Error("update heartbeat time failed %s", err.Error())
	}
}

// UpdatePhase TODO
func UpdatePhase(taskid, phase string) {
	err := DB.Model(TbSimulationTask{}).Where("task_id = ?", taskid).Updates(
		TbSimulationTask{
			Phase:      phase,
			UpdateTime: time.Now(),
		}).Error
	if err != nil {
		logger.Error("update heartbeat time failed %s", err.Error())
	}
}

// CreateTask TODO
func CreateTask(taskid, requestid string) (err error) {
	var task TbSimulationTask
	err = DB.Where(&TbSimulationTask{TaskId: taskid}).First(&task).Error
	if err == nil {
		return fmt.Errorf("this task exists:%s", taskid)
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		logger.Error("")
		return err
	}
	return DB.Create(&TbSimulationTask{
		TaskId:     taskid,
		RequestID:  requestid,
		Phase:      Phase_Waitting,
		CreateTime: time.Now(),
	}).Error
}
