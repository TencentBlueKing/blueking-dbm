// Package handler v2版本处理器
package handler

import (
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/service"

	"github.com/gin-gonic/gin"
)

// GetPartitionsConfigV2 v2版本的配置查询接口
func GetPartitionsConfigV2(r *gin.Context) {
	var input service.QueryParititionsInput
	if err := r.ShouldBind(&input); err != nil {
		slog.Error("v2 query_conf bind error", "error", err)
		SendResponse(r, errno.ErrBind, nil)
		return
	}

	slog.Info("v2 query_conf",
		"bk_biz_id", input.BkBizId,
		"immute_domains", input.ImmuteDomains,
		"cluster_type", input.ClusterType)

	lists, count, err := input.GetPartitionsConfig()
	if err != nil {
		slog.Error("v2 query_conf error", "error", err)
		SendResponse(r, err, nil)
		return
	}

	// v2版本的响应结构
	type ListResponseV2 struct {
		Count int64       `json:"count"`
		Items interface{} `json:"items"`
		// 可以在这里添加v2版本特有的字段
		// Version string `json:"version"` // 例如：标识API版本
	}

	SendResponse(r, err, ListResponseV2{
		Count: count,
		Items: lists,
	})
}
