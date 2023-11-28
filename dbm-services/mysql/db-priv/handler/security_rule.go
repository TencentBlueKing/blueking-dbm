package handler

import (
	"encoding/json"
	"io/ioutil"
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
)

// GetSecurityRule 获取安全规则
func (m *PrivService) GetSecurityRule(c *gin.Context) {
	slog.Info("do GetSecurityRule!")

	var input service.SecurityRulePara

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
	// 根据名称查询安全规则
	security, err := input.GetSecurityRule()
	SendResponse(c, err, security)
	return
}

// AddSecurityRule 添加安全规则
func (m *PrivService) AddSecurityRule(c *gin.Context) {

	slog.Info("do AddSecurityRule!")
	var input service.SecurityRulePara

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
	// 添加安全规则，安全规则主要用于生成密码和检验密码复杂度
	err = input.AddSecurityRule(string(body))
	SendResponse(c, err, nil)
	return
}

// DeleteSecurityRule 删除安全规则
func (m *PrivService) DeleteSecurityRule(c *gin.Context) {
	slog.Info("do DeleteSecurityRule!")

	var input service.SecurityRulePara

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
	// 根据id删除安全规则
	err = input.DeleteSecurityRule(string(body))
	SendResponse(c, err, nil)
	return
}

// ModifySecurityRule 修改安全规则，修改安全规则的名称和内容
func (m *PrivService) ModifySecurityRule(c *gin.Context) {
	slog.Info("do ModifySecurityRule!")
	var input service.SecurityRulePara

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
	// 根据id，修改安全规则，修改安全规则的名称和内容
	err = input.ModifySecurityRule(string(body))
	SendResponse(c, err, nil)
	return
}
