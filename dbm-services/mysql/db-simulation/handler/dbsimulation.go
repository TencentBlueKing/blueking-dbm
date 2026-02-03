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
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
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
		sp.POST("/create/by/request/id", s.CreateClusterByRequestId)
	}
}

const (
	// DefaultMySQLCharset 默认 MySQL 字符集
	DefaultMySQLCharset = "utf8mb4"
)

// CreateClusterByRequestIdParam 创建集群的请求参数
type CreateClusterByRequestIdParam struct {
	Name         string `json:"name" binding:"required"`
	RequestId    string `json:"request_id" binding:"required"`
	RandomString string `json:"random_string" binding:"required"`
}

// CreateClusterByRequestId 创建集群的请求
func (s *SimulationHandler) CreateClusterByRequestId(r *gin.Context) {
	var param CreateClusterByRequestIdParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("参数绑定失败 %s", err)
		return
	}

	// 查询请求记录
	record, err := s.queryRequestRecord(param.RequestId)
	if err != nil {
		logger.Error("查询请求记录失败 request_id:%s error:%s", param.RequestId, err.Error())
		s.SendResponse(r, errors.Wrap(err, "查询请求记录失败"), nil)
		return
	}

	// 解析请求体
	originRequestBody, err := s.parseRequestBody(record.RequestBody)
	if err != nil {
		logger.Error("解析请求体失败 request_id:%s error:%s", param.RequestId, err.Error())
		s.SendResponse(r, errors.Wrap(err, "解析请求体失败"), nil)
		return
	}

	// 提取配置信息
	config, err := s.extractClusterConfig(originRequestBody)
	if err != nil {
		logger.Error("提取集群配置失败 request_id:%s error:%s", param.RequestId, err.Error())
		s.SendResponse(r, errors.Wrap(err, "提取集群配置失败"), nil)
		return
	}

	// 创建 Pod 配置
	ps := service.NewDbPodSets()
	ps.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: param.Name,
		RootPwd: param.RandomString,
		Charset: config.Charset,
	}
	ps.DbImage, err = service.GetImgFromMySQLVersion(config.MySQLVersion)
	if err != nil {
		logger.Error(err.Error())
		s.SendResponse(r, errors.Wrap(err, "获取 MySQL 镜像失败"), nil)
		return
	}

	// 为每个 Spider 版本构建 SpiderPods 配置
	for _, spiderVer := range config.SpiderVersions {
		spiderImg, _ := service.GetSpiderAndTdbctlImg(spiderVer.Version, service.LatestVersion)
		ps.SpiderPods = append(ps.SpiderPods, service.SpiderPodBaseInfo{
			SpiderImage:     spiderImg,
			SpiderVersion:   spiderVer.Version,
			SpiderStartArgs: spiderVer.StartConfig,
		})
	}
	// 获取 TdbCtl 镜像（使用第一个 Spider 版本的配置）
	_, ps.TdbCtlImage = service.GetSpiderAndTdbctlImg(config.SpiderVersions[0].Version, service.LatestVersion)
	ps.TdbCtlStartArgs = config.TdbCtlStartArgs
	ps.BackendStartArgs = config.BackendStartArgs

	// 创建集群 Pod
	if err := ps.CreateClusterPod(config.MySQLVersion, nil); err != nil {
		logger.Error("创建集群 Pod 失败 request_id:%s pod_name:%s mysql_version:%s error:%s",
			param.RequestId, param.Name, config.MySQLVersion, err.Error())
		s.SendResponse(r, errors.Wrap(err, "创建集群 Pod 失败"), nil)
		return
	}

	logger.Info("创建集群 Pod 成功 request_id:%s pod_name:%s mysql_version:%s",
		param.RequestId, param.Name, config.MySQLVersion)
	s.SendResponse(r, nil, "ok")
}

// clusterConfig 集群配置信息
type clusterConfig struct {
	Charset          string
	MySQLVersion     string
	SpiderVersions   []service.SpiderVersionConfig // 多个 Spider 版本配置
	TdbCtlStartArgs  map[string]string
	BackendStartArgs map[string]string
}

// queryRequestRecord 查询请求记录
func (s *SimulationHandler) queryRequestRecord(requestID string) (*model.TbRequestRecord, error) {
	var record model.TbRequestRecord
	if err := model.DB.Where("request_id = ?", requestID).First(&record).Error; err != nil {
		return nil, errors.Wrapf(err, "查询请求记录失败, request_id: %s", requestID)
	}
	return &record, nil
}

// parseRequestBody 解析请求体 JSON
func (s *SimulationHandler) parseRequestBody(requestBody string) (map[string]interface{}, error) {
	var body map[string]interface{}
	if err := json.Unmarshal([]byte(requestBody), &body); err != nil {
		return nil, errors.Wrap(err, "JSON 反序列化失败")
	}
	return body, nil
}

