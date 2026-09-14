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

// MigrateAccountRuleInDbm DBM一个业务下的集群拆分到另一个业务，账号规则也需要迁移
func (m *PrivService) MigrateAccountRuleInDbm(c *gin.Context) {
	slog.Info("do MigrateAccountRuleInDbm!")
	// 迁移帐号的入参
	var input service.MigrateInDbmPara
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
	//  获取帐号规则
	confictUsers, migrateUsers, err := input.MigrateAccountRuleInDbm(string(body), ticket)
	data := struct {
		ConfictUsers []string `json:"conflict_users"`
		MigrateUsers []string `json:"migrate_users"`
	}{confictUsers, migrateUsers}
	SendResponse(c, err, data)
	return
}
