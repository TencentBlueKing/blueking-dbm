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
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/model"
)

// Response response data define
type Response struct {
	Data      interface{} `json:"data"`
	RequestID string      `json:"request_id"`
	Message   string      `json:"msg"`
	Code      int         `json:"code"`
}

// CreateClusterParam 创建临时的spider的集群参数
type CreateClusterParam struct {
	Pwd           string `json:"pwd"`
	PodName       string `json:"podname"`
	SpiderVersion string `json:"spider_version"`
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
	ps.SpiderImage, ps.TdbCtlImage = getSpiderAndTdbctlImg(param.SpiderVersion, LatestVersion)
	if err := ps.CreateClusterPod(); err != nil {
		logger.Error(err.Error())
		return
	}
	SendResponse(r, nil, "ok", "")
}

func replaceUnderSource(str string) string {
	return strings.ReplaceAll(str, "_", "-")
}

// T 请求查询模拟执行整体任务的执行状态参数
type T struct {
	TaskID string `json:"task_id"`
}

// QueryTask 查询模拟执行整体任务的执行状态
func QueryTask(c *gin.Context) {
	var param T
	if err := c.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(c, err, map[string]interface{}{"stderr": "failed to deserialize parameters"}, "")
		return
	}
	logger.Info("get task_id is %s", param.TaskID)
	var tasks []model.TbSimulationTask
	if err := model.DB.Where(&model.TbSimulationTask{TaskId: param.TaskID}).Find(&tasks).Error; err != nil {
		logger.Error("query task failed %s", err.Error())
		SendResponse(c, err, map[string]interface{}{"stderr": err.Error()}, "")
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
			SendResponse(c, fmt.Errorf("%s", task.SysErrMsg), map[string]interface{}{
				"simulation_version": task.MySQLVersion,
				"stdout":             task.Stdout,
				"stderr":             task.Stderr,
				"errmsg":             fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)},
				"")

		case model.TaskSuccess:
			allSuccessful = true
		default:
			allSuccessful = false
			SendResponse(c, fmt.Errorf("unknown transition state"), map[string]interface{}{
				"stdout": task.Stdout,
				"stderr": task.Stderr,
				"errmsg": fmt.Sprintf("the program has been run with abnormal status:%s", task.Status)},
				"")
		}
	}
	if allSuccessful {
		SendResponse(c, nil, map[string]interface{}{"stdout": "all ok", "stderr": "all ok"}, "")
	}
}

// SendResponse return response data to http client
func SendResponse(r *gin.Context, err error, data interface{}, requestid string) {
	if err != nil {
		r.JSON(http.StatusOK, Response{
			Code:      1,
			Message:   err.Error(),
			Data:      data,
			RequestID: requestid,
		})
		return
	}
	r.JSON(http.StatusOK, Response{
		Code:      0,
		Message:   "successfully",
		Data:      data,
		RequestID: requestid,
	})
}

// getImgFromMySQLVersion 根据版本获取模拟执行运行的镜像配置
func getImgFromMySQLVersion(version string) (img string, err error) {
	img, errx := model.GetImageName("mysql", version)
	if errx == nil {
		logger.Info("get image from db img config: %s", img)
		return img, nil
	}
	switch {
	case regexp.MustCompile("5.5").MatchString(version):
		return config.GAppConfig.Image.Tendb55Img, nil
	case regexp.MustCompile("5.6").MatchString(version):
		return config.GAppConfig.Image.Tendb56Img, nil
	case regexp.MustCompile("5.7").MatchString(version):
		return config.GAppConfig.Image.Tendb57Img, nil
	case regexp.MustCompile("8.0").MatchString(version):
		return config.GAppConfig.Image.Tendb80Img, nil
	default:
		return "", fmt.Errorf("not match any version")
	}
}

func getSpiderAndTdbctlImg(spiderVersion, tdbctlVersion string) (spiderImg, tdbctlImg string) {
	return getSpiderImg(spiderVersion), getTdbctlImg(tdbctlVersion)
}

const (
	// LatestVersion latest version
	LatestVersion = "latest"
)

func getSpiderImg(version string) (img string) {
	if lo.IsEmpty(version) {
		version = LatestVersion
	}
	img, errx := model.GetImageName("spider", version)
	if errx == nil {
		return img
	}
	return config.GAppConfig.Image.SpiderImg
}

func getTdbctlImg(version string) (img string) {
	if lo.IsEmpty(version) {
		version = LatestVersion
	}
	img, errx := model.GetImageName("tdbctl", version)
	if errx == nil {
		return img
	}
	return config.GAppConfig.Image.TdbCtlImg
}
