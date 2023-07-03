package handler

import (
	"encoding/json"
	"io/ioutil"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// AddPrivDryRun 使用账号规则，新增权限预检查
func (m *PrivService) AddPrivDryRun(c *gin.Context) {
	slog.Info("do AddPrivDryRun!")

	var (
		input    service.PrivTaskPara
		taskpara service.PrivTaskPara
	)

	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	if err := json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	taskpara, err = input.AddPrivDryRun()
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, err, taskpara)
	return
}

// AddPriv 使用账号规则，新增权限
func (m *PrivService) AddPriv(c *gin.Context) {
	slog.Info("do AddPriv!")

	var input service.PrivTaskPara

	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	err = input.AddPriv(string(body))
	SendResponse(c, err, nil)
	return
}

// AddPrivWithoutAccountRule 不使用账号规则模版，在mysql实例授权。此接口不被页面前端调用，为后台服务设计。不建议通过此接口授权。
func (m *PrivService) AddPrivWithoutAccountRule(c *gin.Context) {
	slog.Info("do AddPrivWithoutAccountRule!")

	var input service.AddPrivWithoutAccountRule

	body, err := ioutil.ReadAll(c.Request.Body)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	if err = json.Unmarshal(body, &input); err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.ErrBind, err)
		return
	}

	err = input.AddPrivWithoutAccountRule(string(body))
	SendResponse(c, err, nil)
	return
}
