package handler

import (
	"encoding/json"
	"io/ioutil"
	"log/slog"
	"net/http"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
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

	if err = json.Unmarshal(body, &input); err != nil {
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

	if err = json.Unmarshal(body, &input); err != nil {
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

	if err = json.Unmarshal(body, &input); err != nil {
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

// GetAccountList 获取账号列表
func (m *PrivService) GetAccountList(c *gin.Context) {
	slog.Info("do GetAccountList!")
	var input service.GetAccountListPara

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

	accounts, count, err := input.GetAccountList()
	type ListResponse struct {
		Count   int64       `json:"count"`
		Results interface{} `json:"results"`
	}
	SendResponse(c, err, ListResponse{
		Count:   count,
		Results: accounts,
	})
	return
}

// GetAccountIncludePsw 获取账号密码
func (m *PrivService) GetAccountIncludePsw(c *gin.Context) {
	slog.Info("do GetAccount!")
	var input service.GetAccountIncludePswPara

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

	accounts, count, err := input.GetAccountIncludePsw()
	SendResponse(c, err, ListResponse{
		Count: count,
		Items: accounts,
	})
	return
}

// SendResponse TODO
func SendResponse(c *gin.Context, err error, data interface{}) {
	code, message := errno.DecodeErr(err)

	c.JSON(http.StatusOK, Response{
		Code:    code,
		Message: message,
		Data:    data,
	})
}

// Response TODO
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// ListResponse TODO
type ListResponse struct {
	Count int64       `json:"count"`
	Items interface{} `json:"items"`
}
