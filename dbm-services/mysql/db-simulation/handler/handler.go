// Package handler TODO
package handler

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/model"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// Response TODO
type Response struct {
	RequestId string      `json:"request_id"`
	Code      int         `json:"code"`
	Message   string      `json:"msg"`
	Data      interface{} `json:"data"`
}

// CreateClusterParam TODO
type CreateClusterParam struct {
	Pwd     string `json:"pwd"`
	PodName string `json:"podname"`
}

// CreateTmpSpiderPodCluster TODO
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

// SpiderClusterSimulation TODO
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
	tsk.DbImage = img
	tsk.SpiderImage = param.GetSpiderImg()
	tsk.TdbCtlImage = param.GetTdbctlImg()
	tsk.BaseInfo = &service.MySQLPodBaseInfo{
		PodName: fmt.Sprintf("spider-%s-%s", strings.ToLower(param.MySQLVersion),
			replaceUnderSource(param.TaskId)),
		Lables: map[string]string{"task_id": replaceUnderSource(param.TaskId),
			"request_id": requestId},
		RootPwd: cmutil.RandStr(10),
		Charset: param.MySQLCharSet,
	}
	service.SpiderTaskChan <- tsk
	SendResponse(r, nil, "request successful", requestId)
}

// Dbsimulation TODO
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
		RootPwd: cmutil.RandStr(10),
		Charset: param.MySQLCharSet,
	}
	service.TaskChan <- tsk
	SendResponse(r, nil, "request successful", requestId)
}

func replaceUnderSource(str string) string {
	return strings.ReplaceAll(str, "_", "-")
}

// T TODO
type T struct {
	TaskId string `json:"task_id"`
}

// QueryTask TODO
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

// SendResponse TODO
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
