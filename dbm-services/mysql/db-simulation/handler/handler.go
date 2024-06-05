/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package handler TODO
package handler

import (
	"fmt"
	"net/http"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/model"

	"github.com/gin-gonic/gin"
)

// Response respone data define
type Response struct {
	Data      interface{} `json:"data"`
	RequestId string      `json:"request_id"`
	Message   string      `json:"msg"`
	Code      int         `json:"code"`
}

// CreateClusterParam 创建临时的spider的集群参数
type CreateClusterParam struct {
	Pwd     string `json:"pwd"`
	PodName string `json:"podname"`
}

// CreateTmpSpiderPodCluster 创建临时的spider的集群,多用于测试，debug
func CreateTmpSpiderPodCluster(r *gin.Context) {
	var param CreateClusterParam
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", "")
		return
	}
	ps := service.NewDbPodSets()
	ps.BaseInfo = &service.MySQLPodBaseInfo{

		PodName: param.PodName,
		RootPwd: param.Pwd,
		Charset: "utf8mb4",
	}
	ps.DbImage = config.GAppConfig.Image.Tendb57Img
	ps.TdbCtlImage = config.GAppConfig.Image.TdbCtlImg
	ps.SpiderImage = config.GAppConfig.Image.SpiderImg
	if err := ps.CreateClusterPod(); err != nil {
		logger.Error(err.Error())
		return
	}
	SendResponse(r, nil, "ok", "")
}

// SpiderClusterSimulation TendbCluster 模拟执行
func SpiderClusterSimulation(r *gin.Context) {
	var param service.SpiderSimulationExecParam
	requestId := r.GetString("request_id")
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", requestId)
		return
	}
	img, err := service.GetImgFromMySQLVersion(param.MySQLVersion)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", param.MySQLVersion, err.Error())
		SendResponse(r, err, nil, requestId)
		return
	}

	if err := model.CreateTask(param.TaskId, requestId); err != nil {
		logger.Error("create task db record error %s", err.Error())
		SendResponse(r, err, nil, requestId)
		return
	}
	tsk := service.SimulationTask{
		RequestId: requestId,
		DbPodSets: service.NewDbPodSets(),
		BaseParam: &param.BaseParam,
	}
	rootPwd := cmutil.RandStr(10)
	if !service.DelPod {
		logger.Info("the pwd %s", rootPwd)
	}
	tsk.DbImage = img
	tsk.SpiderImage = param.GetSpiderImg()
	tsk.TdbCtlImage = param.GetTdbctlImg()
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("spider-%s-%s", strings.ToLower(param.MySQLVersion),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": requestId},
		RootPwd: rootPwd,
		Charset: param.MySQLCharSet,
	}
	service.SpiderTaskChan <- tsk
	SendResponse(r, nil, "request successful", requestId)
}

// Dbsimulation 发起Tendb模拟执行
func Dbsimulation(r *gin.Context) {
	var param service.BaseParam
	requestId := r.GetString("request_id")
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, "failed to deserialize parameters", requestId)
		return
	}
	if requestId == "" {
		SendResponse(r, fmt.Errorf("create request id failed"), nil, requestId)
		return
	}
	img, err := service.GetImgFromMySQLVersion(param.MySQLVersion)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", param.MySQLVersion, err.Error())
		SendResponse(r, err, nil, requestId)
		return
	}
	if err := model.CreateTask(param.TaskId, requestId); err != nil {
		logger.Error("create task db record error %s", err.Error())
		SendResponse(r, err, nil, requestId)
		return
	}
	tsk := service.SimulationTask{
		RequestId: requestId,
		DbPodSets: service.NewDbPodSets(),
		BaseParam: &param,
	}
	tsk.DbImage = img
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("tendb-%s-%s", strings.ToLower(param.MySQLVersion),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": requestId},
		RootPwd: param.TaskId,
		Charset: param.MySQLCharSet,
	}
	service.TaskChan <- tsk
	SendResponse(r, nil, "request successful", requestId)
}

func replaceUnderSource(str string) string {
	return strings.ReplaceAll(str, "_", "-")
}

// T 请求查询模拟执行整体任务的执行状态参数
type T struct {
	TaskId string `json:"task_id"`
}

// QueryTask 查询模拟执行整体任务的执行状态
func QueryTask(c *gin.Context) {
	var param T
	if err := c.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(c, err, "failed to deserialize parameters", "")
		return
	}
	logger.Info("get task_id is %s", param.TaskId)
	var task model.TbSimulationTask
	if err := model.DB.Where(&model.TbSimulationTask{TaskId: param.TaskId}).First(&task).Error; err != nil {
		logger.Error("query task failed %s", err.Error())
		SendResponse(c, err, "query task failed", "")
		return
	}
	if task.Phase != model.Phase_Done {
		c.JSON(http.StatusOK, Response{
			Code:    2,
			Message: fmt.Sprintf("task current phase is %s", task.Phase),
			Data:    "",
		})
		return
	}
	switch task.Status {
	case model.Task_Failed:
		SendResponse(c, fmt.Errorf(task.SysErrMsg), map[string]interface{}{"stdout": task.Stdout, "stderr": task.Stderr,
			"errmsg": fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)}, "")

	case model.Task_Success:
		SendResponse(c, nil, map[string]interface{}{"stdout": task.Stdout, "stderr": task.Stderr}, "")

	default:
		SendResponse(c, fmt.Errorf("unknown transition state"), map[string]interface{}{"stdout": task.Stdout,
			"stderr": task.Stderr,
			"errmsg": fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)}, "")
	}
}

// FT  请求查询SQL文件模拟执行的参数
type FT struct {
	TaskId        string   `json:"task_id" binding:"required"`
	FileNameHashs []string `json:"file_name_hashs"  binding:"gt=0,dive,required"`
}

// QueryFileTask 查询SQL文件模拟执行的结果
func QueryFileTask(c *gin.Context) {
	var param FT
	if err := c.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(c, err, "failed to deserialize parameters", "")
		return
	}
	var fss []model.TbSqlFileSimulationInfo
	if err := model.DB.Where("task_id = ? and file_name_hash in (?)", param.TaskId, param.FileNameHashs).Find(&fss).
		Error; err != nil {
		logger.Error("query task failed %s", err.Error())
		SendResponse(c, err, "query task failed", "")
		return
	}
	SendResponse(c, nil, fss, "")
}

// SendResponse return respone data to http client
func SendResponse(r *gin.Context, err error, data interface{}, requestid string) {
	if err != nil {
		r.JSON(http.StatusOK, Response{
			Code:      1,
			Message:   err.Error(),
			Data:      data,
			RequestId: requestid,
		})
		return
	}
	r.JSON(http.StatusOK, Response{
		Code:      0,
		Message:   "successfully",
		Data:      data,
		RequestId: requestid,
	})
}
