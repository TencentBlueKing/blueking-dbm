package handler

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"encoding/json"
	"io/ioutil"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// GetRandomExclude 获取不参加随机化的业务
func (m *PrivService) GetRandomExclude(c *gin.Context) {
	slog.Info("do GetRandomExclude!")
	var input service.RandomExcludePara
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
	// 获取不参加随机化的业务
	exclude, err := input.GetRandomizeExclude()
	SendResponse(c, err, exclude)
	return
}

// ModifyRandomExclude 修改不参与随机化的业务
func (m *PrivService) ModifyRandomExclude(c *gin.Context) {
	slog.Info("do ModifyRandomExclude!")
	var input service.RandomExcludePara

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
	// 传入的业务列表替换当前业务列表
	err = input.ModifyRandomizeExclude(string(body))
	SendResponse(c, err, nil)
	return
}
