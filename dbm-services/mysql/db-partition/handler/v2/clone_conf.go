package v2

import (
	"log/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/handler"
	servicev2 "dbm-services/mysql/db-partition/service/v2"

	"github.com/gin-gonic/gin"
)

// CloneConf v2 分区配置克隆 /partition/v2/clone_conf
func CloneConf(c *gin.Context) {
	var input servicev2.CloneConfInput
	if err := c.ShouldBind(&input); err != nil {
		err = errno.ErrReadEntity.Add(err.Error())
		slog.Error(err.Error())
		handler.SendResponse(c, err, nil)
		return
	}

	slog.Info("v2 clone_conf",
		"cluster_type", input.ClusterType,
		"operator", input.Operator,
		"info_count", len(input.Infos))

	out, err := servicev2.ClonePartitionsConfig(&input)
	if err != nil {
		slog.Error("v2 clone_conf failed", "error", err)
		handler.SendResponse(c, err, nil)
		return
	}
	handler.SendResponse(c, nil, out)
}
