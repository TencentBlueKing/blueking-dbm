package handler

import (
	"encoding/json"
	"io/ioutil"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// AddAccount 新增账号
func (m *PrivService) AddAccount(c *gin.Context) {
	slog.Info("do AddAccount!")
	var input service.AccountPara

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

	err = input.AddAccount(string(body))
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, nil, nil)
	return
}

// DeleteAccount 删除账号
func (m *PrivService) DeleteAccount(c *gin.Context) {
	slog.Info("do DeleteAccount!")

	var input service.AccountPara

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

	err = input.DeleteAccount(string(body))
	SendResponse(c, err, nil)
	return
}

// ModifyAccount 修改账号的密码
func (m *PrivService) ModifyAccount(c *gin.Context) {

	slog.Info("do ModifyAccount!")
	var input service.AccountPara

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

	err = input.ModifyAccountPassword(string(body))

	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, nil, nil)
	return
}
