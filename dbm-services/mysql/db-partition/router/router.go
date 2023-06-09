// Package router TODO
package router

import (
	"dbm-services/mysql/db-partition/handler"

	"github.com/gin-gonic/gin"
)

// RegisterRouter TODO
func RegisterRouter(engine *gin.Engine) {
	p := engine.Group("/partition")
	p.POST("/query_conf", handler.GetPartitionsConfig)
	p.POST("/query_log", handler.GetPartitionLog)
	p.POST("/create_conf", handler.CreatePartitionsConfig)
	p.POST("/del_conf", handler.DeletePartitionsConfig)
	p.POST("/dry_run", handler.DryRun)
	p.POST("/disable_partition", handler.DisablePartition)
	p.POST("/enable_partition", handler.EnablePartition)
	p.POST("/update_conf", handler.UpdatePartitionsConfig)
}
