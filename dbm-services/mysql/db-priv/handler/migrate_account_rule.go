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
	//  获取帐号规则
	success, fail, successSpider, failSpider, exUids, err := input.MigrateAccountRule()
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
