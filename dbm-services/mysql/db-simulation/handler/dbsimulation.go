/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package handler

import (
	"fmt"
	"strings"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/model"
)

// QueryFileResultParam 获取模拟执行文件的结果
type QueryFileResultParam struct {
	RootID    string `json:"root_id"  binding:"required" `
	VersionID string `json:"version_id" binding:"required"`
}

// QuerySimulationFileResult 查询模拟执行每个文件的执行结果
func QuerySimulationFileResult(r *gin.Context) {
	var param QueryFileResultParam
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", "")
		return
	}
	task_id := fmt.Sprintf("%s_%s", param.RootID, param.VersionID)
	var data []model.TbSqlFileSimulationInfo
	err := model.DB.Where("task_id = ? ", task_id).Find(&data).Error
	if err != nil {
		logger.Error("query file task result failed %v", err)
		SendResponse(r, err, err.Error(), "")
		return
	}
	SendResponse(r, nil, data, "")
}

// TendbSimulation Tendb simulation handler
func TendbSimulation(r *gin.Context) {
	var param service.BaseParam
	requestID := r.GetString("request_id")
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", requestID)
		return
	}
	if requestID == "" {
		SendResponse(r, fmt.Errorf("create request id failed"), nil, requestID)
		return
	}
	version := param.MySQLVersion
	img, err := service.GetImgFromMySQLVersion(version)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", version, err.Error())
		SendResponse(r, err, nil, requestID)
		return
	}
	if err := model.CreateTask(param.TaskId, requestID, version, param.Uid); err != nil {
		logger.Error("create task db record error %s", err.Error())
		SendResponse(r, err, nil, requestID)
		return
	}
	tsk := service.SimulationTask{
		RequestId: requestID,
		DbPodSets: service.NewDbPodSets(),
		BaseParam: &param,
		Version:   version,
	}
	tsk.DbImage = img
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("tendb-%s-%s", strings.ToLower(version),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": requestID},
		RootPwd: param.TaskId,
		Args:    param.BuildStartArgs(),
		Charset: param.MySQLCharSet,
	}
	service.TaskChan <- tsk

	SendResponse(r, nil, "request successful", requestID)
}

// TendbClusterSimulation TendbCluster simulation handler
func TendbClusterSimulation(r *gin.Context) {
	var param service.SpiderSimulationExecParam
	RequestID := r.GetString("request_id")
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", RequestID)
		return
	}
	version := param.MySQLVersion
	img, err := service.GetImgFromMySQLVersion(version)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", version, err.Error())
		SendResponse(r, err, nil, RequestID)
		return
	}

	if err := model.CreateTask(param.TaskId, RequestID, version, param.Uid); err != nil {
		logger.Error("create task db record error %s", err.Error())
		SendResponse(r, err, nil, RequestID)
		return
	}
	tsk := service.SimulationTask{
		RequestId: RequestID,
		DbPodSets: service.NewDbPodSets(),
		BaseParam: &param.BaseParam,
		Version:   version,
	}
	rootPwd := cmutil.RandomString(10)
	if !service.DelPod {
		logger.Info("the pwd %s", rootPwd)
	}
	tsk.DbImage = img
	tsk.SpiderImage, tsk.TdbCtlImage = service.GetSpiderAndTdbctlImg(param.SpiderVersion, service.LatestVersion)
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("spider-%s-%s", strings.ToLower(version),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": RequestID},
		RootPwd: rootPwd,
		Charset: param.MySQLCharSet,
	}
	service.SpiderTaskChan <- tsk
	SendResponse(r, nil, "request successful", RequestID)
}
