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
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/model"
)

// SimulationHandler TODO
type SimulationHandler struct {
	BaseHandler
}

// RegisterRouter 注册路由信息
func (s *SimulationHandler) RegisterRouter(engine *gin.Engine) {
	t := engine.Group("/simulation")
	{
		// query simulation task status info
		t.POST("/task/file", s.QuerySimulationFileResult)
		t.POST("/task", s.QueryTask)
	}
	// mysql
	g := engine.Group("/mysql")
	{
		g.POST("/simulation", s.TendbSimulation)
		g.POST("/task", s.QueryTask)
	}
	// spider
	sp := engine.Group("/spider")
	{
		sp.POST("/simulation", s.TendbClusterSimulation)
		sp.POST("/create", s.CreateTmpSpiderPodCluster)
	}
}

// CreateClusterParam 创建临时的spider的集群参数
type CreateClusterParam struct {
	Pwd            string `json:"pwd"`
	PodName        string `json:"podname"`
	SpiderVersion  string `json:"spider_version"`
	BackendVersion string `json:"backend_version"`
}

// CreateTmpSpiderPodCluster 创建临时的spider的集群,多用于测试，debug
func (s *SimulationHandler) CreateTmpSpiderPodCluster(r *gin.Context) {
	var param CreateClusterParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	ps := service.NewDbPodSets()
	ps.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: param.PodName,
		RootPwd: param.Pwd,
		Charset: "utf8mb4",
	}
	var err error
	ps.DbImage, err = service.GetImgFromMySQLVersion(param.BackendVersion)
	if err != nil {
		logger.Error(err.Error())
		return
	}
	ps.SpiderImage, ps.TdbCtlImage = service.GetSpiderAndTdbctlImg(param.SpiderVersion, service.LatestVersion)
	if err := ps.CreateClusterPod(""); err != nil {
		logger.Error(err.Error())
		return
	}
	s.SendResponse(r, nil, "ok")
}

func replaceUnderSource(str string) string {
	return strings.ReplaceAll(str, "_", "-")
}

// T 请求查询模拟执行整体任务的执行状态参数
type T struct {
	TaskID string `json:"task_id"`
}

// QueryTask 查询模拟执行整体任务的执行状态
func (s *SimulationHandler) QueryTask(c *gin.Context) {
	var param T
	if err := s.Prepare(c, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	logger.Info("get task_id is %s", param.TaskID)
	var tasks []model.TbSimulationTask
	if err := model.DB.Where(&model.TbSimulationTask{TaskId: param.TaskID}).Find(&tasks).Error; err != nil {
		logger.Error("query task failed %s", err.Error())
		s.SendResponse(c, err, map[string]interface{}{"stderr": err.Error()})
		return
	}
	allSuccessful := false
	for _, task := range tasks {
		if task.Phase != model.PhaseDone {
			c.JSON(http.StatusOK, Response{
				Code:    2,
				Message: fmt.Sprintf("task current phase is %s", task.Phase),
				Data:    "",
			})
			return
		}
		switch task.Status {
		case model.TaskFailed:
			allSuccessful = false
			s.SendResponse(c, fmt.Errorf("%s", task.SysErrMsg), map[string]interface{}{
				"simulation_version": task.MySQLVersion,
				"stdout":             task.Stdout,
				"stderr":             task.Stderr,
				"errmsg":             fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)})

		case model.TaskSuccess:
			allSuccessful = true
		default:
			allSuccessful = false
			s.SendResponse(c, fmt.Errorf("unknown transition state"), map[string]interface{}{
				"stdout": task.Stdout,
				"stderr": task.Stderr,
				"errmsg": fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)})
		}
	}
	if allSuccessful {
		s.SendResponse(c, nil, map[string]interface{}{"stdout": "all ok", "stderr": "all ok"})
	}
}

// QueryFileResultParam 获取模拟执行文件的结果
type QueryFileResultParam struct {
	RootID    string `json:"root_id"  binding:"required" `
	VersionID string `json:"version_id" binding:"required"`
}

// QuerySimulationFileResult 查询模拟执行每个文件的执行结果
func (s *SimulationHandler) QuerySimulationFileResult(r *gin.Context) {
	var param QueryFileResultParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	task_id := fmt.Sprintf("%s_%s", param.RootID, param.VersionID)
	var data []model.TbSqlFileSimulationInfo
	err := model.DB.Where("task_id = ? ", task_id).Find(&data).Error
	if err != nil {
		logger.Error("query file task result failed %v", err)
		s.SendResponse(r, err, err.Error())
		return
	}
	s.SendResponse(r, nil, data)
}

// TendbSimulation Tendb simulation handler
func (s *SimulationHandler) TendbSimulation(r *gin.Context) {
	var param service.BaseParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	if s.RequestId == "" {
		s.SendResponse(r, fmt.Errorf("create request id failed"), nil)
		return
	}
	version := param.MySQLVersion
	img, err := service.GetImgFromMySQLVersion(version)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", version, err.Error())
		s.SendResponse(r, err, nil)
		return
	}
	if err := model.CreateTask(param.TaskId, s.RequestId, version, param.Uid); err != nil {
		logger.Error("create task db record error %s", err.Error())
		s.SendResponse(r, err, nil)
		return
	}
	tsk := service.SimulationTask{
		RequestId: s.RequestId,
		DbPodSets: service.NewDbPodSets(),
		BaseParam: &param,
		Version:   version,
	}
	tsk.DbImage = img
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("tendb-%s-%s", strings.ToLower(version),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": s.RequestId},
		RootPwd: param.TaskId,
		Args:    param.BuildStartArgs(),
		Charset: param.MySQLCharSet,
	}
	service.TaskChan <- tsk

	s.SendResponse(r, nil, "request successful")
}

// TendbClusterSimulation TendbCluster simulation handler
func (s *SimulationHandler) TendbClusterSimulation(r *gin.Context) {
	var param service.SpiderSimulationExecParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	version := param.MySQLVersion
	img, err := service.GetImgFromMySQLVersion(version)
	if err != nil {
		logger.Error("GetImgFromMySQLVersion %s failed:%s", version, err.Error())
		s.SendResponse(r, err, nil)
		return
	}

	if err := model.CreateTask(param.TaskId, s.RequestId, version, param.Uid); err != nil {
		logger.Error("create task db record error %s", err.Error())
		s.SendResponse(r, err, nil)
		return
	}
	tsk := service.SimulationTask{
		RequestId: s.RequestId,
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
			"request_id": s.RequestId},
		RootPwd: rootPwd,
		Charset: param.MySQLCharSet,
	}
	service.SpiderTaskChan <- tsk
	s.SendResponse(r, nil, "request successful")
}
