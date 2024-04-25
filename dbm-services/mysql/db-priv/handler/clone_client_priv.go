package handler

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"encoding/json"
	"io/ioutil"
	"log/slog"
	"strings"

	"github.com/gin-gonic/gin"
)

// CloneClientPrivDryRun 克隆客户端权限预检查
func (m *PrivService) CloneClientPrivDryRun(c *gin.Context) {
	slog.Info("do  CloneClientPrivDryRun!")
	var input service.CloneClientPrivParaList

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

	err = input.CloneClientPrivDryRun()
	SendResponse(c, err, nil)
	return
}

// CloneClientPriv 克隆客户端权限
func (m *PrivService) CloneClientPriv(c *gin.Context) {
	slog.Info("do  CloneClientPriv!")
	var input service.CloneClientPrivPara
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

	err = input.CloneClientPriv(string(body), ticket)
	SendResponse(c, err, nil)
	return
}
