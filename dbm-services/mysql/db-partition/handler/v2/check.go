// Package v2 v2 巡检 HTTP 处理器
package v2

import (
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/handler"
	servicev2 "dbm-services/mysql/db-partition/service/v2"

	"github.com/gin-gonic/gin"
)

// ListCheckBiz POST /partition/v2/check/list_biz
func ListCheckBiz(c *gin.Context) {
	var input servicev2.ListCheckBizInput
	if err := c.ShouldBind(&input); err != nil {
		slog.Error("v2 list_check_biz bind error", "error", err)
		handler.SendResponse(c, errno.ErrBind, nil)
		return
	}

	data, err := servicev2.ListCheckBiz(&input)
	if err != nil {
		slog.Error("v2 list_check_biz error", "error", err)
		handler.SendResponse(c, err, nil)
		return
	}
	handler.SendResponse(c, nil, data)
}

// ListCheckConfIds POST /partition/v2/check/list_conf_ids
func ListCheckConfIds(c *gin.Context) {
	var input servicev2.ListCheckConfIdsInput
	if err := c.ShouldBind(&input); err != nil {
		slog.Error("v2 list_check_conf_ids bind error", "error", err)
		handler.SendResponse(c, errno.ErrBind, nil)
		return
	}

	data, err := servicev2.ListCheckConfIds(&input)
	if err != nil {
		slog.Error("v2 list_check_conf_ids error", "error", err)
		handler.SendResponse(c, err, nil)
		return
	}
	handler.SendResponse(c, nil, data)
}
