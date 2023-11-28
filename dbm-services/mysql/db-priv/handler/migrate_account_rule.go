package handler

import (
	"encoding/json"
	"io/ioutil"
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"

	"github.com/gin-gonic/gin"
)

// MigrateAccountRule 迁移mysql帐号规则
func (m *PrivService) MigrateAccountRule(c *gin.Context) {
	slog.Info("do MigrateAccountRule!")
	// 迁移帐号的入参
	var input service.MigratePara
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
	// MigrateAccountRule 获取安全规则
	err = input.MigrateAccountRule()
	if err != nil {
		slog.Error("msg", err)
	}
	SendResponse(c, err, nil)
	return

}
