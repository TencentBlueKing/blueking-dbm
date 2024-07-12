package handler

import (
	"encoding/json"
	"io/ioutil"
	"log/slog"
	"strings"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
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

	if err = json.Unmarshal(body, &input); err != nil {
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
	ticket := strings.TrimPrefix(c.FullPath(), "/priv/")

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

	err = input.AddPriv(string(body), ticket)
	SendResponse(c, err, nil)
	return
}

// AddPrivWithoutAccountRule 不使用账号规则模版，在mysql实例授权。此接口不被页面前端调用，为后台服务设计。不建议通过此接口授权。
func (m *PrivService) AddPrivWithoutAccountRule(c *gin.Context) {
	slog.Info("do AddPrivWithoutAccountRule!")

	var input service.AddPrivWithoutAccountRule
	ticket := strings.TrimPrefix(c.FullPath(), "/priv/")

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

	err = input.AddPrivWithoutAccountRule(string(body), ticket)
	SendResponse(c, err, nil)
	return
}

// GetPriv 查询ip在集群授权情况
func (m *PrivService) GetPriv(c *gin.Context) {
	slog.Info("do GetPriv!")
	var input service.GetPrivPara
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
	formatted, count, download, hasPriv, noPriv, err := input.GetPriv()
	if err != nil {
		slog.Error(err.Error())
		SendResponse(c, err, nil)
		return
	}
	data := struct {
		Formatted []service.RelatedIp `json:"privs"`
		Count     int                 `json:"count"`
		Download  []service.GrantInfo `json:"download"`
		HasPriv   []string            `json:"has_priv"`
		NoPriv    []string            `json:"no_priv"`
	}{formatted, count, download, hasPriv, noPriv}
	SendResponse(c, err, data)
	return
}

// GetUserList 在集群中，根据host，查询user@host中的user
func (m *PrivService) GetUserList(c *gin.Context) {
	slog.Info("do GetUserList!")
	var input service.GetPrivPara
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
	users, count, err := input.GetUserList()
	SendResponse(c, err, ListResponse{
		Count: count,
		Items: users,
	})
	return
}
