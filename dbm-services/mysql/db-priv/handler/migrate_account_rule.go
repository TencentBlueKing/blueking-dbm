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

// MigrateAccountRule 迁移mysql帐号规则
func (m *PrivService) MigrateAccountRule(c *gin.Context) {
	slog.Info("do MigrateAccountRule!")
	// 迁移帐号的入参
	var input service.MigratePara
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
	success, fail, successSpider, failSpider, exUids, err := input.MigrateAccountRule(string(body), ticket)
	info := "成功"
	if err != nil {
		slog.Error("msg", "失败", err.Error())
		info = "失败"
	}
	data := struct {
		MigratedMysqlUids  []service.PrivRule `json:"migrated_mysql"`
		MysqlMigrateFail   []service.PrivRule `json:"mysql_migrate_fail"`
		MigratedSpiderUids []service.PrivRule `json:"migrated_spider"`
		SpiderMigrateFail  []service.PrivRule `json:"spider_migrate_fail"`
		CanNotMigrateUids  []int              `json:"can_not_migrate_uids"`
		Info               string             `json:"info"`
	}{success, fail, successSpider,
		failSpider, exUids, info}
	SendResponse(c, err, data)
	return
}

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
