// Package v2 v2 版本 HTTP 处理器
package v2

import (
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/handler"
	"dbm-services/mysql/db-partition/service"
	servicev2 "dbm-services/mysql/db-partition/service/v2"

	"github.com/gin-gonic/gin"
)

// QueryConf v2 配置查询接口 /partition/v2/query_conf，model 与 service 共用
func QueryConf(c *gin.Context) {
	var input service.QueryParititionsInput
	if err := c.ShouldBind(&input); err != nil {
		slog.Error("v2 query_conf bind error", "error", err)
		handler.SendResponse(c, errno.ErrBind, nil)
		return
	}

	slog.Info("v2 query_conf",
		"bk_biz_id", input.BkBizId,
		"immute_domains", input.ImmuteDomains,
		"cluster_type", input.ClusterType)

	lists, count, err := servicev2.GetPartitionsConfig(&input)
	if err != nil {
		slog.Error("v2 query_conf error", "error", err)
		handler.SendResponse(c, err, nil)
		return
	}

	type listResponseV2 struct {
		Count int64       `json:"count"`
		Items interface{} `json:"items"`
	}
	handler.SendResponse(c, err, listResponseV2{
		Count: count,
		Items: lists,
	})
}
