package handler

import (
	"encoding/json"
	"io/ioutil"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// GetAccountRuleList 获取账号规则
func (m *PrivService) GetAccountRuleList(c *gin.Context) {
	slog.Info("do GetAccountRuleList!")

	var input service.BkBizId

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

	accountRuleList, count, err := input.QueryAccountRule()
	SendResponse(c, err, ListResponse{
		Count: count,
		Items: accountRuleList,
	})
	return
}

// AddAccountRule 添加账号规则
func (m *PrivService) AddAccountRule(c *gin.Context) {

	slog.Info("do AddAccountRule!")
	var input service.AccountRulePara

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

	err = input.AddAccountRule(string(body))
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, nil, nil)
	return
}

// DeleteAccountRule 删除账号规则
func (m *PrivService) DeleteAccountRule(c *gin.Context) {
	slog.Info("do DeleteAccountRule!")

	var input service.DeleteAccountRuleById

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

	err = input.DeleteAccountRule(string(body))
	SendResponse(c, err, nil)
	return
}

// ModifyAccountRule 修改账号规则，修改账号规则的db名、权限
func (m *PrivService) ModifyAccountRule(c *gin.Context) {
	slog.Info("do ModifyAccountRule!")
	var input service.AccountRulePara

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

	err = input.ModifyAccountRule(string(body))
	if err != nil {
		SendResponse(c, err, nil)
		return
	}
	SendResponse(c, nil, nil)
	return
}