// extractClusterConfig 从请求体中提取集群配置
func (s *SimulationHandler) extractClusterConfig(body map[string]interface{}) (*clusterConfig, error) {
	config := &clusterConfig{}

	// 提取字符集
	if charset, ok := body["mysql_charset"].(string); ok && charset != "" {
		config.Charset = charset
	} else {
		config.Charset = DefaultMySQLCharset
	}

	// 提取 MySQL 版本
	mysqlVersion, ok := body["mysql_version"].(string)
	if !ok || mysqlVersion == "" {
		return nil, errors.New("mysql_version 字段缺失或类型错误")
	}
	config.MySQLVersion = mysqlVersion

	// 提取多个 Spider 版本配置
	if spiderVersions, ok := body["spider_versions"].([]interface{}); ok && len(spiderVersions) > 0 {
		for _, sv := range spiderVersions {
			if svMap, ok := sv.(map[string]interface{}); ok {
				version, _ := svMap["version"].(string)
				if version == "" {
					continue
				}
				startConfig := make(map[string]string)
				if sc, ok := svMap["start_config"].(map[string]interface{}); ok {
					startConfig = convertToStringMap(sc)
				}
				config.SpiderVersions = append(config.SpiderVersions, service.SpiderVersionConfig{
					Version:     version,
					StartConfig: startConfig,
				})
			}
		}
	}
	if len(config.SpiderVersions) == 0 {
		return nil, errors.New("spider_versions 字段缺失或为空")
	}

	// 提取 TdbCtl 启动参数
	if tdbCtlArgs, ok := body["tdbctl_start_configs"].(map[string]interface{}); ok {
		config.TdbCtlStartArgs = convertToStringMap(tdbCtlArgs)
	} else {
		config.TdbCtlStartArgs = make(map[string]string)
	}

	// 提取 Backend 启动参数
	if backendArgs, ok := body["mysql_start_configs"].(map[string]interface{}); ok {
		config.BackendStartArgs = convertToStringMap(backendArgs)
	} else {
		config.BackendStartArgs = make(map[string]string)
	}

	return config, nil
}

// convertToStringMap 将 map[string]interface{} 转换为 map[string]string
func convertToStringMap(m map[string]interface{}) map[string]string {
	result := make(map[string]string, len(m))
	for k, v := range m {
		if str, ok := v.(string); ok {
			result[k] = str
		} else if str := fmt.Sprintf("%v", v); str != "" {
			result[k] = str
		}
	}
	return result
}

// CreateClusterParam 创建临时的spider的集群参数
type CreateClusterParam struct {
	RandomString   string                        `json:"random_string"`
	PodName        string                        `json:"pod_name"`
	SpiderVersions []service.SpiderVersionConfig `json:"spider_versions" binding:"required,gt=0,dive"` // 多个 Spider 版本配置
	BackendVersion string                        `json:"backend_version"`
	Charset        string                        `json:"charset"`
}

// CreateTmpSpiderPodCluster 创建临时的spider的集群,多用于测试，debug
func (s *SimulationHandler) CreateTmpSpiderPodCluster(r *gin.Context) {
	var param CreateClusterParam
	if err := s.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	if param.Charset == "" {
		param.Charset = "utf8mb4"
	}
	ps := service.NewDbPodSets()
	ps.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: param.PodName,
		RootPwd: param.RandomString,
		Charset: param.Charset,
	}
	var err error
	ps.DbImage, err = service.GetImgFromMySQLVersion(param.BackendVersion)
	if err != nil {
		logger.Error(err.Error())
		return
	}

	// 为每个 Spider 版本构建 SpiderPods 配置
	for _, spiderVer := range param.SpiderVersions {
		spiderImg, _ := service.GetSpiderAndTdbctlImg(spiderVer.Version, service.LatestVersion)
		ps.SpiderPods = append(ps.SpiderPods, service.SpiderPodBaseInfo{
			SpiderImage:     spiderImg,
			SpiderVersion:   spiderVer.Version,
			SpiderStartArgs: spiderVer.StartConfig,
		})
	}
	// 获取 TdbCtl 镜像
	_, ps.TdbCtlImage = service.GetSpiderAndTdbctlImg(param.SpiderVersions[0].Version, service.LatestVersion)

	if err := ps.CreateClusterPod("", nil); err != nil {
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
			s.SendResponse(c, errno.SimulationTaskFailed.Add(task.SysErrMsg), map[string]interface{}{
				"simulation_version": task.MySQLVersion,
				"stdout":             task.Stdout,
				"stderr":             task.Stderr,
				"errmsg":             fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)})

		case model.TaskSuccess:
			allSuccessful = true
		default:
			allSuccessful = false
			s.SendResponse(c, errno.SimulationTaskFailed.Add("unknown transition state"), map[string]interface{}{
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
		Labels: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": s.RequestId},
		RootPwd: param.TaskId,
		Args:    param.BuildStartArgs(),
		Charset: param.MySQLCharSet,
	}
	tsk.BackendStartArgs = param.MySQLStartConfigs
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

	// 为每个 Spider 版本构建 SpiderPods 配置
	for _, spiderVer := range param.SpiderVersions {
		spiderImg := service.GetSpiderImg(spiderVer.Version)
		tsk.SpiderPods = append(tsk.SpiderPods, service.SpiderPodBaseInfo{
			SpiderImage:     spiderImg,
			SpiderVersion:   spiderVer.Version,
			SpiderStartArgs: spiderVer.StartConfig,
		})
	}
	// 获取 TdbCtl 镜像
	tsk.TdbCtlImage = service.GetTdbctlImg(service.LatestVersion)

	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("spider-%s-%s", strings.ToLower(version),
			replaceUnderSource(param.TaskId)),
		Labels: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": s.RequestId},
		RootPwd: rootPwd,
		Charset: param.MySQLCharSet,
	}
	tsk.BackendStartArgs = param.MySQLStartConfigs
	service.SpiderTaskChan <- tsk
	s.SendResponse(r, nil, "request successful")
}
