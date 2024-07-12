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

// GetAccountRuleList 获取账号规则
func (m *PrivService) GetAccountRuleList(c *gin.Context) {
	slog.Info("do GetAccountRuleList!")
	var input service.QueryRulePara

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

	if *input.ClusterType == "mongodb" {
		err = input.MongoDBAddAccountRule(string(body), ticket)
	} else {
		err = input.AddAccountRule(string(body), ticket)
	}
	SendResponse(c, err, nil)
	return
}

// AddAccountRuleDryRun 添加账号规则
func (m *PrivService) AddAccountRuleDryRun(c *gin.Context) {
	slog.Info("do AddAccountRule!")
	var input service.AccountRulePara
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

	forceRun, err := input.AddAccountRuleDryRun()
	type Force struct {
		ForceRun bool `json:"force_run"`
	}
	SendResponse(c, err, Force{forceRun})
	return
}

// DeleteAccountRule 删除账号规则
func (m *PrivService) DeleteAccountRule(c *gin.Context) {
	slog.Info("do DeleteAccountRule!")

	var input service.DeleteAccountRuleById
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

	err = input.DeleteAccountRule(string(body), ticket)
	SendResponse(c, err, nil)
	return
}

// ModifyAccountRule 修改账号规则，修改账号规则的db名、权限
func (m *PrivService) ModifyAccountRule(c *gin.Context) {
	slog.Info("do ModifyAccountRule!")
	var input service.AccountRulePara
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

	err = input.ModifyAccountRule(string(body), ticket)
	SendResponse(c, err, nil)
	return
}
