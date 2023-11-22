package handler

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"encoding/base64"
	"encoding/json"
	"io/ioutil"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"
)

// GenerateRandomString 生成随机化密码
func (m *PrivService) GenerateRandomString(c *gin.Context) {
	slog.Info("do GenerateRandomString!")
	var input service.GenerateRandomStringPara
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
	if input.SecurityRuleName == "" {
		SendResponse(c, errno.RuleNameNull, nil)
		return
	}
	// 获取安全规则
	security, err := service.GetSecurityRule(input.SecurityRuleName)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.RuleNameNull, nil)
		return
	}
	password, err := service.GenerateRandomString(security)
	// 传输base64，因为部分字符通过url传输会转义
	SendResponse(c, err, base64.StdEncoding.EncodeToString([]byte(password)))
	return
}

// CheckPassword 检查随机化密码复杂度
func (m *PrivService) CheckPassword(c *gin.Context) {
	slog.Info("do CheckRandomString!")
	var input service.CheckPasswordPara
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
	if input.SecurityRuleName == "" {
		SendResponse(c, errno.RuleNameNull, nil)
		return
	}
	// 获取安全规则
	security, err := service.GetSecurityRule(input.SecurityRuleName)
	if err != nil {
		slog.Error("msg", err)
		SendResponse(c, errno.RuleNameNull, nil)
		return
	}
	// base64解码
	plain, err := base64.StdEncoding.DecodeString(input.Password)
	if err != nil {
		slog.Error("msg", "base64 decode error", err)
		SendResponse(c, err, nil)
		return
	}
	// 检查密码复杂度，返回每一项的检查是否通过，true检查通过，false未通过
	resp := service.CheckPassword(security, plain)
	SendResponse(c, nil, resp)
	return
}
